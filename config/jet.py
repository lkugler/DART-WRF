"""Cluster configuration file, see docstring of ClusterConfig class in dartwrf/utils.py for details"""
from re import A
from dartwrf.utils import ClusterConfig

cluster = ClusterConfig(
    max_nproc = 20,
    max_nproc_for_each_ensemble_member = 16,
    use_slurm = True,

    # binaries
    python = '/jetfs/home/lkugler/miniforge3/envs/verif/bin/python',
    ncks = '/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-2021.7.1/nco-5.1.0-izrhxv24jqco5epjhf5ledsqwanojc5m/bin/ncks',
    ideal = '/jetfs/home/lkugler/data/compile/bin/ideal-v4.6.0_20250210_StS.exe',
    wrfexe = '/jetfs/home/lkugler/data/compile/bin/wrf-v4.6.0_20250210_StS.exe',
    dart_modules = 'module purge; module load rttov/v13.2-gcc-8.5.0',
    wrf_modules = """module purge; module load netcdf-fortran/4.5.3-intel-2021.7.1-27ldrnt""",

    # paths for data output
    wrf_rundir_base = '/jetfs/home/lkugler/data/run_WRF/',  # path for temporary files
    dart_rundir_base = '/jetfs/home/lkugler/data/run_DART/',  # path for temporary files
    archive_base = '/jetfs/home/lkugler/data/sim_archive/',

    # paths used as input
    srcdir = '/jetfs/home/lkugler/data/compile/WRF-4.3/run',
    dart_srcdir = '/jetfs/home/lkugler/data/compile/DART/DART-10.8.3_10pct/models/wrf/work/',
    rttov_srcdir = '/jetfs/home/lkugler/data/compile/RTTOV13/rtcoef_rttov13/',
    
    dartwrf_dir_dev = '/jetfs/home/lkugler/DART-WRF/',
    WRF_namelist_template = '/jetfs/home/lkugler/DART-WRF/config/templates/namelist.input_nat_exact',
    rttov_nml = "/jetfs/home/lkugler/DART-WRF/config/templates/obs_def_rttov.VIS+WV.nml",
    
    # other inputs
    geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.250m_1600x1600',
    geo_em_forecast = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
    #obs_impact_filename = dartwrf_dir_dev+'/templates/impactfactor_T.txt'

    WRF_exe_template = '/jetfs/home/lkugler/DART-WRF/config/templates/run_WRF.jet.sh',
    WRF_ideal_template = '/jetfs/home/lkugler/DART-WRF/config/templates/run_WRF_ideal.sh',

    slurm_cfg = {"account": "lkugler", "partition": "all",  
                    "ntasks": "1", "ntasks-per-core": "1", "mem": "30G",
                    "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"},

    # WRF file format, will only change if WRF changes
    wrfout_format = '/wrfout_d01_%Y-%m-%d_%H:%M:%S',

    # pattern for the init_time folder in sim_archive
    pattern_init_time = "/%Y-%m-%d_%H:%M/",
    
    # how an obs_seq.out file is archived
    pattern_obs_seq_out = "<archivedir>/diagnostics/%Y-%m-%d_%H:%M_obs_seq.out",
        
    # how an obs_seq.final file is archived
    pattern_obs_seq_final = "<archivedir>/diagnostics/%Y-%m-%d_%H:%M_obs_seq.final",  

    )