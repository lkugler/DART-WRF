import os, sys, shutil, warnings, glob
import time as time_module
import datetime as dt
import numpy as np

from dartwrf.utils import symlink, copy, mkdir, try_remove, print, shell, write_txt
from dartwrf import wrfout_add_geo
from dartwrf.obs import error_models as err
from dartwrf.obs import obsseq
from dartwrf.obs import create_obsseq_out as osq_out
from dartwrf import dart_nml

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster


wrfout_format = '/wrfout_d01_%Y-%m-%d_%H:%M:%S'  # WRF file format, will only change if WRF changes
pattern_init_time = "/%Y-%m-%d_%H:%M/"  # pattern for the init_timme folder in sim_archive
pattern_obs_seq_final = "/%Y-%m-%d_%H:%M:%S_obs_seq.final"  # how an obs_seq.final file is archived
pattern_obs_seq_out = "/%Y-%m-%d_%H:%M:%S_obs_seq.out"  # how an obs_seq.out file is archived


def _prepare_DART_grid_template():
    # DART needs a wrfinput file as a template for the grid
    # No data will be read from this file, but the grid information must match exactly.
    symlink(cluster.dart_rundir + "/prior_ens1/wrfout_d01", 
            cluster.dart_rundir + "/wrfinput_d01")

def _find_nature(time):
    """Find the path to the nature file for the given time
    """
    glob_pattern = time.strftime(exp.nature_wrfout_pattern)  # replace time in pattern
    print('searching for nature in pattern:', glob_pattern)
    f_nat = glob.glob(glob_pattern)[0]  # find the nature wrfout-file

    # check user input
    if not 'wrfout' in f_nat.split('/')[-1]:
        warnings.warn(f_nat+" does not contain 'wrfout' in filename, are you sure this is a valid nature file?")
    assert os.path.exists(f_nat), f_nat+" does not exist"
    return f_nat

def prepare_nature_dart(time):
    """Prepares DART nature (wrfout_d01) if available
    
    Args:
        time (dt.datetime): Time at which observations will be made
    """
    try:
        f_nat = _find_nature(time)
    except:
        print('-> no nature available')
        return
    
    shutil.copy(f_nat, cluster.dart_rundir + "/wrfout_d01")  # copy nature wrfout to DART directory

    # add coordinates if necessary
    if cluster.geo_em_for_WRF_ideal:
        wrfout_add_geo.run(cluster.geo_em_for_WRF_ideal, cluster.dart_rundir + "/wrfout_d01")

def prepare_prior_ensemble(assim_time, prior_init_time, prior_valid_time, prior_path_exp):
    """Prepares DART files for running filter
    i.e.
    - links first guess state to DART first guess filenames
    - creates wrfinput_d01 files (grid file, not a real wrfinput file)
    - adds geo-reference (xlat,xlon) coords so that DART can deal with the files
    - writes txt files so DART knows what input and output is
    - removes probably pre-existing files which could lead to problems
    """
    print("prepare prior state estimate")
    for iens in range(1, exp.n_ens + 1):

        print("link wrfout file to DART background file")
        wrfout_run = (
            prior_path_exp
            + prior_init_time.strftime(pattern_init_time)
            + str(iens)
            + prior_valid_time.strftime(wrfout_format)
        )
        dart_ensdir = cluster.dart_rundir + "/prior_ens" + str(iens)
        wrfout_dart = dart_ensdir + "/wrfout_d01"

        # copy prior ens file from archived wrfout files (prior_path_exp)
        os.makedirs(dart_ensdir, exist_ok=True)
        print("copy", wrfout_run, "to", wrfout_dart)
        copy(wrfout_run, wrfout_dart)

        # DART needs a grid file for each ensemble member (this is no real wrfinput file)
        symlink(wrfout_dart, dart_ensdir + "/wrfinput_d01")

        # ensure prior time matches assim time
        # can be intentionally different, e.g. by using a prior for a different time
        if assim_time != prior_valid_time:
            print("overwriting time in prior from nature wrfout")
            shell(cluster.ncks+ " -A -v XTIME,Times "+ 
                    cluster.dart_rundir+"/wrfout_d01 "+ wrfout_dart)

        # this seems to be necessary (else wrong level selection)
        if cluster.geo_em_for_WRF_ideal:
            wrfout_add_geo.run(cluster.geo_em_for_WRF_ideal, wrfout_dart)

    use_linked_files_as_prior()
    write_list_of_outputfiles()

    print("removing preassim and filter_restart")
    os.system("rm -rf " + cluster.dart_rundir + "/preassim_*")
    os.system("rm -rf " + cluster.dart_rundir + "/filter_restart*")
    os.system("rm -rf " + cluster.dart_rundir + "/output_mean*")
    os.system("rm -rf " + cluster.dart_rundir + "/output_sd*")
    os.system("rm -rf " + cluster.dart_rundir + "/perfect_output_*")
    os.system("rm -rf " + cluster.dart_rundir + "/obs_seq.fina*")

