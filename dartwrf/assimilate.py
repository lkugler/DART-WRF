import os
import sys
import shutil
import warnings
import glob
import time as time_module
import datetime as dt
import numpy as np

from dartwrf.utils import Config, symlink, copy, try_remove, print, shell, write_txt, obskind_read
from dartwrf import wrfout_add_geo
from dartwrf.obs import error_models as err
from dartwrf.obs import obsseq
from dartwrf import dart_nml


def prepare_DART_grid_template(cfg):
    """Prepare DART grid template wrfinput_d01 file from a prior file
    
    DART needs a wrfinput file as a template for the grid information.
    No data except grid info will be read from this file.
    The grid information must match exactly with the prior file "wrfout_d01"
    """
    f_wrfout_dummy = cfg.dir_dart_run+'/prior_ens1/wrfout_d01'
    if os.path.exists(f_wrfout_dummy):
        copy(f_wrfout_dummy, cfg.dir_dart_run + "/wrfinput_d01")
    
        if cfg.geo_em_forecast:
            wrfout_add_geo.run(cfg, cfg.geo_em_forecast, cfg.dir_dart_run + "/wrfinput_d01")
    else:
        pass # what now?

def prepare_prior_ensemble(cfg, assim_time, prior_init_time, prior_valid_time, prior_path_exp):
    """Prepares DART files for running filter
    i.e.
    - links first guess state to DART first guess filenames
    - creates wrfinput_d01 files (grid file, not a real wrfinput file)
    - adds geo-reference (xlat,xlon) coords so that DART can deal with the files
    - writes txt files so DART knows what input and output is
    - removes probably pre-existing files which could lead to problems
    """
    print("prepare prior ensemble")
    for iens in range(1, cfg.ensemble_size + 1):

        print("link wrfout file to DART background file")
        f_wrfout = (
            prior_path_exp
            + prior_init_time.strftime(cfg.pattern_init_time)
            + str(iens)
            + prior_valid_time.strftime(cfg.wrfout_format)
        )
        dart_ensdir = cfg.dir_dart_run + "/prior_ens" + str(iens)
        wrfout_dart = dart_ensdir + "/wrfout_d01"

        # copy prior ens file from archived wrfout files (prior_path_exp)
        print("link", f_wrfout, "to", wrfout_dart)
        if not os.path.isfile(f_wrfout):
            raise FileNotFoundError(f_wrfout + " does not exist")
        symlink(f_wrfout, wrfout_dart)

        # ensure prior time matches assim time
        # can be intentionally different, e.g. by using a prior for a different time
        if assim_time != prior_valid_time:
            copy(f_wrfout, wrfout_dart)
            print("overwriting time in prior from nature wrfout")
            shell(cfg.ncks + " -A -v XTIME,Times " +
                  cfg.dir_dart_run+"/wrfout_d01 " + wrfout_dart)

        # this seems to be necessary (else wrong level selection)
        #if cluster.geo_em_forecast:
        #    wrfout_add_geo.run(cluster.geo_em_forecast, wrfout_dart)

    use_linked_files_as_prior(cfg)
    write_list_of_outputfiles(cfg)

    print("removing preassim and filter_restart")
    os.system("rm -rf " + cfg.dir_dart_run + "/preassim_*")
    os.system("rm -rf " + cfg.dir_dart_run + "/filter_restart*")
    os.system("rm -rf " + cfg.dir_dart_run + "/output_mean*")
    os.system("rm -rf " + cfg.dir_dart_run + "/output_sd*")
    os.system("rm -rf " + cfg.dir_dart_run + "/perfect_output_*")
    os.system("rm -rf " + cfg.dir_dart_run + "/obs_seq.fina*")


def use_linked_files_as_prior(cfg):
    """Instruct DART to use the prior ensemble as input
    """
    files = []
    for iens in range(1, cfg.ensemble_size+1):
        files.append("./prior_ens" + str(iens) + "/wrfout_d01")
    write_txt(files, cfg.dir_dart_run+'/input_list.txt')


def use_filter_output_as_prior(cfg):
    """Use the last posterior as input for DART, e.g. to evaluate the analysis in observation space
    """
    files = []
    for iens in range(1, cfg.ensemble_size+1):
        f_new = cfg.dir_dart_run+'/prior_ens'+str(iens)+'/wrfout_d01'
        try:
            os.remove(f_new)
        except:
            pass
        os.rename(cfg.dir_dart_run+'/filter_restart_d01.' +
                  str(iens).zfill(4), f_new)
        files.append(f_new)

    write_txt(files, cfg.dir_dart_run+'/input_list.txt')


