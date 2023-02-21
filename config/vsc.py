import os, sys
import datetime as dt
from dartwrf import utils
from config.cfg import exp

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
obs_impact_filename     path to obs_impact_filename (see DART guide; module assim_tools_mod and program obs_impact_tool)
geo_em                  path to NetCDF file of WRF domain (see WRF guide)

slurm_cfg               python dictionary, containing options of SLURM
                            defined in SLURM docs (https://slurm.schedmd.com/sbatch.html)
                            this configuration can be overwritten later on, for example:
                            'dict(cluster.slurm_cfg, **cfg_update)' where
                            'cfg_update = {"nodes": "2"}'
"""


cluster = utils.ClusterConfig(exp)
cluster.name = 'VSC' 
cluster.max_nproc = 20
cluster.size_jobarray = 10  # 10 jobs with each 4 WRF processes per node
cluster.use_slurm = True

# binaries
cluster.python = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/python'
cluster.python_enstools = '/home/fs71386/lkugler/miniconda3/envs/enstools/bin/python'
cluster.ncks = '/home/fs71386/lkugler/miniconda3/envs/DART/bin/ncks'
cluster.ideal = '/home/fs71386/lkugler/compile/bin/ideal-v4.2.2_v1.22.exe'
cluster.wrfexe = '/home/fs71386/lkugler/compile/bin/wrf-v4.3_v1.22.exe'
cluster.container = '/home/fs71386/lkugler/run_container.sh python.gcc9.5.0.vsc4.sif'

# paths for data output
cluster.wrf_rundir_base = '/gpfs/data/fs71386/lkugler/run_WRF/'  # path for temporary files
cluster.dart_rundir_base = '/gpfs/data/fs71386/lkugler/run_DART/'  # path for temporary files
cluster.archive_base = '/gpfs/data/fs71386/lkugler/sim_archive/'

# paths used as input
cluster.srcdir = '/gpfs/data/fs71386/lkugler/compile/WRF/WRF-4.3/run'
cluster.dart_srcdir = '/gpfs/data/fs71386/lkugler/compile/DART/DART/models/wrf/work'
cluster.rttov_srcdir = '/gpfs/data/fs71386/lkugler/compile/RTTOV13/rtcoef_rttov13/'
cluster.scriptsdir = '/home/fs71386/lkugler/DART-WRF/dartwrf/'

# templates/run scripts
cluster.namelist = cluster.scriptsdir+'/../templates/namelist.input'
cluster.run_WRF = '/home/fs71386/lkugler/DART-WRF/dartwrf/run_ens.vsc.sh'

cluster.slurm_cfg = {"account": "p71386", "partition": "skylake_0384", "qos": "p71386_0384",
                 "nodes": "1", "ntasks": "1", "ntasks-per-node": "48", "ntasks-per-core": "1",
                 "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"}