def use_linked_files_as_prior():
    """Instruct DART to use the prior ensemble as input
    """
    files = []
    for iens in range(1, exp.n_ens+1):
        files.append("./prior_ens" + str(iens) + "/wrfout_d01")
    write_txt(files, cluster.dart_rundir+'/input_list.txt')

def use_filter_output_as_prior(assim_time):
    """Use posterior as input for DART, e.g. to evaluate the analysis in observation space
    """
    filedir = cluster.archivedir+assim_time.strftime(pattern_init_time+"/assim_stage0/")

    files = []
    for iens in range(1, exp.n_ens+1):
        files.append(filedir+'filter_restart_d01.'+str(iens).zfill(4))
    write_txt(files, cluster.dart_rundir+'/input_list.txt')

def write_list_of_outputfiles():
    files = []
    for iens in range(1, exp.n_ens+1):
        files.append("./filter_restart_d01." + str(iens).zfill(4))
    write_txt(files, cluster.dart_rundir+'/output_list.txt')


def filter(nproc=12):
    _prepare_DART_grid_template()

    print("time now", dt.datetime.now())
    print("running filter")
    os.chdir(cluster.dart_rundir)
    try_remove(cluster.dart_rundir + "/obs_seq.final")

    t = time_module.time()
    if nproc > 1:
        # -genv I_MPI_PIN_PROCESSOR_LIST=0-"+str(int(nproc) - 1)
        shell(cluster.dart_modules+" mpirun -np "+str(int(nproc))+" ./filter > log.filter") 
    else:
        shell(cluster.dart_modules+" ./filter > log.filter")
    print("./filter took", int(time_module.time() - t), "seconds")
    
    if not os.path.isfile(cluster.dart_rundir + "/obs_seq.final"):
        raise RuntimeError(
            "obs_seq.final does not exist in " + cluster.dart_rundir,
            "\n look for " + cluster.dart_rundir + "/log.filter")


############### archiving

def archive_filteroutput(time):
    """Archive filter output files (filter_restart, preassim, postassim, output_mean, output_sd)
    """
    archive_dir = cluster.archivedir + "/obs_seq_final/"
    mkdir(archive_dir)

    # copy obs_seq.final to archive
    fout = archive_dir + time.strftime(pattern_obs_seq_final)
    copy(cluster.dart_rundir + "/obs_seq.final", fout)
    print(fout, "saved.")

    archive_assim = cluster.archivedir + time.strftime(pattern_init_time+"/assim_stage0/")
    mkdir(archive_assim)

    # copy input.nml to archive
    copy(cluster.dart_rundir + "/input.nml", archive_assim + "/input.nml")

    # copy filter_restart files to archive (initial condition for next run)
    for iens in range(1, exp.n_ens + 1):  # single members
        copy(
            cluster.dart_rundir + "/filter_restart_d01." + str(iens).zfill(4),
            archive_assim + "/filter_restart_d01." + str(iens).zfill(4),
        )

    # copy preassim/postassim files to archive (not necessary for next forecast run)
    try:  
        ftypes = ['preassim', 'postassim']
        for ftype in ftypes:
            for iens in range(1, exp.n_ens + 1):
                fname = "/"+ftype+"_member_" + str(iens).zfill(4) + ".nc"
                copy(cluster.dart_rundir + fname, archive_assim + fname)

        for f in ["output_mean.nc", "output_sd.nc"]:  # copy mean and sd to archive
            copy(cluster.dart_rundir + "/" + f, archive_assim + "/" + f)

    except Exception as e:
        warnings.warn(str(e))

