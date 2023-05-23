"""Cluster configuration file, see docstring of ClusterConfig class in dartwrf/utils.py for details"""
from dartwrf import utils
from dartwrf.exp_config import exp


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