def write_list_of_outputfiles(cfg):
    files = []
    for iens in range(1, cfg.ensemble_size+1):
        files.append("./filter_restart_d01." + str(iens).zfill(4))
    write_txt(files, cfg.dir_dart_run+'/output_list.txt')


def filter(cfg):
    """Calls DART ./filter program

    Args:
        nproc (int): number of cores for use in ./filter call

    Returns:
        None    (writes to file)
    """
    nproc = cfg.max_nproc
        
    print("time now", dt.datetime.now())
    print("running filter")
    os.chdir(cfg.dir_dart_run)
    try_remove(cfg.dir_dart_run + "/obs_seq.final")

    t = time_module.time()
    if nproc > 1:
        # -genv I_MPI_PIN_PROCESSOR_LIST=0-"+str(int(nproc) - 1)
        shell(cfg.dart_modules+"; mpirun -np " +
              str(int(nproc))+" ./filter > log.filter")
    else:
        shell(cfg.dart_modules+"; ./filter > log.filter")
    print("./filter took", int(time_module.time() - t), "seconds")

    if not os.path.isfile(cfg.dir_dart_run + "/obs_seq.final"):
        raise RuntimeError(
            "obs_seq.final does not exist in run_DART directory. ",
            "Check log file at " + cfg.dir_dart_run + "/log.filter")


def archive_filteroutput(cfg, time):
    """Archive filter output files (filter_restart, preassim, postassim, output_mean, output_sd)
    """
    # archive diagnostics
    dir_out = cfg.dir_archive + time.strftime(cfg.pattern_init_time)
    os.makedirs(dir_out, exist_ok=True)

    # copy input.nml to archive
    copy(cfg.dir_dart_run + "/input.nml", dir_out + "/input.nml")

    # copy filter_restart files to archive (initial condition for next run)
    for iens in range(1, cfg.ensemble_size + 1):  # single members
        copy(
            cfg.dir_dart_run + "/filter_restart_d01." + str(iens).zfill(4),
            dir_out + "/filter_restart_d01." + str(iens).zfill(4),
        )

    # copy preassim/postassim files to archive (not necessary for next forecast run)
    for f in ["preassim_mean.nc", "preassim_sd.nc",
              "postassim_mean.nc", "postassim_sd.nc",
              "output_mean.nc", "output_sd.nc"]:
        try:
            copy(cfg.dir_dart_run + "/" + f, dir_out + "/" + f)
        except:
            warnings.warn(f+" not found")

    if False:  # save disk space, dont do this by default
        try:
            ftypes = ['preassim', 'postassim']
            for ftype in ftypes:
                for iens in range(1, cfg.ensemble_size + 1):
                    fname = "/"+ftype+"_member_" + str(iens).zfill(4) + ".nc"
                    copy(cfg.dir_dart_run + fname, dir_out + fname)
        except Exception as e:
            warnings.warn(str(e))


def get_parametrized_error(obscfg, osf_prior) -> np.ndarray: # type: ignore
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
        NotImplementedError('sat_channel not implemented',
                            obscfg.get("sat_channel"))
    

def set_obserr_assimilate_in_obsseqout(cfg, oso, outfile="./obs_seq.out"):
    """"Overwrite existing variance values in obs_seq.out files

    Args:
        oso (ObsSeq): python representation of obs_seq.out file, will be modified and written to file

    Returns:
        None    (writes to file)

    Variables:
        osf_prior (ObsSeq): python representation of obs_seq.final (output of filter in evaluate-mode without posterior)
                        contains prior values; used for parameterized errors
    """

    for obscfg in cfg.assimilate_these_observations:
        kind_str = obscfg['kind']  # e.g. 'RADIOSONDE_TEMPERATURE'
        kind = cfg.obs_kind_nrs[kind_str]  # e.g. 263

        # modify observation error of each kind sequentially
        where_oso_iskind = oso.df.kind == kind

        if "error_assimilate" in obscfg:
            if obscfg["error_assimilate"]  == False:
                print("error_assimilate is False, will compute dynamic obs-errors")
                # get a parametrized error for this observation type
                
                # parametrization is state dependent => need states
                use_external_FO = obscfg.get("external_FO", False)
                if use_external_FO:
                    # read prior from obs_seq.out
                    pass
                    
                    # modify OE in obs_seq.out
                    pass
                else:
                    f_osf = cfg.dir_dart_run + "/obs_seq.final"
                    if not os.path.isfile(f_osf):
                        print('computing prior as input for dynamic obs errors')
                        # generates obs_seq.final
                        evaluate(cfg, cfg.time, f_out_pattern=f_osf)

                    # read prior (obs_seq.final)
                    osf_prior = obsseq.ObsSeq(f_osf)
                    where_osf_iskind = osf_prior.df.kind == kind

                    assim_err = get_parametrized_error(
                        obscfg, osf_prior.df[where_osf_iskind])
                    oso.df.loc[where_oso_iskind, 'variance'] = assim_err**2
                    # assert np.allclose(assim_err, oso.df['variance']**2)  # check
            else:
                # overwrite with user-defined values
                oso.df.loc[where_oso_iskind,
                            'variance'] = obscfg["error_assimilate"]**2

    oso.to_dart(outfile)


