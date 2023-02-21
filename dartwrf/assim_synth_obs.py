import os, sys, shutil, warnings
import time as time_module
import datetime as dt
import numpy as np

from config.cfg import exp
from config.clusters import cluster
from dartwrf.utils import symlink, copy, sed_inplace, append_file, mkdir, try_remove, print, shell
from dartwrf.obs import error_models as err
import dartwrf.create_obsseq as osq
from dartwrf import wrfout_add_geo
from dartwrf import obsseq

earth_radius_km = 6370


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

    if just_prior_values:  # if not compute posterior
        template = cluster.scriptsdir + "/../templates/input.eval.nml"
    else:
        template = cluster.scriptsdir + "/../templates/input.nml"
    copy(template, cluster.dartrundir + "/input.nml")

    # impact_factor
    if exp.adjust_obs_impact:
        copy(cluster.obs_impact_filename, cluster.dartrundir + "/control_impact_runtime.txt")

    # The keys in `options` are placeholders in input.nml which will be replaced.
    # How? This is defined here
    options = {
        "<adjust_obs_impact>": '.true.' if exp.adjust_obs_impact else '.false.',
        "<filter_kind>": str(int(exp.filter_kind)),
        "<sampling_error_correction>": '.true.' if exp.sec else '.false.',
        "<prior_inflation>": str(exp.prior_inflation),
        "<post_inflation>": str(exp.post_inflation),
        "<n_ens>": str(int(exp.n_ens)),
        "<cov_loc_radian>": "0.00000001",  # dummy value, used for types not mentioned below
        "<list_obstypes>": "'" + "','".join(list_obstypes) + "'",
        "<list_cutoffs>": ", ".join(list_cov_loc_radian),
    }

    # Note: only one value of vertical localization possible
    try:
        cov_loc_vert_km, cov_loc_horiz_km = exp.cov_loc_vert_km_horiz_km
        vert_norm_hgt = to_vertical_normalization(cov_loc_vert_km, cov_loc_horiz_km)
        options["<vert_norm_hgt>"] = str(vert_norm_hgt)
        options["<horiz_dist_only>"] = ".false."
    except Exception as e:
        warnings.warn(str(e)+' - not using vertical localization.')
        options["<horiz_dist_only>"] = ".true."
        options["<vert_norm_hgt>"] = "99999.0"  # dummy value

    for key, value in options.items():
        sed_inplace(cluster.dartrundir + "/input.nml", key, value)

    # input.nml for RTTOV
    rttov_nml = cluster.scriptsdir + "/../templates/obs_def_rttov.VIS.nml"
    append_file(cluster.dartrundir + "/input.nml", rttov_nml)


def link_nature_to_dart_truth(time):
    # get wrfout_d01 from nature run
    shutil.copy(time.strftime(exp.nature_wrfout), cluster.dartrundir + "/wrfout_d01")
    # DART may need a wrfinput file as well, which serves as a template for dimension sizes
    symlink(cluster.dartrundir + "/wrfout_d01", cluster.dartrundir + "/wrfinput_d01")
    print(
        "linked", time.strftime(exp.nature_wrfout),
        "to", cluster.dartrundir + "/wrfout_d01",
    )


def prepare_nature_dart(time):
    print("linking nature to DART & georeferencing")
    link_nature_to_dart_truth(time)
    wrfout_add_geo.run(cluster.geo_em, cluster.dartrundir + "/wrfout_d01")


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
        dart_ensdir = cluster.dartrundir + "/prior_ens" + str(iens)
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
        wrfout_add_geo.run(cluster.geo_em, wrfout_dart)

    write_list_of_inputfiles_prior()
    write_list_of_outputfiles()

    print("removing preassim and filter_restart")
    os.system("rm -rf " + cluster.dartrundir + "/preassim_*")
    os.system("rm -rf " + cluster.dartrundir + "/filter_restart*")
    os.system("rm -rf " + cluster.dartrundir + "/output_mean*")
    os.system("rm -rf " + cluster.dartrundir + "/output_sd*")
    os.system("rm -rf " + cluster.dartrundir + "/perfect_output_*")
    os.system("rm -rf " + cluster.dartrundir + "/obs_seq.fina*")


def write_txt(lines, fpath):
    try_remove(fpath)
    with open(fpath, "w") as file:
        for line in lines:
            file.write(line+'\n')

def write_list_of_inputfiles_prior():
     files = []
     for iens in range(1, exp.n_ens+1):
          files.append("./prior_ens" + str(iens) + "/wrfout_d01")
     write_txt(files, cluster.dartrundir+'/input_list.txt')

