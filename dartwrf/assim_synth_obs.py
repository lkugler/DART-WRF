from multiprocessing.sharedctypes import Value
import os, sys, shutil, warnings
import time as time_module
import datetime as dt
import numpy as np
from scipy.interpolate import interp1d

from config.cfg import exp, cluster
from dartwrf.utils import symlink, copy, sed_inplace, append_file, mkdir, try_remove, print, shell
import dartwrf.create_obsseq as osq
from dartwrf import wrfout_add_geo
from dartwrf import obsseq

earth_radius_km = 6370

def OE_model_harnisch_WV73(ci):
    if ci >= 0 and ci < 16:
        # Kelvin, fit of Fig 7b, Harnisch 2016
        x_ci = [0, 5, 10.5, 13, 16]  # average cloud impact [K]
        y_oe = [1, 4.5, 10, 12, 13]  # adjusted observation error [K]
        oe_73_linear = interp1d(x_ci, y_oe, assume_sorted=True)
        return oe_73_linear(ci)
    else:
        return 13.0

def cloudimpact_73(bt_mod, bt_obs):
    """
    follows Harnisch 2016
    """
    biascor_obs = 0
    bt_lim = 255  # Kelvin for 7.3 micron WV channel

    ci_obs = max(0, bt_lim - (bt_obs - biascor_obs))
    ci_mod = max(0, bt_lim - bt_mod)
    ci = (ci_obs + ci_mod) / 2
    return ci


def read_prior_obs(f_obs_prior):
    """
    docstring
    """
    obsseq = open(f_obs_prior, "r").readlines()
    OBSs = []
    # read observations from obs_seq.final
    for i, line in enumerate(obsseq):
        if " OBS " in line:
            observed = float(obsseq[i + 1].strip())
            truth = float(obsseq[i + 2].strip())
            prior_ensmean = float(obsseq[i + 3].strip())
            prior_enssd = float(obsseq[i + 4].strip())
            prior_ens = []
            for j in range(5, 5 + exp.n_ens):
                prior_ens.append(float(obsseq[i + j].strip()))

            OBSs.append(dict(observed=observed, truth=truth, prior_ens=np.array(prior_ens)))
    return OBSs


def read_truth_obs_obsseq(f):
    """Reads observed and true values from obs_seq.out/final files."""
    obsseq = open(f, "r").readlines()
    true = []
    obs = []
    # read observations from obs_seq.out
    for i, line in enumerate(obsseq):
        if " OBS " in line:
            observed = float(obsseq[i + 1].strip())
            truth = float(obsseq[i + 2].strip())
            true.append(truth)
            obs.append(observed)
    return true, obs


def replace_errors_obsseqout(f, new_errors):
    """Replaces existing observation errors in obs_seq.final files

    new_errors (np.array) : standard deviation,
                            shape must match the number of observations
    """
    debug = True
    obsseq = open(f, "r").readlines()

    # find number of lines between two ' OBS   ' lines:
    first_obs = second_obs = None
    for i, line in enumerate(obsseq):
        if " OBS " in line:
            if first_obs is None:
                first_obs = i
            else:
                second_obs = i
                break
    if not second_obs:
        raise RuntimeError('just one OBS in this file?! '+str(f))
    lines_between = second_obs - first_obs
    lines_obserr_after_obsnr = lines_between - 1  # obserr line is one before ' OBS   ' line

    # replace values in list obsseq
    i_obs = 0
    for i, line in enumerate(obsseq):
        if " OBS " in line:
            line_error_obs_i = i + lines_obserr_after_obsnr

            previous_err_var = obsseq[line_error_obs_i]
            new_err_obs_i = new_errors[i_obs] ** 2  # variance in obs_seq.out
            if debug:
                print(
                    line.strip(),
                    "previous err var ",
                    float(previous_err_var.strip()),
                    "new error",
                    new_err_obs_i,
                )
            obsseq[line_error_obs_i] = " " + str(new_err_obs_i) + " \n"

            i_obs += 1  # next iteration

    with open(f, "w") as file:
        for line in obsseq:
            file.write(line)
    print("replaced obs errors in", f)


