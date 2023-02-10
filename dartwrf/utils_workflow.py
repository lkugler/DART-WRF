import os, sys, shutil, glob, warnings
import subprocess
copy = shutil.copy

class ExperimentConfiguration(object):
    """Collection of variables to use in code later on"""
    def __init__(self):
        pass

class ClusterConfig(object):
    """Collection of variables to use in code later on"""
    def __init__(self):
        pass

    @property
    def archivedir(self):
        return self.archive_base+'/'+self.expname

    def wrf_rundir(self, iens):
        return self.wrf_rundir_base+'/'+self.expname+'/'+str(iens)

    @property
    def scripts_rundir(self):
        return self.archivedir+'/DART-WRF/'

    @property
    def dartrundir(self):
        return self.dart_rundir_base+'/'+self.expname+'/'

class Shellslurm():
    """Like Slurmpy class, but runs locally"""
    def __init__(self, *args, **kwargs):
        pass
    def run(self, *args, **kwargs):
        print(args[0])
        os.system(args[0])


def create_job(*args, cfg_update=dict(), **kwargs):
    """Shortcut to slurmpy's class; keep certain default kwargs
    and only update some with kwarg `cfg_update`
    see https://github.com/brentp/slurmpy

    with_slurm (bool) : if True, use SLURM, else run locally

    """
    from config.cfg import cluster
    if cluster.use_slurm:
        from slurmpy import Slurm
        return Slurm(*args, slurm_kwargs=dict(cluster.slurm_cfg, **cfg_update), 
                 log_dir=log_dir, scripts_dir=slurm_scripts_dir, **kwargs)
    else:
        return Shellslurm(*args)

def backup_scripts():
    """Copies scripts and configuration to archive dir output folder"""
    from config.cfg import cluster
    os.makedirs(cluster.archivedir, exist_ok=True)

    try:
        shutil.copytree(cluster.scriptsdir, cluster.scripts_rundir)
        shutil.copytree(cluster.scriptsdir+'/../', cluster.scripts_rundir)
    except FileExistsError:
        pass
    except:
        raise

def prepare_WRFrundir(init_time):
    """Create WRF/run directories and wrfinput files
    """
    from config.cfg import cluster
    cmd = cluster.python+' '+cluster.scripts_rundir+'/prepare_wrfrundir.py '+init_time.strftime('%Y-%m-%d_%H:%M')
    print(cmd)
    os.system(cmd)