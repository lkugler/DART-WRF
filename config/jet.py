"""Cluster configuration file, see docstring of ClusterConfig class in dartwrf/utils.py for details"""
from dartwrf import utils
from dartwrf.exp_config import exp

cluster = utils.ClusterConfig(exp)
cluster.name = 'jet'
cluster.max_nproc = 20
cluster.use_slurm = True
cluster.size_WRF_jobarray = exp.n_ens
cluster.np_WRF = 16

# binaries
cluster.python = '/jetfs/home/lkugler/miniforge3/envs/verif/bin/python'
cluster.ncks = '/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-2021.7.1/nco-5.1.0-izrhxv24jqco5epjhf5ledsqwanojc5m/bin/ncks'
cluster.ideal = '/jetfs/home/lkugler/data/compile/bin/ideal-v4.6.0_20250210_StS.exe'
cluster.wrfexe = '/jetfs/home/lkugler/data/compile/bin/wrf-v4.6.0_20250210_StS.exe'
cluster.dart_modules = 'module purge; module load rttov/v13.2-gcc-8.5.0'
cluster.wrf_modules = """module purge; module load netcdf-fortran/4.5.3-intel-2021.7.1-27ldrnt"""

# paths for data output
cluster.wrf_rundir_base = '/jetfs/home/lkugler/data/run_WRF/'  # path for temporary files
cluster.dart_rundir_base = '/jetfs/home/lkugler/data/run_DART/'  # path for temporary files
cluster.archive_base = '/jetfs/home/lkugler/data/sim_archive/'

# paths used as input
cluster.srcdir = '/jetfs/home/lkugler/data/compile/WRF-4.3/run'
cluster.dart_srcdir = '/jetfs/home/lkugler/data/compile/DART/DART-10.8.3_10pct/models/wrf/work/'
cluster.rttov_srcdir = '/jetfs/home/lkugler/data/compile/RTTOV13/rtcoef_rttov13/'
cluster.dartwrf_dir = '/jetfs/home/lkugler/DART-WRF/'

# other inputs
cluster.geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.250m_1600x1600' 
cluster.geo_em_forecast = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200'
#cluster.obs_impact_filename = cluster.dartwrf_dir+'/templates/impactfactor_T.txt'
cluster.namelist = cluster.dartwrf_dir+'/templates/namelist.input_nat_exact'
cluster.rttov_nml = cluster.dartwrf_dir + "/templates/obs_def_rttov.VIS+WV.nml"
cluster.run_WRF = '/jetfs/home/lkugler/DART-WRF/dartwrf/run_ens.jet.sh'

cluster.slurm_cfg = {"account": "lkugler", "partition": "all",  
                 "ntasks": "1", "ntasks-per-core": "1", "mem": "30G",
                 "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"}

# WRF file format, will only change if WRF changes
cluster.wrfout_format = '/wrfout_d01_%Y-%m-%d_%H:%M:%S'

# pattern for the init_time folder in sim_archive
cluster.pattern_init_time = "/%Y-%m-%d_%H:%M/"

# how an obs_seq.out file is archived
cluster.pattern_obs_seq_out = cluster.archivedir + \
    "/diagnostics/%Y-%m-%d_%H:%M_obs_seq.out"  
    
# how an obs_seq.final file is archived
cluster.pattern_obs_seq_final = cluster.archivedir + \
    "/diagnostics/%Y-%m-%d_%H:%M_obs_seq.final"  
