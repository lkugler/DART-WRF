import os, sys
import datetime as dt

class ClusterConfig(object):
    """Helper class"""
    def __init__(self):
        pass

    def archivedir(self):
        return self.archive_base+'/'+self.expname

    def wrf_rundir(self, iens):
        return self.userdir+'/run_WRF/'+self.expname+'/'+str(iens)

#######################################################################################


vsc = ClusterConfig()
vsc.name = 'vsc'
vsc.python = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/python'
vsc.ncks = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/ncks'
vsc.userdir = '/home/fs71386/lkugler'
vsc.srcdir = '/home/fs71386/lkugler/compile/WRF/WRF-4.2.2/run'
vsc.archive_base = '/gpfs/data/fs71386/lkugler/sim_archive/'
vsc.dart_srcdir = '/home/fs71386/lkugler/DART/DART-9.9.0/models/wrf/work'
vsc.dartrundir = '/home/fs71386/lkugler/run_DART'
vsc.scriptsdir = '/home/fs71386/lkugler/DART-WRF/scripts'

vsc.nature_wrfout = '/home/fs71386/lkugler/data/sim_archive/exp_v1.16_P1_nature/2008-07-30_06:00/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'
#vsc.input_profile = '/home/fs71386/lkugler/wrf_profiles/data/wrf/ens/from_LMU/raso.nat.<iens>.wrfprof'
vsc.input_profile = '/home/fs71386/lkugler/wrf_profiles/data/wrf/ens/2021-05-04/raso.fc.<iens>.wrfprof'

vsc.ideal = vsc.userdir+'/compile/bin/ideal-v4.2.2_v1.16.exe'
vsc.wrfexe = vsc.userdir+'/compile/bin/wrf-v4.2.2_v1.16.exe'
vsc.namelist = vsc.scriptsdir+'/../templates/namelist.input'
vsc.run_WRF = '/gpfs/data/fs71386/lkugler/DART-WRF/scripts/osse/run_ens.vsc.sh'

vsc.slurm_cfg = {"account": "p71386", "partition": "mem_0384", "qos": "p71386_0384",
                 "ntasks": "1", "nodes": "1", "ntasks-per-node": "48", "ntasks-per-core": "1",
                 "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"}


jet = ClusterConfig()
jet.name = 'jet'
jet.python = '/jetfs/home/lkugler/miniconda3/bin/python'
jet.ncks = 'ncks'
jet.userdir = '/jetfs/home/lkugler'
jet.srcdir = '/jetfs/home/lkugler/compile/WRF/WRF-4.1.5/run'
jet.archive_base = '/jetfs/home/lkugler/data_jetfs/sim_archive/'
jet.dartrundir = '/jetfs/home/lkugler/DART-WRF/rundir'
jet.scriptsdir = '/jetfs/home/lkugler/DART-WRF/scripts/osse'
jet.nature_wrfout = '/raid61/scratch/lkugler/VSC/sim_archive/OSSE_v1.10_LMU+shear/2/single/wrfout_d01_%Y-%m-%d_%H:%M:%S'

jet.ideal = jet.userdir+'/compile/bin/ideal.exe'
jet.wrfexe = jet.userdir+'/compile/bin/wrf-v4.2_v1.10.dmpar.exe'
jet.namelist = jet.userdir+'/config_files/namelist.input'
jet.run_WRF = '/jetfs/home/lkugler/DART-WRF/scripts/osse/run_ens.jet.sh'

jet.slurm_cfg = {"account": "p71386", "partition": "mem_0384", "qos": "p71386_0384",
                 "mem-per-cpu": "2GB",
                 "ntasks-per-node": "48", "ntasks-per-core": 1, "gres": "none"}