def set_DART_nml(just_prior_values=False):
    def to_radian_horizontal(cov_loc_horiz_km):
        cov_loc_radian = cov_loc_horiz_km / earth_radius_km
        return cov_loc_radian

    def to_vertical_normalization(cov_loc_vert_km, cov_loc_horiz_km):
        vert_norm_rad = earth_radius_km * cov_loc_vert_km / cov_loc_horiz_km * 1000
        return vert_norm_rad

    list_obstypes = [obscfg["kind"] for obscfg in exp.observations]
    list_cov_loc_radius_km = [obscfg["cov_loc_radius_km"] for obscfg in exp.observations]
    list_cov_loc_radian = [str(to_radian_horizontal(a)) for a in list_cov_loc_radius_km]

    if just_prior_values:
        template = cluster.scriptsdir + "/../templates/input.eval.nml"
    else:
        template = cluster.scriptsdir + "/../templates/input.nml"
    copy(template, cluster.dartrundir + "/input.nml")

    # options keys are replaced in input.nml with values
    options = {
        "<sampling_error_correction>": '.true.' if exp.sec else '.false.',
        "<post_inflation>": '4' if exp.inflation else '0',
        "<n_ens>": str(int(exp.n_ens)),
        "<cov_loc_radian>": "0.00000001",  # dummy value, used for types not mentioned below
        "<list_obstypes>": "'" + "','".join(list_obstypes) + "'",
        "<list_cutoffs>": ", ".join(list_cov_loc_radian),
    }

    # Note: only one value of vertical localization possible
    if hasattr(exp, 'cov_loc_vert_km_horiz_km'):
        options["<horiz_dist_only>"] = ".false."
        cov_loc_vert_km, cov_loc_horiz_km = exp.cov_loc_vert_km_horiz_km
        vert_norm_hgt = to_vertical_normalization(cov_loc_vert_km, cov_loc_horiz_km)
        options["<vert_norm_hgt>"] = str(vert_norm_hgt)
    else:
        options["<horiz_dist_only>"] = ".true."
        options["<vert_norm_hgt>"] = "99999.0"  # dummy value

    for key, value in options.items():
        sed_inplace(cluster.dartrundir + "/input.nml", key, value)

    # input.nml for RTTOV
    rttov_nml = cluster.scriptsdir + "/../templates/obs_def_rttov.VIS.nml"
    append_file(cluster.dartrundir + "/input.nml", rttov_nml)


def run_Hx(time, obscfg):
    """
    # assumes that prior ensemble is already linked to advance_temp<i>/wrfout_d01
    Creates 
        obs_seq.final (file):       observations on (non-averaged) grid
    """
    # existing obs_seq.out is a precondition for filter
    # needs to know where to take observations
    osq.create_obsseqin_alltypes(time, [obscfg, ])
    run_perfect_model_obs()
    
    print("running H(x) : obs operator on ensemble prior")

    # set input.nml to calculate prior Hx 
    set_DART_nml(just_prior_values=True)

    # run filter to calculate prior Hx 
    shell("mpirun -np 12 ./filter &> log.filter.preassim")

    osf = obsseq.ObsSeq(cluster.dartrundir + "/obs_seq.final")

    if hasattr(exp, "superob_km"):
        df = osf.df
        print("superobbing to", exp.superob_km, "km")
        osf.df = osf.df.superob(window_km=exp.superob_km)
        osf.to_dart(cluster.dartrundir + "/obs_seq.final")
    return osf


def obs_operator_nature(time):
    print("getting true values in obs space from nature run")
    prepare_nature_dart(time)
    run_perfect_model_obs()
    true, _ = read_truth_obs_obsseq(cluster.dartrundir + "/obs_seq.out")
    return true


def link_nature_to_dart_truth(time):
    # get wrfout_d01 from nature run
    shutil.copy(time.strftime(exp.nature_wrfout), cluster.dartrundir + "/wrfout_d01")
    # DART may need a wrfinput file as well, which serves as a template for dimension sizes
    symlink(cluster.dartrundir + "/wrfout_d01", cluster.dartrundir + "/wrfinput_d01")
    print(
        "linked",
        time.strftime(exp.nature_wrfout),
        "to",
        cluster.dartrundir + "/wrfout_d01",
    )


