"""Cluster configuration file, see docstring of ClusterConfig class in dartwrf/utils.py for details"""
from dartwrf import utils
from dartwrf.exp_config import exp

cluster = utils.ClusterConfig(exp)
cluster.name = 'jet'
cluster.max_nproc = 12
cluster.use_slurm = True
cluster.size_WRF_jobarray = exp.n_ens
cluster.np_WRF = 12

# binaries
cluster.python = '/jetfs/home/lkugler/miniconda3/envs/DART/bin/python'
cluster.ncks = '/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-2021.7.1/nco-5.1.0-izrhxv24jqco5epjhf5ledsqwanojc5m/bin/ncks'
cluster.ideal = '/jetfs/home/lkugler/bin/ideal-v4.3_v1.22.exe'
cluster.wrfexe = '/jetfs/home/lkugler/bin/wrf-v4.3_v1.22_ifort_20230413.exe'
cluster.dart_modules = 'module purge; module load rttov/v13.2-gcc-8.5.0; '
cluster.wrf_modules = """module purge; module load intel-oneapi-compilers/2022.2.1-zkofgc5 hdf5/1.12.2-intel-2021.7.1-w5sw2dq netcdf-fortran/4.5.3-intel-2021.7.1-27ldrnt netcdf-c/4.7.4-intel-2021.7.1-lnfs5zz intel-oneapi-mpi/2021.7.1-intel-2021.7.1-pt3unoz
export HDF5=/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-2021.7.1/hdf5-1.12.2-w5sw2dqpcq2orlmeowleamoxr65dhhdc
"""

# paths for data output
cluster.wrf_rundir_base = '/jetfs/home/lkugler/data/run_WRF/'  # path for temporary files
cluster.dart_rundir_base = '/jetfs/home/lkugler/data/run_DART/'  # path for temporary files
cluster.archive_base = '/jetfs/home/lkugler/data/sim_archive/'

# paths used as input
cluster.srcdir = '/jetfs/home/lkugler/data/compile/WRF-4.3/run'
cluster.dart_srcdir = '/jetfs/home/lkugler/data/compile/DART/DART-10.8.3/models/wrf/work'
cluster.rttov_srcdir = '/jetfs/home/lkugler/data/compile/RTTOV13/rtcoef_rttov13/'
cluster.dartwrf_dir = '/jetfs/home/lkugler/DART-WRF/'

# other inputs
cluster.geo_em_for_WRF_ideal = '/jetfs/home/lkugler/data/geo_em.d01.nc'
cluster.obs_impact_filename = cluster.dartwrf_dir+'/templates/impactfactor_T.txt'
cluster.namelist = cluster.dartwrf_dir+'/templates/namelist.input'
cluster.run_WRF = '/jetfs/home/lkugler/DART-WRF/dartwrf/run_ens.jet.sh'

cluster.slurm_cfg = {"account": "lkugler", "partition": "compute", #"nodelist": "jet07",
                 "ntasks": "1", "ntasks-per-core": "1", "mem": "30G",
                 "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"}
