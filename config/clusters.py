import os, sys
import datetime as dt

class ClusterConfig(object):
    """Helper class"""
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



#######################################################################################


vsc = ClusterConfig()
vsc.name = 'vsc'
vsc.python = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/python'
vsc.python_enstools = '/home/fs71386/lkugler/miniconda3/envs/enstools/bin/python'
vsc.ncks = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/ncks'
vsc.tmpfiledir = '/gpfs/data/fs71386/lkugler'
vsc.userdir = '/home/fs71386/lkugler'
vsc.srcdir = '/gpfs/data/fs71386/lkugler/compile/WRF/WRF-4.3/run'
vsc.archive_base = '/gpfs/data/fs71386/lkugler/sim_archive/'
vsc.dart_srcdir = '/home/fs71386/lkugler/DART/DART-9.11.9/models/wrf/work'
vsc.dartrundir = '/gpfs/data/fs71386/lkugler/run_DART'
vsc.scriptsdir = '/home/fs71386/lkugler/DART-WRF/scripts/'

vsc.ideal = vsc.userdir+'/compile/bin/ideal-v4.2.2_v1.16.exe'
vsc.wrfexe = vsc.userdir+'/compile/bin/wrf-v4.3_v1.16.exe'
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
jet.dartrundir = '/jetfs/home/lkugler/DART-WRF/rundir'

jet.ideal = jet.userdir+'/compile/bin/ideal.exe'
jet.wrfexe = jet.userdir+'/compile/bin/wrf-v4.2_v1.10.dmpar.exe'
jet.namelist = jet.userdir+'/config_files/namelist.input'
jet.run_WRF = '/jetfs/home/lkugler/DART-WRF/scripts/osse/run_ens.jet.sh'

jet.slurm_cfg = {"account": "p71386", "partition": "mem_0384", "qos": "p71386_0384",
                 "mem-per-cpu": "2GB",
                 "ntasks-per-node": "48", "ntasks-per-core": 1, "gres": "none"}