def prepare_nature_dart(time):
    print("linking nature to DART & georeferencing")
    link_nature_to_dart_truth(time)
    wrfout_add_geo.run(
        cluster.dartrundir + "/../geo_em.d01.nc", cluster.dartrundir + "/wrfout_d01"
    )


def prepare_prior_ensemble(assim_time, prior_init_time, prior_valid_time, prior_path_exp):
    """Prepares DART files for running filter
    i.e.
    - links first guess state to DART first guess filenames
    - creates wrfinput_d01 files
    - adds geo-reference (xlat,xlon) coords so that DART can deal with the files
    - writes txt files so DART knows what input and output is
    - removes probably pre-existing files which could lead to problems
    """
    print("prepare prior state estimate")
    for iens in range(1, exp.n_ens + 1):
        print("link wrfout file to DART background file")
        wrfout_run = (
            prior_path_exp
            + prior_init_time.strftime("/%Y-%m-%d_%H:%M/")
            + str(iens)
            + prior_valid_time.strftime("/wrfout_d01_%Y-%m-%d_%H:%M:%S")
        )
        dart_ensdir = cluster.dartrundir + "/advance_temp" + str(iens)
        wrfout_dart = dart_ensdir + "/wrfout_d01"

        os.makedirs(dart_ensdir, exist_ok=True)
        print("copy", wrfout_run, "to", wrfout_dart)
        copy(wrfout_run, wrfout_dart)
        symlink(wrfout_dart, dart_ensdir + "/wrfinput_d01")

        # ensure prior time matches assim time (can be off intentionally)
        if assim_time != prior_valid_time:
            print("overwriting time in prior from nature wrfout")
            shell(cluster.ncks+ " -A -v XTIME,Times "+ 
                    cluster.dartrundir+"/wrfout_d01 "+ wrfout_dart)

        # this seems to be necessary (else wrong level selection)
        wrfout_add_geo.run(cluster.dartrundir + "/../geo_em.d01.nc", wrfout_dart)

    fpath = cluster.dartrundir + "/input_list.txt"
    print("writing", fpath)
    try_remove(fpath)
    with open(fpath, "w") as f:
        for iens in range(1, exp.n_ens + 1):
            f.write("./advance_temp" + str(iens) + "/wrfout_d01")
            f.write("\n")

    fpath = cluster.dartrundir + "/output_list.txt"
    print("writing", fpath)
    try_remove(fpath)
    with open(fpath, "w") as f:
        for iens in range(1, exp.n_ens + 1):
            f.write("./filter_restart_d01." + str(iens).zfill(4))
            f.write("\n")

    print("removing preassim and filter_restart")
    os.system("rm -rf " + cluster.dartrundir + "/preassim_*")
    os.system("rm -rf " + cluster.dartrundir + "/filter_restart*")
    os.system("rm -rf " + cluster.dartrundir + "/output_mean*")
    os.system("rm -rf " + cluster.dartrundir + "/output_sd*")
    os.system("rm -rf " + cluster.dartrundir + "/perfect_output_*")
    os.system("rm -rf " + cluster.dartrundir + "/obs_seq.fina*")


def calc_obserr_WV73(Hx_nature, Hx_prior):
    """Calculate parametrized error (for assimilation)
    Args:
        Hx_nature (np.array):       dim (observations)
        Hx_prior (np.array):        dim (ensemble_members, observations)

    Returns
        np.array        Observation error std-deviation with dim (observations)
    """
    debug = False
    n_obs = len(Hx_nature)
    OEs = np.ones(n_obs)
    for iobs in range(n_obs):
        bt_y = Hx_nature[iobs]
        bt_x_ens = Hx_prior[:, iobs]
        
        # compute Cloud impact for every pair (ensemble, truth)
        CIs = [cloudimpact_73(bt_x, bt_y) for bt_x in bt_x_ens]
        mean_CI = np.mean(CIs)
        oe_model = OE_model_harnisch_WV73(mean_CI)
        if debug:
            print("BT_nature=", bt_y, "=> mean_CI=", mean_CI, "=> OE_assim=", oe_model)
        OEs[iobs] = oe_model
    return OEs

