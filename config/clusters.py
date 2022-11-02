import os, sys
import datetime as dt

"""Configuration name docs

When coding, use attributes of a dictionary like this: 
$ from cfg import exp, cluster
$ path = cluster.archivedir


attribute name    |     description
------------------------------------------------------
name                    any string (currently unused)

python                  path of python version to use
python_enstools         path of python version to use for verification script (not provided)
ncks                    path to 'ncks' program; type 'which ncks' to find the path,
                            if it doesn't exist, try to load the module first ('module load nco')
ideal                   path to WRF's ideal.exe
wrfexe                  path to WRF's wrf.exe

wrf_rundir_base         path for temporary files for WRF
dart_rundir_base        path for temporary files for DART
archive_base            path for long-time output storage

srcdir                  path to where WRF has been compiled, including the 'run' folder of WRF, e.g. /home/WRF-4.3/run
dart_srcdir             path to DART compile directory, e.g. /home/DART-9.11.9/models/wrf/work
rttov_srcdir            path to RTTOV compile directory, e.g. /home/RTTOV13/rtcoef_rttov13/
scriptsdir              path where DART-WRF scripts reside, e.g. /home/DART-WRF/scripts

namelist                path to a namelist template; strings like <hist_interval>, will be overwritten in scripts/prepare_namelist.py
run_WRF                 path to script which runs WRF on a node of the cluster

slurm_cfg               python dictionary, containing options of SLURM
                            defined in SLURM docs (https://slurm.schedmd.com/sbatch.html)
                            this configuration can be overwritten later on, for example:
                            'dict(cluster.slurm_cfg, **cfg_update)' where
                            'cfg_update = {"nodes": "2"}'
"""                 


class ClusterConfig(object):
    """Helper class, contains useful abbreviations to use in code later on"""
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


vsc = ClusterConfig()
vsc.name = 'vsc' 

# binaries
vsc.python = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/python'
vsc.python_enstools = '/home/fs71386/lkugler/miniconda3/envs/enstools/bin/python'
vsc.ncks = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/ncks'
vsc.ideal = '/home/fs71386/lkugler/compile/bin/ideal-v4.2.2_v1.22.exe'
vsc.wrfexe = '/home/fs71386/lkugler/compile/bin/wrf-v4.3_v1.22.exe'
vsc.container = '/home/fs71386/lkugler/run_container.sh python.gcc9.5.0.vsc4.sif'

# paths for data output
vsc.wrf_rundir_base = '/gpfs/data/fs71386/lkugler/run_WRF/'  # path for temporary files
vsc.dart_rundir_base = '/gpfs/data/fs71386/lkugler/run_DART/'  # path for temporary files
vsc.archive_base = '/gpfs/data/fs71386/lkugler/sim_archive/'

# paths used as input
vsc.srcdir = '/gpfs/data/fs71386/lkugler/compile/WRF/WRF-4.3/run'
vsc.dart_srcdir = '/gpfs/data/fs71386/lkugler/compile/DART/DART/models/wrf/work'
vsc.rttov_srcdir = '/gpfs/data/fs71386/lkugler/compile/RTTOV13/rtcoef_rttov13/'
vsc.scriptsdir = '/home/fs71386/lkugler/DART-WRF/dartwrf/'

# templates/run scripts
vsc.namelist = vsc.scriptsdir+'/../templates/namelist.input'
vsc.run_WRF = '/home/fs71386/lkugler/DART-WRF/dartwrf/run_ens.vsc.sh'

vsc.slurm_cfg = {"account": "p71386", "partition": "skylake_0384", "qos": "p71386_0384",
                 "nodes": "1", "ntasks": "1", "ntasks-per-node": "48", "ntasks-per-core": "1",
                 "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"}

jet = ClusterConfig()
jet.name = 'jet'

# binaries
jet.python = '/jetfs/home/lkugler/miniconda3/envs/DART/bin/python'
jet.python_verif = '/jetfs/home/lkugler/miniconda3/envs/enstools/bin/python'
jet.ncks = '/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-20.0.2/nco-4.9.3-dhlqiyog7howjmaleyfhm6lkt7ra37xf/bin/ncks'
jet.ideal = '/jetfs/home/lkugler/bin/ideal-v4.3_v1.22.exe'
jet.wrfexe = '/jetfs/home/lkugler/bin/wrf-v4.3_v1.22.exe'
jet.container = ''

# paths for data output
jet.wrf_rundir_base = '/jetfs/home/lkugler/data/run_WRF/'  # path for temporary files
jet.dart_rundir_base = '/jetfs/home/lkugler/data/run_DART/'  # path for temporary files
jet.archive_base = '/jetfs/home/lkugler/data/sim_archive/'

# paths used as input
jet.srcdir = '/jetfs/home/lkugler/data/compile/WRF-4.3/run'
jet.dart_srcdir = '/jetfs/home/lkugler/data/compile/DART/DART-10.5.3/models/wrf/work'
jet.rttov_srcdir = '/jetfs/home/lkugler/data/compile/RTTOV13/rtcoef_rttov13/'
jet.scriptsdir = '/jetfs/home/lkugler/DART-WRF/dartwrf/'
jet.geo_em = '/jetfs/home/lkugler/data/geo_em.d01.nc'

# templates/run scripts
jet.namelist = jet.scriptsdir+'/../templates/namelist.input'
jet.run_WRF = '/jetfs/home/lkugler/DART-WRF/dartwrf/run_ens.jet.sh'

jet.slurm_cfg = {"account": "lkugler", "partition": "compute",
                 "ntasks": "1", "ntasks-per-core": "1", "mem": "50G",
                 "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"}
