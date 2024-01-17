import os, shutil, warnings

from dartwrf.utils import try_remove, print, shell, symlink
import dartwrf.obs.create_obsseq_in as osi
from dartwrf.obs import obsseq
from dartwrf import assimilate as aso

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster


def _prepare_DART_grid_template():
    # DART needs a wrfinput file as a template for the grid
    # No data will be read from this file, but the grid information must match exactly.
    
    # error if the source does not exist
    if not os.path.exists(cluster.dart_rundir + "/wrfout_d01"):
        raise FileNotFoundError("wrfout_d01 not found in " + cluster.dart_rundir, 
                                "but necessary to create observations")
    symlink(cluster.dart_rundir + "/wrfout_d01", 
            cluster.dart_rundir + "/wrfinput_d01")

def generate_obsseq_out(time, nproc=12):
    """Generate an obs_seq.out file from the current experiment
    Expects an existing nature file in the cluster.dart_rundir
    
    Args:
        time (datetime): time of the observations
        nproc (int, optional): number of cores for call to ./perfect_model_obs
    
    Returns:
        obsseq.ObsSeq: obs_seq.out representation
    """

    def _ensure_physical_vis(oso):  # set reflectance < surface albedo to surface albedo
        """ Set values smaller than surface albedo to surface albedo
        Highly hacky. Your albedo might be different.
        """
        print(" removing obs below surface albedo ")
        clearsky_albedo = 0.2928

        if_vis_obs = oso.df['kind'].values == 262
        if_obs_below_surface_albedo = oso.df['observations'].values < clearsky_albedo
        oso.df.loc[if_vis_obs & if_obs_below_surface_albedo, ('observations')] = clearsky_albedo
        oso.to_dart(f=cluster.dart_rundir + "/obs_seq.out")
        return oso


    def _apply_superobbing(oso):
        try:
            f_oso = aso.pattern_obs_seq_out + '-before_superob'
            shutil.copy(cluster.dart_rundir + "/obs_seq.out", f_oso)
            print('saved', f_oso)
        except Exception as e:
            warnings.warn(str(e))

        print(" superobbing to", exp.superob_km, "km")
        oso.df = oso.df.superob(window_km=exp.superob_km)
        oso.to_dart(f=cluster.dart_rundir + "/obs_seq.out")
        return oso

    osi.create_obs_seq_in(time, exp.observations)  # create obs definition file

    _prepare_DART_grid_template()
    run_perfect_model_obs(nproc=nproc)  # generate observation, draws from gaussian

    oso = obsseq.ObsSeq(cluster.dart_rundir + "/obs_seq.out")

    oso = _ensure_physical_vis(oso)

    if getattr(exp, "superob_km", False):
        oso = _apply_superobbing(oso)
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
    nproc = min(nproc, cluster.max_nproc)

    try_remove(cluster.dart_rundir + "/obs_seq.out")
    if not os.path.exists(cluster.dart_rundir + "/obs_seq.in"):
        raise RuntimeError("obs_seq.in does not exist in " + cluster.dart_rundir)
    shell(cluster.dart_modules+' mpirun -np '+str(nproc)+" ./perfect_model_obs > log.perfect_model_obs")
    if not os.path.exists(cluster.dart_rundir + "/obs_seq.out"):
        raise RuntimeError(
            "obs_seq.out does not exist in " + cluster.dart_rundir,
            "\n see "+cluster.dart_rundir + "/log.perfect_model_obs")
    
if __name__ == '__main__':
    """Generate obs_seq.out files from an experiment
    
    Usage:
        python3 create_obsseq_out.py 2008-07-30_12:00,2008-07-30_12:01
    
    Args:
        times (str): comma-separated list of times of the observations

    Returns:
        None, creates obs_seq.out in cluster.archivedir
    """
    import argparse
    import datetime as dt
    parser = argparse.ArgumentParser(description='Generate obs_seq.out files from an experiment')
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

        aso.prepare_nature_dart(time)  # link WRF files to DART directory
        generate_obsseq_out(time)