def run_perfect_model_obs(nproc=12):
    print("generating observations - running ./perfect_model_obs")
    os.chdir(cluster.dartrundir)

    try_remove(cluster.dartrundir + "/obs_seq.out")
    if not os.path.exists(cluster.dartrundir + "/obs_seq.in"):
        raise RuntimeError("obs_seq.in does not exist in " + cluster.dartrundir)
    print(shell("mpirun -np "+str(nproc)+" ./perfect_model_obs > log.perfect_model_obs"))
    if not os.path.exists(cluster.dartrundir + "/obs_seq.out"):
        raise RuntimeError(
            "obs_seq.out does not exist in " + cluster.dartrundir,
            "\n look for " + cluster.dartrundir + "/log.perfect_model_obs")


def assimilate(nproc=48):
    print("time now", dt.datetime.now())
    print("running filter")
    os.chdir(cluster.dartrundir)
    try_remove(cluster.dartrundir + "/obs_seq.final")
    t = time_module.time()
    #shell('mpirun -np 12 ./filter &> log.filter')
    shell("".join([
        "mpirun -genv I_MPI_PIN_PROCESSOR_LIST=0-",
        str(int(nproc) - 1)," -np ",str(int(nproc))," ./filter > log.filter"]))
    print("./filter took", int(time_module.time() - t), "seconds")
    if not os.path.isfile(cluster.dartrundir + "/obs_seq.final"):
        raise RuntimeError(
            "obs_seq.final does not exist in " + cluster.dartrundir,
            "\n look for " + cluster.dartrundir + "/log.filter")

# currently unused
# def recycle_output():
#     """Use output of assimilation (./filter) as input for another assimilation (with ./filter)
#     Specifically, this copies the state fields from filter_restart_d01.000x to the wrfout files in advance_temp folders"""
#     update_vars = ['U', 'V', 'T', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QRAIN', 'U10', 'V10', 'T2', 'Q2', 'TSK', 'PSFC', 'CLDFRA']
#     updates = ','.join(update_vars)

#     print('recycle DART output to be used as input')
#     for iens in range(1, exp.n_ens+1):
#         dart_output = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
#         dart_input = cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01'

#         #print('check for non-monotonic vertical pressure')

#         # convert link to file in order to be able to update the content
#         if os.path.islink(dart_input):
#             l = os.readlink(dart_input)
#             os.remove(dart_input)
#             copy(l, dart_input)

#         # print('move DART output to input: '+dart_output+' -> '+dart_input)
#         # os.rename(dart_output, dart_input)  # probably doesnt work

#         print('updating', updates, 'in', dart_input, 'from', dart_output)
#         os.system(cluster.ncks+' -A -v '+updates+' '+dart_output+' '+dart_input)

############### archiving

def archive_osq_final(time, posterior_1min=False):
    """Save obs_seq.final file for later.
    time (dt.datetime) : time of sampling values from files
    posterior_1min (bool) : False if usual assimilation
    """

    if posterior_1min:
        archive_dir = cluster.archivedir + "/obs_seq_final_1min/"
    else:
        archive_dir = cluster.archivedir + "/obs_seq_final/"
    mkdir(archive_dir)
    fout = archive_dir + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.final")
    copy(cluster.dartrundir + "/obs_seq.final", fout)
    print(fout, "saved.")

    # try:
    #     print('archive regression diagnostics') # what are regression diagnostics?!
    #     copy(cluster.dartrundir+'/reg_diagnostics', archive_dir+'/reg_diagnostics')
    # except Exception as e:
    #     warnings.warn(str(e))


def archive_filteroutput(time):
    print("archiving output")
    archive_assim = cluster.archivedir + time.strftime("/%Y-%m-%d_%H:%M/assim_stage0/")
    mkdir(archive_assim)
    copy(cluster.dartrundir + "/input.nml", archive_assim + "/input.nml")

    for iens in range(1, exp.n_ens + 1):  # single members
        copy(
            cluster.dartrundir + "/filter_restart_d01." + str(iens).zfill(4),
            archive_assim + "/filter_restart_d01." + str(iens).zfill(4),
        )

    try:  # not necessary for next forecast run
        for iens in range(1, exp.n_ens + 1):
            copy(
                cluster.dartrundir + "/postassim_member_" + str(iens).zfill(4) + ".nc",
                archive_assim + "/postassim_member_" + str(iens).zfill(4) + ".nc",
            )

        for f in ["output_mean.nc", "output_sd.nc"]:  # copy mean and sd to archive
            copy(cluster.dartrundir + "/" + f, archive_assim + "/" + f)

    except Exception as e:
        warnings.warn(str(e))