def reject_small_FGD(cfg, time, oso):
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
    osf_prior = obsseq.ObsSeq(cfg.dir_dart_run + "/obs_seq.final")

    # obs should be superobbed already!
    for i, obscfg in enumerate(cfg.assimilate_these_observations):
        if i > 0:
            raise NotImplementedError(
                'Multiple observation types -> might not work')

        obs = oso.df.observations.values
        Hx_prior_mean = osf_prior.df['prior ensemble mean']
        n_obs_orig = len(obs)

        if obscfg.get("sat_channel") == 1:

            if True:
                print('removing obs with abs(FGD) < 0.03')
                Hx_prior = osf_prior.df.get_prior_Hx().T
                Hx_prior_mean = np.mean(Hx_prior, axis=0)
                # Hx_prior_spread = osf_prior.df['prior ensemble spread'].values
                # Hx_prior_spread[Hx_prior_spread < 1e-9] = 1e-9

                abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
                oso.df = oso.df[abs_FGD > 0.03]  # Hx_prior_spread]

                # obs_dist_to_priormean = abs(obs - Hx_prior_mean)
                # oso.df = oso.df[obs_dist_to_priormean > 5]
                # print('removed', n_obs_orig-len(oso.df), 'observations with abs(FGD) smaller than 5')

            else:
                # set obs to prior mean => no change in mean but spread is adjusted.
                abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
                Hx_prior_median = np.median(
                    osf_prior.df.get_prior_Hx(), axis=1)
                oso.df.loc[abs_FGD <= 0.05,
                           'observations'] = Hx_prior_median[abs_FGD <= 0.05]

        elif obscfg.get("sat_channel") == 6:  # WV73

            print('removing obs with abs(FGD) smaller than 5')
            obs = oso.df.observations.values
            n_obs_orig = len(obs)

            abs_FGD = abs(obs - Hx_prior_mean)  # /Hx_prior_spread
            oso.df = oso.df[abs_FGD > 5]
        else:
            raise NotImplementedError(
                'no obs QC implemented for this obs type')

        print('QC removed', n_obs_orig-len(oso.df), 'observations')

        # archive obs_seq.out before QC (contains all observations, including later removed ones)
        f_out_archive = time.strftime(cfg.pattern_obs_seq_out)+"-beforeQC"
        os.makedirs(os.path.dirname(f_out_archive), exist_ok=True)
        copy(cfg.dir_dart_run + "/obs_seq.out", f_out_archive)

        # for assimilation later
        f_out_dart = cfg.dir_dart_run+'/obs_seq.out'
        oso.to_dart(f_out_dart)
        print('saved', f_out_dart)


def evaluate(cfg, assim_time,
             obs_seq_out=False,
             prior_is_filter_output=False,
             f_out_pattern: str = './obs_seq.final'):
    """Calculates either prior or posterior obs space values.

    Note: Depends on a prepared input_list.txt, which defines the ensemble (prior or posterior).

    Output file: Saves obs_seq.final to `/archivedir/obs_seq_final/`

    Args:
        assim_time (datetime): time of assimilation
        obs_seq_out (str, optional):    use the argument as obs_seq.out file, defaults to use the existing obs_seq.out file
                                        at these observations, the posterior will be evaluated
        f_out_pattern (str, mandatory): output filename
        prior_is_filter_output (bool, optional): if True, use the filter output as prior, else use already linked ensemble files

    Returns
        None (writes file)
    """
    prepare_run_DART_folder(cfg)

    if prior_is_filter_output:
        print('using filter_restart files in run_DART as prior')
        use_filter_output_as_prior(cfg)
    else:
        print('using files linked to `run_DART/<exp>/prior_ens*/wrfout_d01` as prior')
        use_linked_files_as_prior(cfg)

    # the observations at which to evaluate the prior at
    if obs_seq_out:
        copy(obs_seq_out, cfg.dir_dart_run + '/obs_seq.out')  # user defined file
    else:
        # use existing obs_seq.out file currently present in the run_DART directory
        if not os.path.isfile(cfg.dir_dart_run+'/obs_seq.out'):
            raise RuntimeError(cfg.dir_dart_run +
                               '/obs_seq.out does not exist')

    dart_nml.write_namelist(cfg, just_prior_values=True)
    filter(cfg)
    archive_filter_diagnostics(cfg, assim_time, f_out_pattern)


