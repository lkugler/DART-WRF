import os, sys
import datetime as dt

class ClusterConfig(object):
    """Helper class, contains useful abbreviations to use in code later on"""
    def __init__(self):
        pass

    @property
    def archivedir(self):
        return self.archive_base+'/'+self.expname

    def wrf_rundir(self, iens):
        return '/gpfs/data/fs71386/lkugler/run_WRF/'+self.expname+'/'+str(iens)

    @property
    def scripts_rundir(self):
        return self.archivedir+'/DART-WRF/'

    @property
    def dartrundir(self):
        return '/gpfs/data/fs71386/lkugler/run_DART/'+self.expname+'/'


#######################################################################################
"""Configuration name docs

Use attributes of a dictionary like this: `path = vsc.archivedir`

attribute name  | publicly usable  |   description
------------------------------------------------------
name                yes                 any custom name (currently unused)
python              yes                 path of python version to use
python_enstools     no                  path of python version to use for verification script (not provided)
ncks                yes                 path to 'ncks' program; type 'which ncks' to find the path,
                                        if it doesn't exist, try to load the module first ('module load nco')
tmpfiledir          yes                 path to directory where the 'run_WRF' directory is created
                                        necessary to run WRF forecasts
userdir             no                  path to user's directory
srcdir              yes                 path to where WRF has been compiled
                                        including the 'run' folder of WRF, e.g. /home/WRF-4.3/run
archive_base        yes                 path where to write output to
                                        in there, one folder will be created for every experiment
dart_srcdir         yes                 path to DART compile directory, e.g. /home/DART-9.11.9/models/wrf/work
rttov_srcdir        yes                 path to RTTOV compile directory, e.g. /home/RTTOV13/rtcoef_rttov13/
scriptsdir          yes                 path where DART-WRF scripts reside, e.g. /home/DART-WRF/scripts
ideal               yes                 path to WRF's ideal.exe
wrfexe              yes                 path to WRF's wrf.exe
namelist            yes                 path to a namelist template; strings like <hist_interval> 
                                        will be overwritten in scripts/prepare_namelist.py
run_WRF             yes                 path to script which runs WRF on a node of the cluster
slurm_cfg           yes                 python dictionary, containing options of SLURM
                                        defined in SLURM docs (https://slurm.schedmd.com/sbatch.html)
                                        this configuration can be overwritten later on, for example:
                                        'dict(cluster.slurm_cfg, **cfg_update)' where
                                        'cfg_update = {"nodes": "2"}'
"""                 

vsc = ClusterConfig()
vsc.name = 'vsc'  
vsc.python = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/python'
vsc.python_enstools = '/home/fs71386/lkugler/miniconda3/envs/enstools/bin/python'
vsc.ncks = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/ncks'
vsc.tmpfiledir = '/gpfs/data/fs71386/lkugler'
vsc.userdir = '/home/fs71386/lkugler'
vsc.srcdir = '/gpfs/data/fs71386/lkugler/compile/WRF/WRF-4.3/run'
vsc.archive_base = '/gpfs/data/fs71386/lkugler/sim_archive/'
vsc.dart_srcdir = '/gpfs/data/fs71386/lkugler/compile/DART/DART-9.11.9/models/wrf/work'
vsc.rttov_srcdir = '/gpfs/data/fs71386/lkugler/compile/RTTOV13/rtcoef_rttov13/'
vsc.scriptsdir = '/home/fs71386/lkugler/DART-WRF/scripts/'

vsc.ideal = vsc.userdir+'/compile/bin/ideal-v4.2.2_v1.16.exe'
vsc.wrfexe = vsc.userdir+'/compile/bin/wrf-v4.3_v1.19.exe'
vsc.namelist = vsc.scriptsdir+'/../templates/namelist.input'
vsc.run_WRF = '/home/fs71386/lkugler/DART-WRF/scripts/run_ens.vsc.sh'

vsc.slurm_cfg = {"account": "p71386", "partition": "mem_0384", "qos": "p71386_0384",
                 "nodes": "1", "ntasks": "1", "ntasks-per-node": "48", "ntasks-per-core": "1",
                 "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"}


jet = ClusterConfig()
jet.name = 'jet'
jet.python = '/jetfs/home/lkugler/miniconda3/bin/python'
jet.ncks = 'ncks'
jet.userdir = '/jetfs/home/lkugler'
jet.srcdir = '/jetfs/home/lkugler/compile/WRF/WRF-4.1.5/run'
jet.scriptsdir = ''
jet.archive_base = '/jetfs/home/lkugler/data_jetfs/sim_archive/'

jet.ideal = jet.userdir+'/compile/bin/ideal.exe'
jet.wrfexe = jet.userdir+'/compile/bin/wrf-v4.2_v1.10.dmpar.exe'
jet.namelist = jet.userdir+'/config_files/namelist.input'
jet.run_WRF = '/jetfs/home/lkugler/DART-WRF/scripts/osse/run_ens.jet.sh'

jet.slurm_cfg = {"account": "p71386", "partition": "mem_0384", "qos": "p71386_0384",
                 "mem-per-cpu": "2GB",
                 "ntasks-per-node": "48", "ntasks-per-core": 1, "gres": "none"}
