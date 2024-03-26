"""Cluster configuration file, see docstring of ClusterConfig class in dartwrf/utils.py for details"""
from dartwrf import utils
from dartwrf.exp_config import exp

cluster = utils.ClusterConfig(exp)
cluster.name = 'srvx1'
cluster.max_nproc = 6
cluster.use_slurm = False

# binaries
cluster.python = 'python'
cluster.python_verif = '/users/staff/lkugler/miniconda3/bin/python'
cluster.ncks = '/home/swd/spack/opt/spack/linux-rhel8-skylake_avx512/gcc-8.5.0/nco-5.0.1-ntu44aoxlvwtr2tsrobfr4lht7cpvccf/bin/ncks'
cluster.ideal = '' #/jetfs/home/lkugler/bin/ideal-v4.3_v1.22.exe'
cluster.wrfexe = '' #/jetfs/home/lkugler/bin/wrf-v4.3_v1.22.exe'
cluster.dart_modules = 'pip install scipy; module purge; module load netcdf-fortran/4.5.2-gcc-8.5.0-MPI3.1.6; '
cluster.wrf_modules = ''

# paths for data output
cluster.wrf_rundir_base = utils.userhome+'/AdvDA/run_WRF/'  # path for temporary files
cluster.dart_rundir_base = utils.userhome+'/AdvDA/run_DART/'  # path for temporary files
cluster.archive_base = utils.userhome+'/data/sim_archive/'

# paths used as input
cluster.srcdir = '/users/staff/lkugler/AdvDA23/DART/WRF-4.3/run'
cluster.dart_srcdir = '/users/students/lehre/advDA_s2023/DART/models/wrf/work'
cluster.rttov_srcdir = '/users/students/lehre/advDA_s2023/RTTOV13/rtcoef_rttov13/'
cluster.dartwrf_dir = utils.userhome+'/AdvDA/DART-WRF/'
cluster.geo_em_for_WRF_ideal = '/users/students/lehre/advDA_s2023/data/geo_em.d01.nc'

# templates/run scripts
cluster.namelist = cluster.dartwrf_dir+'/../templates/namelist.input'
cluster.run_WRF = cluster.dartwrf_dir+'/run_ens.jet.sh'

cluster.slurm_cfg = None