def archive_filter_diagnostics(cfg, time, f_out_pattern):
    """Copy the filter output txt to the archive
    """
    f_archive = time.strftime(f_out_pattern)

    dir_out = os.path.dirname(f_archive)
    os.makedirs(dir_out, exist_ok=True)
    copy(cfg.dir_dart_run + "/obs_seq.final", f_archive)
    print(f_archive, "saved.")


def txtlink_to_prior(cfg, time, prior_init_time, prior_path_exp):
    """For reproducibility, write the path of the prior to a txt file
    """
    os.makedirs(cfg.dir_archive +
                time.strftime('/%Y-%m-%d_%H:%M/'), exist_ok=True)
    os.system('echo "'+prior_path_exp+'\n'+prior_init_time.strftime('/%Y-%m-%d_%H:%M/')
              + '\n'+time.strftime('/wrfrst_d01_%Y-%m-%d_%H:%M:%S')+'" > '
                + cfg.dir_archive + time.strftime('/%Y-%m-%d_%H:%M/')+'link_to_prior.txt')


def prepare_adapt_inflation(cfg, time, prior_init_time):
    """Prepare inflation files (spatially varying)

    Recycles inflation files from previous assimilations
    or takes default files from archive.

    Args:
        time (datetime): time of assimilation
        prior_init_time (datetime): time of prior assimilation
    """
    dir_priorinf = cfg.dir_archive + \
        prior_init_time.strftime(cfg.pattern_init_time)

    f_prior = dir_priorinf + \
        time.strftime("/%Y-%m-%d_%H:%M_output_priorinf_mean.nc")
    f_new = cfg.dir_dart_run + '/input_priorinf_mean.nc'

    if os.path.isfile(f_prior):
        copy(f_prior, f_new)
        print(f_prior, 'copied to', f_new)
    else:  
        # no prior inflation file at the first assimilation
        warnings.warn(f_prior + ' does not exist. Using default file instead.')
        f_default = cfg.dir_archive+"/../input_priorinf_mean.nc"
        copy(f_default, f_new)


    f_prior = dir_priorinf + \
        time.strftime("/%Y-%m-%d_%H:%M_output_priorinf_sd.nc")
    f_new = cfg.dir_dart_run + '/input_priorinf_sd.nc'

    if os.path.isfile(f_prior):
        copy(f_prior, f_new)
        print(f_prior, 'copied to', f_new)
    else:
        # no prior inflation file at the first assimilation
        warnings.warn(f_prior + ' does not exist. Using default file instead.')
        f_default = cfg.dir_archive + "/../input_priorinf_sd.nc"
        copy(f_default, f_new)


def archive_adapt_inflation(cfg, time):
    dir_output = cfg.dir_archive + time.strftime(cfg.pattern_init_time)
    os.makedirs(dir_output, exist_ok=True)

    f_output = cfg.dir_dart_run + '/output_priorinf_sd.nc'
    f_archive = dir_output + \
        time.strftime("/%Y-%m-%d_%H:%M_output_priorinf_sd.nc")
    copy(f_output, f_archive)
    print(f_archive, 'saved')

    f_output = cfg.dir_dart_run + '/output_priorinf_mean.nc'
    f_archive = dir_output + \
        time.strftime("/%Y-%m-%d_%H:%M_output_priorinf_mean.nc")
    copy(f_output, f_archive)
    print(f_archive, 'saved')


