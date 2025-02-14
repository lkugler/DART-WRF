import os, sys
import shutil
import glob
import warnings

from dartwrf.utils import Config, try_remove, print, shell, symlink, copy, obskind_read
import dartwrf.obs.create_obsseq_in as osi
from dartwrf.obs import obsseq
from dartwrf import wrfout_add_geo


def prepare_nature_dart(cfg: Config):
    """Prepares DART nature (wrfout_d01) if available

    Args:
        time (dt.datetime): Time at which observations will be made
    """
    time = cfg.time
    
    def _find_nature(time):
        """Find the path to the nature file for the given time
        """
        glob_pattern = time.strftime(cfg.nature_wrfout_pattern)
        print('searching for nature in pattern:', glob_pattern)
        try:
            f_nat = glob.glob(glob_pattern)[0]  # find the nature wrfout-file
        except IndexError:
            raise IOError("no nature found with pattern "+glob_pattern)

        # check user input
        if not 'wrfout' in f_nat.split('/')[-1]:
            warnings.warn(
                f_nat+" does not contain 'wrfout' in filename, are you sure this is a valid nature file?")

        if not os.path.exists(f_nat):
            raise IOError(f_nat+" does not exist -> no nature found")
        
        print('using nature:', f_nat)
        return f_nat
    
    print("prepare nature")
    f_nat = _find_nature(time)
    # link nature wrfout to DART directory
    copy(f_nat, cfg.dir_dart_run + "/wrfout_d01")

    # add coordinates if necessary
    if cfg.geo_em_nature:
        wrfout_add_geo.run(cfg, cfg.geo_em_nature, cfg.dir_dart_run + "/wrfout_d01")
        
    # as a grid template
    symlink(cfg.dir_dart_run + "/wrfout_d01", cfg.dir_dart_run + "/wrfinput_d01")
    


def run_perfect_model_obs(cfg: Config):
    """Run the ./perfect_model_obs program

    Args:
        nproc (int): number of processors to use

    Returns:
        None, creates obs_seq.out
    """
    print("running ./perfect_model_obs")
    os.chdir(cfg.dir_dart_run)
    nproc = cfg.max_nproc

    try_remove(cfg.dir_dart_run + "/obs_seq.out")
    if not os.path.exists(cfg.dir_dart_run + "/obs_seq.in"):
        raise RuntimeError("obs_seq.in does not exist in " + cfg.dir_dart_run)
    
    shell(cfg.dart_modules+'; mpirun -np '+str(nproc) +
          " ./perfect_model_obs &> log.perfect_model_obs")
    
    if not os.path.exists(cfg.dir_dart_run + "/obs_seq.out"):
        raise RuntimeError(
            "obs_seq.out does not exist in " + cfg.dir_dart_run,
            ". See "+cfg.dir_dart_run + "/log.perfect_model_obs")


def generate_new_obsseq_out(cfg: Config):
    """Generate an obs_seq.out file from obs_seq.in
    Expects an existing nature file in the cluster.dart_rundir.

    Note:
        Combining precomputed FO with regular observations is not supported!

    Args:
        time (datetime): time of the observations
        nproc (int, optional): number of cores for call to ./perfect_model_obs

    Returns:
        obsseq.ObsSeq: obs_seq.out representation
    """
    time = cfg.time
    
    def __force_obs_in_physical_range(oso):
        """ Set values smaller than surface albedo to surface albedo
        Highly hacky. Your albedo might be different.
        """
        print(" removing obs below surface albedo ")
        clearsky_albedo = 0.2928  # custom value
        obs_kind_nrs = obskind_read(cfg.dir_dart_src)

        if_vis_obs = oso.df['kind'].values == obs_kind_nrs['MSG_4_SEVIRI_BDRF']
        if_obs_below_surface_albedo = oso.df['observations'].values < clearsky_albedo
        oso.df.loc[if_vis_obs & if_obs_below_surface_albedo,
                ('observations')] = clearsky_albedo
        oso.to_dart(f=cfg.dir_dart_run + "/obs_seq.out")
        return oso

    def __provide_obs_seq_in(cfg: Config):
        if hasattr(cfg, 'use_this_obs_seq_in'):
            # custom definition of an obs_seq.in file
            print("using obs_seq.in:", cfg.use_this_obs_seq_in)
            copy(cfg.use_this_obs_seq_in, cfg.dir_dart_run+'/obs_seq.in')
        else:
            # create file from scratch
            osi.create_obs_seq_in(cfg, cfg.dir_dart_run+'/obs_seq.in')  
    
    ##############################
    __provide_obs_seq_in(cfg)
    prepare_nature_dart(cfg)
    run_perfect_model_obs(cfg)

    oso = obsseq.ObsSeq(cfg.dir_dart_run + "/obs_seq.out")
    oso = __force_obs_in_physical_range(oso)
    
    f_dest = time.strftime(cfg.pattern_obs_seq_out)
    os.makedirs(os.path.dirname(f_dest), exist_ok=True)
    shutil.copy(cfg.dir_dart_run+'/obs_seq.out', f_dest)
    return oso


if __name__ == '__main__':
    """Generate obs_seq.out files from any wrfout files
    Make sure that the nature & obs info is complete in the config file.

    Usage:
        python create_obsseq_out.py exp_hires.py jet.py 2008-07-30_12:00,2008-07-30_12:01 /jetfs/home/lkugler/data/HiResNature_obs

    Args:
        times (str): comma-separated list of times of the observations

    Returns:
        None, creates obs_seq.out in cluster.archivedir
    """
    # cfg = Config.from_file(sys.argv[1])

    # aso.prepare_run_DART_folder()
    # nml = dart_nml.write_namelist()

    # for time in times:
    #     print("time", time)
    #     time = dt.datetime.strptime(time, '%Y-%m-%d_%H:%M')
    #     generate_new_obsseq_out(time)
        