def archive_osq_out(time):
    dir_obsseq = cluster.archivedir + "/obs_seq_out/"
    os.makedirs(dir_obsseq, exist_ok=True)
    copy(cluster.dartrundir + "/obs_seq.out",
         dir_obsseq + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out"))
    if os.path.isfile(cluster.dartrundir + "/obs_seq.out-orig"):
        try:
            copy(cluster.dartrundir + "/obs_seq.out-orig",
                dir_obsseq + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out-orig"))
        except Exception as e:
            warnings.warn(str(e))

def is_assim_error_parametrized(obscfg):
    if (obscfg["error_assimilate"] == False) and (
        obscfg.get("sat_channel") == 6):
        return True
    else:
        return False

def get_parametrized_error(obscfg):
    """Calculate the parametrized error for an ObsConfig (one obs type)

    Args
        obscfg ()
        df_obs (obsseq.ObsRecord):      contains observations from obs_seq.out

    Returns
        np.array            observation error std-dev for assimilation
    """

    # run obs operator (through filter program)
    # creates obs_seq.final containing truth & prior Hx
    osf = run_Hx(time, obscfg)
    df_obs = osf.df

    Hx_prior = df_obs.get_prior_Hx().T
    Hx_truth = df_obs.get_truth_Hx()

    # compute the obs error for assimilation on the averaged grid
    # since the assimilation is done on the averaged grid
    if obscfg.get("sat_channel") == 6:
        return calc_obserr_WV73(Hx_truth, Hx_prior)
    elif obscfg.get("sat_channel") == 1:
        return calc_obserr_VIS06(Hx_truth, Hx_prior)
    else:
        NotImplementedError('error_assimilate if False and sat_channel', obscfg.get("sat_channel"))


def set_obserr_assimilate_in_obsseqout(obsseqout, outfile="./obs_seq.out"):
    for obscfg in exp.observations:
        kind_str = obscfg['kind']
        kind = osq.obs_kind_nrs[kind_str]

        # modify each kind separately, one after each other
        mask_kind = obsseqout.df.kind == kind

        if obscfg["error_assimilate"] == False:
            assim_err = get_parametrized_error(obscfg)
            obsseqout.df.loc[mask_kind, 'variance'] = assim_err**2
            #assert np.allclose(assim_err, obsseqout.df['variance']**2)  # check
        else:
            # overwrite with user-defined values
            obsseqout.df.loc[mask_kind, 'variance'] = obscfg["error_assimilate"]**2

    obsseqout.to_dart(outfile)

def qc_obs(oso, outfile='./obs_seq.out'):
    # obs should be superobbed already!
    for i, obscfg in enumerate(exp.observations): 
        if i > 0:
            raise NotImplementedError()

        # run obs operator (through filter program)
        # creates obs_seq.final containing truth & prior Hx
        osf = run_Hx(time, obscfg)
        df_final = osf.df
        obs = oso.df.observations.values
        n_obs_orig = len(obs)

        if obscfg.get("sat_channel") == 1:

            print('removing obs with abs(FGD) smaller than prior ens spread')
            Hx_prior = df_final.get_prior_Hx().T
            Hx_prior_mean = np.mean(Hx_prior, axis=0)
            Hx_prior_spread = df_final['prior ensemble spread'].values
            #Hx_prior_spread[Hx_prior_spread < 1e-9] = 1e-9

            abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
            oso.df = oso.df[abs_FGD > Hx_prior_spread]

            # obs_dist_to_priormean = abs(obs - Hx_prior_mean)
            # oso.df = oso.df[obs_dist_to_priormean > 5]
            # print('removed', n_obs_orig-len(oso.df), 'observations with abs(FGD) smaller than 5')

        elif obscfg.get("sat_channel") == 6:  # WV73

            print('removing obs with abs(FGD) smaller than 5')
            obs = oso.df.observations.values
            n_obs_orig = len(obs)

            Hx_prior = df_final.get_prior_Hx().T
            Hx_prior_mean = np.mean(Hx_prior, axis=0)
            abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
            oso.df = oso.df[abs_FGD > 5]
        else:
            raise NotImplementedError('no obs QC implemented for this obs type')
        
        print('QC removed', n_obs_orig-len(oso.df), 'observations') 
        oso.to_dart(outfile)
        print('saved', outfile)


if __name__ == "__main__":
    """Assimilate observations
    as defined in config/cfg.py
    for a certain timestamp (argument) of the nature run (defined in config/clusters.py)

    Workflow:
    1) prepare nature run & prior ensemble for DART
    2) create obs_seq.in
    3) create obs from nature (obs_seq.out) with user-defined obs-errors
    4) Assimilate with assigned errors

    Note:
        assim_time (dt.datetime):           time of output
        prior_valid_time (dt.datetime):     valid time of prior (may be different to assim_time)

    Example call:
        python assim.py 2008-08-07_12:00 2008-08-06:00 2008-08-07_13:00 /home/fs71386/lkugler/data/sim_archive/exp_v1.18_Pwbub-1-ensprof_40mem
    """

    time = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d_%H:%M")
    prior_init_time = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d_%H:%M")
    prior_valid_time = dt.datetime.strptime(sys.argv[3], "%Y-%m-%d_%H:%M")
    prior_path_exp = str(sys.argv[4])

    archive_time = cluster.archivedir + time.strftime("/%Y-%m-%d_%H:%M/")
    os.makedirs(cluster.dartrundir, exist_ok=True)  # create directory to run DART in
    os.chdir(cluster.dartrundir)

    # link DART binaries to run_DART
    os.system(cluster.python + " " + cluster.scripts_rundir + "/link_dart_rttov.py")  

    # remove any existing observation files
    os.system("rm -f input.nml obs_seq.in obs_seq.out obs_seq.out-orig obs_seq.final")  
    set_DART_nml()

    print("prepare nature")
    prepare_nature_dart(time)  # link WRF files to DART directory

    print("prepare prior ensemble")
    prepare_prior_ensemble(time, prior_init_time, prior_valid_time, prior_path_exp)

    ################################################
    print(" 1) create observations with specified obs-error")
    osq.create_obsseqin_alltypes(time, exp.observations)
    set_DART_nml()

    run_perfect_model_obs()  # create observations

    print(" 2.1) obs preprocessing")

    oso = obsseq.ObsSeq(cluster.dartrundir + "/obs_seq.out")

    if True:  # set reflectance < surface albedo to surface albedo
        print(" 2.2) removing obs below surface albedo ")
        if_vis_obs = oso.df['kind'].values == 262
        if_obs_below_surface_albedo = oso.df['observations'].values < 0.2928

        oso.df.loc[if_vis_obs & if_obs_below_surface_albedo, ('observations')] = 0.2928
        oso.to_dart(f=cluster.dartrundir + "/obs_seq.out")

    if getattr(exp, "superob_km", False):
        print(" 2.3) superobbing to", exp.superob_km, "km")
        oso.df = oso.df.superob(window_km=exp.superob_km)
        copy(cluster.dartrundir + "/obs_seq.out", cluster.dartrundir + "/obs_seq.out-orig")
        oso.to_dart(f=cluster.dartrundir + "/obs_seq.out")


    ################################################
    print(" 2.4) assign observation-errors for assimilation ")
    set_obserr_assimilate_in_obsseqout(oso, outfile=cluster.dartrundir + "/obs_seq.out")

    if getattr(exp, "reject_smallFGD", False):
        print(" 2.5) QC of observations ")
        qc_obs(oso, outfile=cluster.dartrundir + "/obs_seq.out")

    print(" 3) assimilate ")
    archive_osq_out(time)
    
    set_DART_nml()
    assimilate()

    archive_filteroutput(time)
    archive_osq_final(time)