def prepare_run_DART_folder(cfg: Config):
    # create directory to run DART in

    def __link_RTTOV_files():
        """Link required files for running RTTOV to run_DART
        """
        if cfg.dir_rttov_src != False:
            rttov_files = ['rttov13pred54L/rtcoef_msg_4_seviri_o3.dat',
                        'mfasis_lut/rttov_mfasis_cld_msg_4_seviri_deff.H5',
                        'cldaer_visir/sccldcoef_msg_4_seviri.dat']

            for f_src in rttov_files:
                destname = os.path.basename(f_src)
                if 'rtcoef' in f_src:
                    destname = 'rtcoef_msg_4_seviri.dat'

                symlink(cfg.dir_rttov_src + f_src,
                        cfg.dir_dart_run+'/'+destname)

            symlink(cfg.dir_dart_run+'/rttov_mfasis_cld_msg_4_seviri_deff.H5',
                    cfg.dir_dart_run+'/rttov_mfasis_cld_msg_4_seviri.H5')  # use deff, not OPAC

            symlink(cfg.dir_dart_src+'/../../../observations/forward_operators/rttov_sensor_db.csv',
                    cfg.dir_dart_run+'/rttov_sensor_db.csv')
            
    def __link_DART_exe():
        """Link the DART executables to the run_DART directory
        """
        bins = ['perfect_model_obs', 'filter', 'obs_diag', 'obs_seq_to_netcdf']
        for b in bins:
            symlink(os.path.join(cfg.dir_dart_src, b),
                    os.path.join(cfg.dir_dart_run, b))

        symlink(cfg.dir_dart_src+'/../../../assimilation_code/programs/gen_sampling_err_table/'
                + 'work/sampling_error_correction_table.nc',
                cfg.dir_dart_run+'/sampling_error_correction_table.nc')
    
    #########################
    # remove any remains of a previous run
    os.makedirs(cfg.dir_dart_run, exist_ok=True)
    os.chdir(cfg.dir_dart_run)
    os.system("rm -f input.nml obs_seq.in obs_seq.out-orig obs_seq.final")
    
    __link_DART_exe()
    
    for obscfg in cfg.assimilate_these_observations:
        if 'sat_channel' in obscfg:
            __link_RTTOV_files()
            continue  # only need to link RTTOV files once


def get_obsseq_out(cfg, time, prior_path_exp, prior_init_time, prior_valid_time):
    """Prepares an obs_seq.out file in the run_DART folder

    Options:
    1) Use existing obs_seq.out file
    2) Use precomputed FO (e.g. cloud fraction)
    3) Generate new observations from nature run with new noise

    Args:
        time (datetime): time of assimilation
        prior_path_exp (str): path to the experiment folder
        prior_init_time (datetime): time of the prior forecast init
        prior_valid_time (datetime): time of the prior

    Returns:
        obsseq.ObsSeq
    """
    use_ACF = False
    if 'assimilate_cloudfractions' in cfg:
        if cfg.assimilate_cloudfractions:
            use_ACF = True

    oso = None
    if isinstance(cfg.assimilate_existing_obsseq, str):
        # assume that the user wants to use an existing obs_seq.out file

        f_obsseq = time.strftime(cfg.assimilate_existing_obsseq)
        if os.path.isfile(f_obsseq):
            # copy to run_DART folder
            copy(f_obsseq, cfg.dir_dart_run+'/obs_seq.out')
            print(f_obsseq, 'copied to', cfg.dir_dart_run+'/obs_seq.out')

        else:
            # explain the error if the file does not exist
            raise IOError('cfg.assimilate_existing_obsseq is not False. \n'
                          + 'In this case, assimilate_existing_obsseq should be a file path (wildcards %H, %M allowed)!\n'
                          + 'But there is no file with this pattern: '+str(cfg.assimilate_existing_obsseq))

    elif use_ACF:
        # prepare observations with precomputed FO
        CF_config = cfg.CF_config.copy()
        f_prior_pattern = CF_config.pop('first_guess_pattern')
        f_obs_pattern = time.strftime(CF_config.pop('f_obs_pattern'))
        f_obs = glob.glob(f_obs_pattern)
        if len(f_obs) == 0:
            raise FileNotFoundError(f_obs_pattern + ' not found')
        f_obs = f_obs[0]
        
        pattern_prior = '/'.join([prior_path_exp,
                                  prior_init_time.strftime('/%Y-%m-%d_%H:%M/'),
                                  '<iens>/',
                                  prior_valid_time.strftime(f_prior_pattern),
                                  ])

        from CloudFractionDA import obsseqout as cfoso
        cfoso.write_obsseq(time, pattern_prior, f_obs,
                           cfg.obs_kind_nrs,
                           path_output = cfg.dir_dart_run + "/obs_seq.out",
                           **CF_config,
                           
        )

    else:
        # do NOT use an existing obs_seq.out file
        # but generate observations with new observation noise
        from dartwrf.obs import create_obsseq_out as osq_out
        oso = osq_out.generate_new_obsseq_out(cfg)

    # copy to sim_archive
    f_obsseq_archive = time.strftime(cfg.pattern_obs_seq_out)
    os.makedirs(os.path.dirname(f_obsseq_archive), exist_ok=True)
    copy(cfg.dir_dart_run+'/obs_seq.out', f_obsseq_archive)

    # read so that we can return it
    if oso is None:
        oso = obsseq.ObsSeq(cfg.dir_dart_run + "/obs_seq.out")
    return oso


