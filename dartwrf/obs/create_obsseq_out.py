import os
import shutil
import glob
import warnings

from dartwrf.utils import try_remove, print, shell, symlink, copy
import dartwrf.obs.create_obsseq_in as osi
from dartwrf.obs import obsseq
from dartwrf import assimilate as aso
from dartwrf import wrfout_add_geo
from dartwrf.obs.obskind import obs_kind_nrs

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster


def prepare_nature_dart(time):
    """Prepares DART nature (wrfout_d01) if available

    Args:
        time (dt.datetime): Time at which observations will be made
    """
    def _find_nature(time):
        """Find the path to the nature file for the given time
        """
        glob_pattern = time.strftime(exp.nature_wrfout_pattern)
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
    copy(f_nat, cluster.dart_rundir + "/wrfout_d01")

    # add coordinates if necessary
    if cluster.geo_em_nature:
        wrfout_add_geo.run(cluster.geo_em_nature, cluster.dart_rundir + "/wrfout_d01")
        
    # as a grid template
    symlink(cluster.dart_rundir + "/wrfout_d01", cluster.dart_rundir + "/wrfinput_d01")
    

def force_obs_in_physical_range(oso):
    """ Set values smaller than surface albedo to surface albedo
    Highly hacky. Your albedo might be different.
    """
    print(" removing obs below surface albedo ")
    clearsky_albedo = 0.2928  # custom value

    if_vis_obs = oso.df['kind'].values == obs_kind_nrs['MSG_4_SEVIRI_BDRF']
    if_obs_below_surface_albedo = oso.df['observations'].values < clearsky_albedo
    oso.df.loc[if_vis_obs & if_obs_below_surface_albedo,
               ('observations')] = clearsky_albedo
    oso.to_dart(f=cluster.dart_rundir + "/obs_seq.out")
    return oso


def run_perfect_model_obs(nproc=12):
    """Run the ./perfect_model_obs program

    Args:
        nproc (int): number of processors to use

    Returns:
        None, creates obs_seq.out
    """
    print("running ./perfect_model_obs")
    os.chdir(cluster.dart_rundir)
    
    if hasattr(cluster, 'max_nproc'):
        nproc = cluster.max_nproc

    try_remove(cluster.dart_rundir + "/obs_seq.out")
    if not os.path.exists(cluster.dart_rundir + "/obs_seq.in"):
        raise RuntimeError(
            "obs_seq.in does not exist in " + cluster.dart_rundir)
    shell(cluster.dart_modules+'; mpirun -np '+str(nproc) +
          " ./perfect_model_obs > log.perfect_model_obs")
    if not os.path.exists(cluster.dart_rundir + "/obs_seq.out"):
        raise RuntimeError(
            "obs_seq.out does not exist in " + cluster.dart_rundir,
            "\n see "+cluster.dart_rundir + "/log.perfect_model_obs")


def generate_new_obsseq_out(time):
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
    def _provide_obs_seq_in(time):
        if hasattr(exp, 'use_this_obs_seq_in'):
            # custom definition of an obs_seq.in file
            print("using obs_seq.in:", exp.use_this_obs_seq_in)
            copy(exp.use_this_obs_seq_in, cluster.dart_rundir+'/obs_seq.in')
        else:
            # create file from scratch
            osi.create_obs_seq_in(time, exp.observations)
        
    _provide_obs_seq_in(time)
    prepare_nature_dart(time)

    run_perfect_model_obs(nproc=cluster.max_nproc)

    oso = obsseq.ObsSeq(cluster.dart_rundir + "/obs_seq.out")
    oso = force_obs_in_physical_range(oso)
    
    f_dest = time.strftime(cluster.pattern_obs_seq_out)
    os.makedirs(os.path.dirname(f_dest), exist_ok=True)
    shutil.copy(cluster.dart_rundir+'/obs_seq.out', f_dest)
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
    import argparse
    import datetime as dt
    parser = argparse.ArgumentParser(
        description='Generate obs_seq.out files from an experiment')

    parser.add_argument('times', type=str, help='times of the observations')
    args = parser.parse_args()
    times = args.times.split(',')
    
    # before running perfect_model_obs, we need to set up the run_DART folder
    from dartwrf import assimilate as aso
    from dartwrf import dart_nml
    aso.prepare_run_DART_folder()
    nml = dart_nml.write_namelist()

    for time in times:
        print("time", time)
        time = dt.datetime.strptime(time, '%Y-%m-%d_%H:%M')
        generate_new_obsseq_out(time)
        