def write_list_of_inputfiles_posterior(assim_time):
     filedir = cluster.archivedir+assim_time.strftime("/%Y-%m-%d_%H:%M/assim_stage0/")

     files = []
     for iens in range(1, exp.n_ens+1):
          files.append(filedir+'filter_restart_d01.'+str(iens).zfill(4))
     write_txt(files, cluster.dartrundir+'/input_list.txt')

def write_list_of_outputfiles():
    files = []
    for iens in range(1, exp.n_ens+1):
        files.append("./filter_restart_d01." + str(iens).zfill(4))
    write_txt(files, cluster.dartrundir+'/output_list.txt')

def run_perfect_model_obs(nproc=12, verbose=True):
    if verbose:
        print("generating observations - running ./perfect_model_obs")
    os.chdir(cluster.dartrundir)

    try_remove(cluster.dartrundir + "/obs_seq.out")
    if not os.path.exists(cluster.dartrundir + "/obs_seq.in"):
        raise RuntimeError("obs_seq.in does not exist in " + cluster.dartrundir)
    shell('mpirun -np '+str(nproc)+' '+cluster.container+" ./perfect_model_obs > log.perfect_model_obs")
    if not os.path.exists(cluster.dartrundir + "/obs_seq.out"):
        raise RuntimeError(
            "obs_seq.out does not exist in " + cluster.dartrundir,
            "\n look for " + cluster.dartrundir + "/log.perfect_model_obs")

def filter(nproc=12):
    print("time now", dt.datetime.now())
    print("running filter")
    os.chdir(cluster.dartrundir)
    try_remove(cluster.dartrundir + "/obs_seq.final")
    t = time_module.time()
    if nproc < 12:
        shell('mpirun -np 12 '+cluster.container+' ./filter &> log.filter')
    else:  # -genv I_MPI_PIN_PROCESSOR_LIST=0-"+str(int(nproc) - 1)
        shell("mpirun -np "+str(int(nproc))+' '+cluster.container+" ./filter > log.filter")
    print("./filter took", int(time_module.time() - t), "seconds")
    if not os.path.isfile(cluster.dartrundir + "/obs_seq.final"):
        raise RuntimeError(
            "obs_seq.final does not exist in " + cluster.dartrundir,
            "\n look for " + cluster.dartrundir + "/log.filter")


############### archiving

def archive_filteroutput(time):
    print("archiving ...")

    archive_dir = cluster.archivedir + "/obs_seq_final/"
    mkdir(archive_dir)
    fout = archive_dir + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.final")
    copy(cluster.dartrundir + "/obs_seq.final", fout)
    print(fout, "saved.")

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

def get_parametrized_error(obscfg, osf_prior):
    """Calculate the parametrized error for an ObsConfig (one obs type)

    Args
        obscfg (object):                configuration of observations
        osf_prior (obsseq.ObsRecord):   contains truth and prior values from obs_seq.final
                                        (output of ./final in evaluate-mode (no posterior))

    Returns
        np.array            observation error std-dev for assimilation
    """
    Hx_prior = osf_prior.get_prior_Hx().T
    Hx_truth = osf_prior.get_truth_Hx()

    # compute the obs error for assimilation on the averaged grid
    # since the assimilation is done on the averaged grid
    channel = obscfg.get("sat_channel")

    if channel == 5:
        return err.calc_obserr_WV('WV62', Hx_truth, Hx_prior)
    if channel == 6:
        return err.calc_obserr_WV('WV73', Hx_truth, Hx_prior)
    else:
        NotImplementedError('sat_channel not implemented', obscfg.get("sat_channel"))


def set_obserr_assimilate_in_obsseqout(oso, osf_prior, outfile="./obs_seq.out"):
    """"Overwrite existing variance values in obs_seq.out files
    
    Args:
        oso (ObsSeq) :  python representation of obs_seq.out file, 
                        will be modified and written to file
        osf_prior (ObsSeq): python representation of obs_seq.final (output of filter in evaluate-mode without posterior)
                            contains prior values; used for parameterized errors

    Returns:
        None    (writes to file)
    """
    for obscfg in exp.observations:
        kind_str = obscfg['kind']
        kind = osq.obs_kind_nrs[kind_str]

        # modify each kind separately, one after each other
        where_oso_iskind = oso.df.kind == kind
        where_osf_iskind = osf_prior.df.kind == kind

        if obscfg["error_assimilate"] == False:
            assim_err = get_parametrized_error(obscfg, osf_prior.df[where_osf_iskind])
            oso.df.loc[where_oso_iskind, 'variance'] = assim_err**2
            #assert np.allclose(assim_err, oso.df['variance']**2)  # check
        else:
            # overwrite with user-defined values
            oso.df.loc[where_oso_iskind, 'variance'] = obscfg["error_assimilate"]**2

    oso.to_dart(outfile)