def main(cfg: Config):
    """Assimilate observations
    as defined in config/cfg.py
    for a certain timestamp (argument) of the nature run (defined in config/clusters.py)

    Workflow:
    1) prepare nature run & prior ensemble for DART
    2) create obs_seq.in
    3) create obs from nature (obs_seq.out) or use existing one
    optional: quality-control
    4) Assimilate with assigned errors
    5) Evaluate posterior (after DART clamping, e.g. setting negative cloud water to zero)

    Args:
        assim_time (dt.datetime):           time of output
        prior_init_time (dt.datetime):      forecast start of prior
        prior_valid_time (dt.datetime):     valid time of prior (may be different to assim_time)
        prior_path_exp (str):               path to prior experiment

    Returns:
        None
    """
    # read config
    time = cfg.time
    prior_init_time = cfg.prior_init_time
    prior_valid_time = cfg.prior_valid_time
    prior_path_exp = cfg.prior_path_exp
    
    cfg.obs_kind_nrs = obskind_read(cfg.dir_dart_src)
    
    # do_reject_smallFGD: triggers additional evaluations of prior & posterior
    do_reject_smallFGD = getattr(cfg, "do_reject_smallFGD", False)
    prepare_run_DART_folder(cfg)
    nml = dart_nml.write_namelist(cfg)

    print(" get observations with specified obs-error")
    oso = get_obsseq_out(cfg, time, prior_path_exp, prior_init_time, prior_valid_time)
    
    # prepare for assimilation
    prepare_prior_ensemble(cfg, time, prior_init_time, prior_valid_time, prior_path_exp)
    prepare_DART_grid_template(cfg)

    # additional evaluation of prior (in case some observations are rejected)
    if do_reject_smallFGD:
        print(" evaluate prior for all observations (incl rejected) ")
        evaluate(cfg, time, f_out_pattern=cfg.pattern_obs_seq_final+"-evaluate_prior")

    print(" assign observation-errors for assimilation ")
    set_obserr_assimilate_in_obsseqout(cfg, oso, outfile=cfg.dir_dart_run + "/obs_seq.out")

    if do_reject_smallFGD:
        print(" reject observations? ")
        reject_small_FGD(cfg, time, oso)

    prior_inflation_type = nml['&filter_nml']['inf_flavor'][0][0]
    if prior_inflation_type != '0':
        prepare_adapt_inflation(cfg, time, prior_init_time)

    print(" run filter ")
    dart_nml.write_namelist(cfg)
    filter(cfg)
    archive_filteroutput(cfg, time)
    archive_filter_diagnostics(cfg, time, cfg.pattern_obs_seq_final)
    txtlink_to_prior(cfg, time, prior_init_time, prior_path_exp)

    if prior_inflation_type != '0':
        archive_adapt_inflation(cfg, time)

    if 'evaluate_posterior_in_obs_space' in cfg:
        if cfg.evaluate_posterior_in_obs_space:
            print(" evaluate posterior in observation-space")
            f_oso = time.strftime(cfg.pattern_obs_seq_out)
            if do_reject_smallFGD:
                # includes all observations (including rejected ones in reject_small_FGD())
                f_oso += '-beforeQC'

            # evaluate() separately after ./filter is crucial when assimilating cloud variables
            # as the obs_seq.final returned by ./filter was produced using un-clamped cloud variables
            evaluate(cfg, time,
                    obs_seq_out=f_oso,
                    prior_is_filter_output=True,
                    f_out_pattern=cfg.pattern_obs_seq_final+"-evaluate")


if __name__ == "__main__":
    """Assimilate observations

    Example:
        python assimilate.py 2008-08-07_13:00 2008-08_12:00 2008-08-07_13:00 /path/to/experiment/
    """
    cfg = Config.from_file(sys.argv[1])
    main(cfg)
