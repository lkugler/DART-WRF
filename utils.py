import os, sys, shutil, glob, warnings
import datetime as dt
from slurmpy import Slurm

from config.cfg import exp, cluster
from dartwrf.utils import script_to_str, symlink, copy


class Shellslurm():
    """Like Slurm class, but runs locally"""
    def __init__(self, *args, **kwargs):
        pass
    def run(self, *args, **kwargs):
        print(args[0])
        os.system(args[0])

def create_job(*args, cfg_update=dict(), with_slurm=True, **kwargs):
    """Shortcut to slurmpy's class; keep certain default kwargs
    and only update some with kwarg `cfg_update`
    see https://github.com/brentp/slurmpy

    with_slurm (bool) : if True, use SLURM, else run locally

    """
    if with_slurm:
        return Slurm(*args, slurm_kwargs=dict(cluster.slurm_cfg, **cfg_update), 
                 log_dir=log_dir, scripts_dir=slurm_scripts_dir, **kwargs)
    else:
        return Shellslurm(*args)

def backup_scripts():
    """Copies scripts and configuration to archive dir output folder"""
    os.makedirs(cluster.archivedir, exist_ok=True)

    try:
        shutil.copytree(cluster.scriptsdir, cluster.scripts_rundir)
    except FileExistsError:
        pass
    except:
        raise
    try:
        copy(os.path.basename(__file__), cluster.scripts_rundir+'/')
    except Exception as e:
        warnings.warn(str(e))

def prepare_WRFrundir(init_time):
    """Create WRF/run directories and wrfinput files
    """
    cmd = cluster.python+' '+cluster.scripts_rundir+'/prepare_wrfrundir.py '+init_time.strftime('%Y-%m-%d_%H:%M')
    print(cmd)
    os.system(cmd)