def qc_obs(time, oso, osf_prior):
    # obs should be superobbed already!
    for i, obscfg in enumerate(exp.observations): 
        if i > 0:
            raise NotImplementedError()

        obs = oso.df.observations.values
        Hx_prior_mean = osf_prior.df['prior ensemble mean']
        n_obs_orig = len(obs)

        if obscfg.get("sat_channel") == 1:

            if False:
                print('removing obs with abs(FGD) < 0.05')
                Hx_prior = osf_prior.df.get_prior_Hx().T
                # Hx_prior_mean = np.mean(Hx_prior, axis=0)
                #Hx_prior_spread = osf_prior.df['prior ensemble spread'].values
                #Hx_prior_spread[Hx_prior_spread < 1e-9] = 1e-9

                abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
                oso.df = oso.df[abs_FGD > 0.05]  # Hx_prior_spread]

                # obs_dist_to_priormean = abs(obs - Hx_prior_mean)
                # oso.df = oso.df[obs_dist_to_priormean > 5]
                # print('removed', n_obs_orig-len(oso.df), 'observations with abs(FGD) smaller than 5')

            else:
                # set obs to prior mean => no change in mean but spread is adjusted.
                abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
                Hx_prior_median = np.median(osf_prior.df.get_prior_Hx(), axis=1)
                oso.df.loc[abs_FGD <= 0.05, 'observations'] = Hx_prior_median[abs_FGD <= 0.05]

        elif obscfg.get("sat_channel") == 6:  # WV73

            print('removing obs with abs(FGD) smaller than 5')
            obs = oso.df.observations.values
            n_obs_orig = len(obs)

            abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
            oso.df = oso.df[abs_FGD > 5]
        else:
            raise NotImplementedError('no obs QC implemented for this obs type')
        
        print('QC removed', n_obs_orig-len(oso.df), 'observations') 

        # for archiving
        f_out_archive = cluster.archivedir + "/obs_seq_out/" + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out-beforeQC")
        os.makedirs(cluster.archivedir + "/obs_seq_out/", exist_ok=True)
        copy(cluster.dartrundir + "/obs_seq.out", f_out_archive)

        # for assimilation later
        f_out_dart = cluster.dartrundir+'/obs_seq.out'
        oso.to_dart(f_out_dart)
        print('saved', f_out_dart)


def evaluate(assim_time, 
             output_format="%Y-%m-%d_%H:%M_obs_seq.final-eval_posterior_allobs"):
    """Depending on input_list.txt, this function calculates either prior or posterior obs space values.
    """

    os.makedirs(cluster.dartrundir, exist_ok=True)  # create directory to run DART in
    os.chdir(cluster.dartrundir)

    # link DART binaries to run_DART
    os.system(cluster.python + " " + cluster.scripts_rundir + "/link_dart_rttov.py")  

    # remove any existing observation files
    os.system("rm -f input.nml obs_seq.final")  

    print("prepare nature")
    prepare_nature_dart(assim_time)  # link WRF files to DART directory

    if not os.path.isfile(cluster.dartrundir+'/obs_seq.out'):
        raise RuntimeError(cluster.dartrundir+'/obs_seq.out does not exist')

    set_DART_nml(just_prior_values=True)
    filter(nproc=6)

    # archiving
    fout = cluster.archivedir + "/obs_seq_final/" + assim_time.strftime(output_format)
    os.makedirs(cluster.archivedir + "/obs_seq_final/", exist_ok=True)
    copy(cluster.dartrundir + "/obs_seq.final", fout)
    print(fout, "saved.")

    osf = obsseq.ObsSeq(cluster.dartrundir + "/obs_seq.final")
    return osf



