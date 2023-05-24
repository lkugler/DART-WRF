import os, shutil, warnings

from dartwrf.utils import try_remove, print, shell
import dartwrf.obs.create_obsseq_in as osi
from dartwrf.obs import obsseq

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster

def generate_obsseq_out(time):

    def ensure_physical_vis(oso):  # set reflectance < surface albedo to surface albedo
        print(" 2.2) removing obs below surface albedo ")
        clearsky_albedo = 0.2928

        if_vis_obs = oso.df['kind'].values == 262
        if_obs_below_surface_albedo = oso.df['observations'].values < clearsky_albedo
        oso.df.loc[if_vis_obs & if_obs_below_surface_albedo, ('observations')] = clearsky_albedo
        oso.to_dart(f=cluster.dart_rundir + "/obs_seq.out")
        return oso


    def apply_superobbing(oso):
        try:
            f_oso = dir_obsseq + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out-before_superob")
            shutil.copy(cluster.dart_rundir + "/obs_seq.out-before_superob", f_oso)
            print('saved', f_oso)
        except Exception as e:
            warnings.warn(str(e))

        print(" 2.3) superobbing to", exp.superob_km, "km")
        oso.df = oso.df.superob(window_km=exp.superob_km)
        oso.to_dart(f=cluster.dart_rundir + "/obs_seq.out")


    ##############################
        
    dir_obsseq=cluster.archivedir + "/obs_seq_out/"
    os.makedirs(dir_obsseq, exist_ok=True)

    osi.create_obs_seq_in(time, exp.observations)
    run_perfect_model_obs()  # generate observation, draws from gaussian

    print(" 2.1) obs preprocessing")
    oso = obsseq.ObsSeq(cluster.dart_rundir + "/obs_seq.out")

    oso = ensure_physical_vis(oso)

    if getattr(exp, "superob_km", False):
        oso = apply_superobbing(oso)

    # archive complete obsseqout
    f_oso = dir_obsseq + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out")
    shutil.copy(cluster.dart_rundir + "/obs_seq.out", f_oso)
    print('saved', f_oso)
    return oso

def run_perfect_model_obs(nproc=12, verbose=True):
    if verbose:
        print("generating observations - running ./perfect_model_obs")
    os.chdir(cluster.dart_rundir)

    try_remove(cluster.dart_rundir + "/obs_seq.out")
    if not os.path.exists(cluster.dart_rundir + "/obs_seq.in"):
        raise RuntimeError("obs_seq.in does not exist in " + cluster.dart_rundir)
    shell(cluster.dart_modules+' mpirun -np '+str(nproc)+" ./perfect_model_obs > log.perfect_model_obs")
    if not os.path.exists(cluster.dart_rundir + "/obs_seq.out"):
        raise RuntimeError(
            "obs_seq.out does not exist in " + cluster.dart_rundir,
            "\n look for " + cluster.dart_rundir + "/log.perfect_model_obs")