def get_parametrized_error(obscfg, osf_prior):
    """Calculate the parametrized error for an ObsConfig (one obs type)

    Args:
        obscfg (object): Configuration of observations
        osf_prior (obsseq.ObsRecord): Contains truth and prior values from obs_seq.final
                                        (output of ./final in evaluate-mode (no posterior))

    Returns:
        np.array: observation error std-dev for assimilation
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


def set_obserr_assimilate_in_obsseqout(oso, outfile="./obs_seq.out"):
    """"Overwrite existing variance values in obs_seq.out files
    
    Args:
        oso (ObsSeq): python representation of obs_seq.out file, will be modified and written to file

    Returns:
        None    (writes to file)

    Variables:
        osf_prior (ObsSeq): python representation of obs_seq.final (output of filter in evaluate-mode without posterior)
                        contains prior values; used for parameterized errors
    """
    from dartwrf.obs.obskind import obs_kind_nrs

    for obscfg in exp.observations:
        kind_str = obscfg['kind']  # e.g. 'RADIOSONDE_TEMPERATURE'
        kind = obs_kind_nrs[kind_str]  # e.g. 263

        # modify observation error of each kind sequentially
        where_oso_iskind = oso.df.kind == kind
        
        if obscfg["error_assimilate"] == False:
            osf_prior = obsseq.ObsSeq(cluster.dart_rundir + "/obs_seq.final")  # this file will be generated by `evaluate()`
            
            where_osf_iskind = osf_prior.df.kind == kind

            assim_err = get_parametrized_error(obscfg, osf_prior.df[where_osf_iskind])
            oso.df.loc[where_oso_iskind, 'variance'] = assim_err**2
            #assert np.allclose(assim_err, oso.df['variance']**2)  # check
        else:
            # overwrite with user-defined values
            oso.df.loc[where_oso_iskind, 'variance'] = obscfg["error_assimilate"]**2

    oso.to_dart(outfile)

def qc_obs(time, oso):
    """Quality control of observations
    We assume that the prior values have been evaluated and are in `run_DART/obs_seq.final`
    
    Args:
        time (datetime): time of the assimilation
        oso (ObsSeq): python representation of obs_seq.out file, will be modified and written to file
    
    Returns:
        None    (writes to file)
        The pre-existing obs_seq.out will be archived.
        The new obs_seq.out will be written to the DART run directory.
    """
    osf_prior = obsseq.ObsSeq(cluster.dart_rundir + "/obs_seq.final")

    # obs should be superobbed already!
    for i, obscfg in enumerate(exp.observations): 
        if i > 0:
            raise NotImplementedError('Multiple observation types -> might not work')

        obs = oso.df.observations.values
        Hx_prior_mean = osf_prior.df['prior ensemble mean']
        n_obs_orig = len(obs)

        if obscfg.get("sat_channel") == 1:

            if True:
                print('removing obs with abs(FGD) < 0.03')
                Hx_prior = osf_prior.df.get_prior_Hx().T
                Hx_prior_mean = np.mean(Hx_prior, axis=0)
                #Hx_prior_spread = osf_prior.df['prior ensemble spread'].values
                #Hx_prior_spread[Hx_prior_spread < 1e-9] = 1e-9

                abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
                oso.df = oso.df[abs_FGD > 0.03]  # Hx_prior_spread]

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

        # archive obs_seq.out before QC (contains all observations, including later removed ones)
        f_out_archive = cluster.archivedir + "/obs_seq_out/" + time.strftime(pattern_obs_seq_out+"-beforeQC")
        os.makedirs(cluster.archivedir + "/obs_seq_out/", exist_ok=True)
        copy(cluster.dart_rundir + "/obs_seq.out", f_out_archive)

        # for assimilation later
        f_out_dart = cluster.dart_rundir+'/obs_seq.out'
        oso.to_dart(f_out_dart)
        print('saved', f_out_dart)


def evaluate(assim_time, 
             obs_seq_out=False,
             prior_is_filter_output=False,
             output_format=pattern_obs_seq_final+"-evaluate",
             nproc=12):
    """Calculates either prior or posterior obs space values.

    Note: Depends on a prepared input_list.txt, which defines the ensemble (prior or posterior).

    Output file: Saves obs_seq.final to `/archivedir/obs_seq_final/`

    Args:
        assim_time (datetime): time of assimilation
        obs_seq_out (str, optional):    use the argument as obs_seq.out file, defaults to use the existing obs_seq.out file
        output_format (str, optional): format string for output filename, default is `"%Y-%m-%d_%H:%M_obs_seq.final-eval_posterior_allobs"`

    Returns:
        obsseq.ObsSeq
    """
    os.makedirs(cluster.dart_rundir, exist_ok=True)  # create directory to run DART in
    os.chdir(cluster.dart_rundir)

    link_DART_binaries_and_RTTOV_files() 

    # remove any existing observation files
    os.system("rm -f input.nml obs_seq.final")  

    print("prepare nature")
    prepare_nature_dart(assim_time)  # link WRF files to DART directory

    if prior_is_filter_output:
        print('using filter_restart files from last assimilation as prior')
        use_filter_output_as_prior(assim_time)
    else:
        print('using files linked to `run_DART/<exp>/prior_ens*/wrfout_d01` as prior')
        use_linked_files_as_prior()

    if obs_seq_out:
        copy(obs_seq_out, cluster.dart_rundir+'/obs_seq.out')
    else:
        # use existing obs_seq.out file
        if not os.path.isfile(cluster.dart_rundir+'/obs_seq.out'):
            raise RuntimeError(cluster.dart_rundir+'/obs_seq.out does not exist')

    dart_nml.write_namelist(just_prior_values=True)
    filter(nproc=nproc)

    # archiving
    fout = cluster.archivedir + "/obs_seq_final/" + assim_time.strftime(output_format)
    os.makedirs(cluster.archivedir + "/obs_seq_final/", exist_ok=True)
    copy(cluster.dart_rundir + "/obs_seq.final", fout)
    print(fout, "saved.")

def get_obsseq_out(time):
    """Prepares an obs_seq.out file in the run_DART folder

    Args:
        time (datetime): time of assimilation

    Returns:
        obsseq.ObsSeq
    """
    if exp.use_existing_obsseq != False: 
        # use an existing obs_seq.out file
        f_obsseq = time.strftime(exp.use_existing_obsseq)
        copy(f_obsseq, cluster.dart_rundir+'/obs_seq.out')  # copy to run_DART folder        
        print(f_obsseq, 'copied to', cluster.dart_rundir+'/obs_seq.out')

        # copy to sim_archive
        os.makedirs(cluster.archivedir + "/obs_seq_out/", exist_ok=True)
        copy(f_obsseq,  time.strftime(cluster.archivedir+'/obs_seq_out/'+pattern_obs_seq_out))

        oso = obsseq.ObsSeq(cluster.dart_rundir + "/obs_seq.out")  # read the obs_seq.out file
    else: 
        # do NOT use an existing obs_seq.out file
        # but generate observations with new observation noise
        oso = osq_out.generate_obsseq_out(time)
    return oso

def prepare_inflation_2(time, prior_init_time):
    """Prepare inflation files (spatially varying)
    
    Recycles inflation files from previous assimilations
    or takes default files from archive.
    
    Args:
        time (datetime): time of assimilation
        prior_init_time (datetime): time of prior assimilation
    """
    dir_priorinf = cluster.archivedir + prior_init_time.strftime(pattern_init_time+"/assim_stage0/") 

    f_default = cluster.archive_base + "/input_priorinf_mean.nc"
    f_prior = dir_priorinf + time.strftime("/%Y-%m-%d_%H:%M_output_priorinf_mean.nc")
    f_new = cluster.dart_rundir + '/input_priorinf_mean.nc'

    if os.path.isfile(f_prior):
        copy(f_prior, f_new)
        print(f_prior, 'copied to', f_new)
    else:  # no prior inflation file at the first assimilation
        warnings.warn(f_prior + ' does not exist. Using default file instead.')
        copy(f_default, f_new)

    f_default = cluster.archive_base + "/input_priorinf_sd.nc"
    f_prior = dir_priorinf + time.strftime("/%Y-%m-%d_%H:%M_output_priorinf_sd.nc")
    f_new = cluster.dart_rundir + '/input_priorinf_sd.nc'

    if os.path.isfile(f_prior):
        copy(f_prior, f_new)
        print(f_prior, 'copied to', f_new)
    else:
        warnings.warn(f_prior + ' does not exist. Using default file instead.')
        copy(f_default, f_new)

def archive_inflation_2(time):
    dir_output = cluster.archivedir + time.strftime(pattern_init_time+"/assim_stage0/")
    os.makedirs(dir_output, exist_ok=True)

    f_output = cluster.dart_rundir + '/output_priorinf_sd.nc'
    f_archive = dir_output + time.strftime("/%Y-%m-%d_%H:%M_output_priorinf_sd.nc")
    copy(f_output, f_archive)
    print(f_archive, 'saved')

    f_output = cluster.dart_rundir + '/output_priorinf_mean.nc'
    f_archive = dir_output + time.strftime("/%Y-%m-%d_%H:%M_output_priorinf_mean.nc")
    copy(f_output, f_archive)
    print(f_archive, 'saved')

def link_DART_binaries_and_RTTOV_files():
    joinp = os.path.join

    # link DART binaries
    bins = ['perfect_model_obs', 'filter', 'obs_diag', 'obs_seq_to_netcdf']
    for b in bins:
            symlink(joinp(cluster.dart_srcdir, b),
                    joinp(cluster.dart_rundir, b))

    # link RTTOV files
    rttov_files = ['rttov13pred54L/rtcoef_msg_4_seviri_o3.dat', 
                    'mfasis_lut/rttov_mfasis_cld_msg_4_seviri_deff.H5',
                    'cldaer_visir/sccldcoef_msg_4_seviri.dat']

    try:  # may fail quietly if we dont need RTTOV
        for f_src in rttov_files:
                destname = os.path.basename(f_src)
                if 'rtcoef' in f_src:
                        destname = 'rtcoef_msg_4_seviri.dat'

                symlink(cluster.rttov_srcdir + f_src, 
                        cluster.dart_rundir+'/'+destname)

        symlink(cluster.dart_rundir+'/rttov_mfasis_cld_msg_4_seviri_deff.H5', 
                cluster.dart_rundir+'/rttov_mfasis_cld_msg_4_seviri.H5')  # use deff, not OPAC

        symlink(cluster.dart_srcdir+'/../../../observations/forward_operators/rttov_sensor_db.csv',
                cluster.dart_rundir+'/rttov_sensor_db.csv')

        symlink(cluster.dart_srcdir+'/../../../assimilation_code/programs/gen_sampling_err_table/'
                +'work/sampling_error_correction_table.nc',
                cluster.dart_rundir+'/sampling_error_correction_table.nc')

        print('prepared DART & RTTOV links in', cluster.dart_rundir)
    except Exception as e:
        if any(['sat_channel' in obscfg for obscfg in exp.observations]):
            raise e
        else:
            pass  # we dont need RTTOV anyway

def prepare_run_DART_folder():
    os.makedirs(cluster.dart_rundir, exist_ok=True)  # create directory to run DART in
    os.chdir(cluster.dart_rundir)

    link_DART_binaries_and_RTTOV_files()

    # remove any existing observation files
    os.system("rm -f input.nml obs_seq.in obs_seq.out obs_seq.out-orig obs_seq.final")  


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
    do_QC = getattr(exp, "do_quality_control", False)  # True: triggers additional evaluations of prior & posterior

    # for which observation type do we have a parametrized observation error?
    error_is_parametrized = [obscfg["error_assimilate"] == False for obscfg in exp.observations]

    prepare_run_DART_folder()
    nml = dart_nml.write_namelist()
    prior_inflation_type = nml['&filter_nml']['inf_flavor'][0][0]

    print("prepare nature")
    prepare_nature_dart(time)  # link WRF files to DART directory

    print("prepare prior ensemble")
    prepare_prior_ensemble(time, prior_init_time, prior_valid_time, prior_path_exp)
    
    print(" get observations with specified obs-error")
    oso = get_obsseq_out(time)

    # is any observation error parametrized?
    if any(error_is_parametrized) or do_QC:
        print(" (optional) evaluate prior for all observations (incl rejected) ")
        evaluate(time, output_format=pattern_obs_seq_final+"-evaluate_prior")

    print(" assign observation-errors for assimilation ")
    set_obserr_assimilate_in_obsseqout(oso, outfile=cluster.dart_rundir + "/obs_seq.out")

    if do_QC:
        print(" reject observations? ")
        qc_obs(time, oso)

    if prior_inflation_type == '2':
        prepare_inflation_2(time, prior_init_time)

    print(" run filter ")
    dart_nml.write_namelist()
    filter(nproc=nproc)
    archive_filteroutput(time)

    if prior_inflation_type == '2':
        archive_inflation_2(time)

    print(" evaluate posterior in observation-space")
    f_oso = pattern_obs_seq_out
    if do_QC:
        f_oso += '-beforeQC'  # includes all observations (including rejected ones in qc_obs())

    # evaluate() separately after ./filter is crucial when assimilating cloud variables
    # as the obs_seq.final returned by ./filter was produced using un-clamped cloud variables
    evaluate(time, obs_seq_out=cluster.archivedir+'/obs_seq_out/'+time.strftime(f_oso),
             prior_is_filter_output=True,
             output_format=pattern_obs_seq_final+"-evaluate")


if __name__ == "__main__":
    """Assimilate synthetic observations
    
    Example:
        python assim_synth_obs.py 2008-08-07_13:00 2008-08_12:00 2008-08-07_13:00 /path/to/experiment/
    """

    time = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d_%H:%M")
    prior_init_time = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d_%H:%M")
    prior_valid_time = dt.datetime.strptime(sys.argv[3], "%Y-%m-%d_%H:%M")
    prior_path_exp = str(sys.argv[4])

    main(time, prior_init_time, prior_valid_time, prior_path_exp)