def generate_obsseq_out(time):

    def ensure_physical_vis(oso):  # set reflectance < surface albedo to surface albedo
        print(" 2.2) removing obs below surface albedo ")
        clearsky_albedo = 0.2928

        if_vis_obs = oso.df['kind'].values == 262
        if_obs_below_surface_albedo = oso.df['observations'].values < clearsky_albedo
        oso.df.loc[if_vis_obs & if_obs_below_surface_albedo, ('observations')] = clearsky_albedo
        oso.to_dart(f=cluster.dartrundir + "/obs_seq.out")
        return oso


    def apply_superobbing(oso):
        try:
            f_oso = dir_obsseq + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out-before_superob")
            shutil.copy(cluster.dartrundir + "/obs_seq.out-before_superob", f_oso)
            print('saved', f_oso)
        except Exception as e:
            warnings.warn(str(e))

        print(" 2.3) superobbing to", exp.superob_km, "km")
        oso.df = oso.df.superob(window_km=exp.superob_km)
        oso.to_dart(f=cluster.dartrundir + "/obs_seq.out")


    ##############################
        
    dir_obsseq=cluster.archivedir + "/obs_seq_out/"
    os.makedirs(dir_obsseq, exist_ok=True)

    osq.create_obs_seq_in(time, exp.observations)
    run_perfect_model_obs()  # generate observation, draws from gaussian

    print(" 2.1) obs preprocessing")
    oso = obsseq.ObsSeq(cluster.dartrundir + "/obs_seq.out")

    oso = ensure_physical_vis(oso)

    if getattr(exp, "superob_km", False):
        oso = apply_superobbing(oso)

    # archive complete obsseqout
    f_oso = dir_obsseq + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out")
    shutil.copy(cluster.dartrundir + "/obs_seq.out", f_oso)
    print('saved', f_oso)
    return oso


def get_obsseq_out(time):

    # did we specify an obsseqout inputfile?
    if exp.use_existing_obsseq != False: 
        f_obsseq = time.strftime(exp.use_existing_obsseq)
        copy(f_obsseq, cluster.dartrundir+'/obs_seq.out')
        print(f_obsseq, 'copied to', cluster.dartrundir+'/obs_seq.out')
        oso = obsseq.ObsSeq(cluster.dartrundir + "/obs_seq.out")
    else:
        # decision to NOT use existing obs_seq.out file
        
        # did we already generate observations?
        # f_oso_thisexp = cluster.archivedir+'/obs_seq_out/'+time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out")
        # if os.path.isfile(f_oso_thisexp):
        #     # oso exists
        #     copy(f_oso_thisexp, cluster.dartrundir+'/obs_seq.out')
        #     print('copied existing obsseqout from', f_oso_thisexp)
        #     oso = obsseq.ObsSeq(cluster.dartrundir + "/obs_seq.out")
        # else: 

        # generate observations with new observation noise
        oso = generate_obsseq_out(time)

    return oso

def main(time, prior_init_time, prior_valid_time, prior_path_exp):
    """Assimilate observations
    as defined in config/cfg.py
    for a certain timestamp (argument) of the nature run (defined in config/clusters.py)

    Workflow:
    1) prepare nature run & prior ensemble for DART
    2) create obs_seq.in
    3) create obs from nature (obs_seq.out) with user-defined obs-errors
    4) Assimilate with assigned errors
    
    Args:
        assim_time (dt.datetime):           time of output
        prior_init_time (dt.datetime):      forecast start of prior
        prior_valid_time (dt.datetime):     valid time of prior (may be different to assim_time)
        prior_path_exp (str):               path to prior experiment
        
    Returns:
        None
    """
    nproc = cluster.max_nproc

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
    print(" 1) get observations with specified obs-error")
    oso = get_obsseq_out(time)

    ################################################
    print('3.1) evaluate prior')  # evaluate prior observations for all locations
    osf_prior = evaluate(time, output_format="%Y-%m-%d_%H:%M_obs_seq.final-eval_prior_allobs")

    print(" 3.2) assign observation-errors for assimilation ")
    set_obserr_assimilate_in_obsseqout(oso, osf_prior, outfile=cluster.dartrundir + "/obs_seq.out")

    if getattr(exp, "reject_smallFGD", False):
        print(" 3.3) reject observations? ")
        qc_obs(time, oso, osf_prior)

    print(" 3.4) assimilate (run filter) ")
    set_DART_nml()
    filter(nproc=nproc)
    archive_filteroutput(time)

    # evaluate posterior observations for all locations
    write_list_of_inputfiles_posterior(time)
    if getattr(exp, "reject_smallFGD", False):
        copy(cluster.archivedir+'/obs_seq_out/'+time.strftime('%Y-%m-%d_%H:%M_obs_seq.out-beforeQC'), 
             cluster.dartrundir+'/obs_seq.out')
    evaluate(time, output_format="%Y-%m-%d_%H:%M_obs_seq.final-eval_posterior_allobs")


if __name__ == "__main__":
    """Assimilate synthetic observations
    
    Example:
        python assim.py 2008-08-07_12:00 2008-08-06:00 2008-08-07_13:00 /home/fs71386/lkugler/data/sim_archive/exp_v1.18_Pwbub-1-ensprof_40mem
    """

    time = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d_%H:%M")
    prior_init_time = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d_%H:%M")
    prior_valid_time = dt.datetime.strptime(sys.argv[3], "%Y-%m-%d_%H:%M")
    prior_path_exp = str(sys.argv[4])

    main(time, prior_init_time, prior_valid_time, prior_path_exp)