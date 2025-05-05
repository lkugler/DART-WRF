"""Cluster configuration file, see docstring of ClusterConfig class in dartwrf/utils.py for details"""

cluster_defaults = dict(
    max_nproc = 20,
    max_nproc_for_each_ensemble_member = 9,
    use_slurm = True,

    # binaries
    python = '/jetfs/home/lkugler/miniforge3/envs/verif/bin/python',
    ncks = '/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-2021.7.1/nco-5.1.0-izrhxv24jqco5epjhf5ledsqwanojc5m/bin/ncks',
    idealexe = '/jetfs/home/lkugler/data/compile/bin/ideal-v4.6.0_20250210_StS.exe',
    wrfexe = '/jetfs/home/lkugler/data/compile/bin/wrf-v4.6.0_20250210_StS.exe',
    dart_modules = 'module purge; module load rttov/v13.2-gcc-8.5.0',
    wrf_modules = """module purge; module load netcdf-fortran/4.5.3-intel-2021.7.1-27ldrnt""",

    # paths for data output
    dir_wrf_run = '/jetfs/home/lkugler/data/run_WRF/<exp>/<ens>/',  # path for temporary files
    dir_dart_run = '/jetfs/home/lkugler/data/run_DART/<exp>/',  # path for temporary files
    dir_archive = '/jetfs/home/lkugler/data/sim_archive/<exp>/',

    # paths used as input
    dir_wrf_src = '/jetfs/home/lkugler/data/compile/WRF-4.3/run',
    dir_dart_src = '/jetfs/home/lkugler/data/compile/DART/DART-10.8.3/models/wrf/work/',
    dir_rttov_src = '/jetfs/home/lkugler/data/compile/RTTOV13/rtcoef_rttov13/',
    dir_dartwrf_dev = '/jetfs/home/lkugler/DART-WRF/',
    
    WRF_namelist_template = '/jetfs/home/lkugler/DART-WRF/templates/namelist.input',
    rttov_nml = "/jetfs/home/lkugler/DART-WRF/templates/obs_def_rttov.VIS+WV.nml",
    
    # other inputs
    #obs_impact_filename = dir_dartwrf_dev+'/templates/impactfactor_T.txt'

    WRF_exe_template = '/jetfs/home/lkugler/DART-WRF/templates/run_WRF.jet.sh',
    WRF_ideal_template = '/jetfs/home/lkugler/DART-WRF/templates/run_WRF_ideal.sh',

    slurm_kwargs = {"account": "lkugler", "partition": "devel", "time": "30",
                    "nodes": "1", "ntasks": "1", "ntasks-per-core": "1", "mem": "25G",
                    #"exclude": "jet07,jet11,jet16,jet18,jet19",
                    "mail-type": "FAIL,TIME_LIMIT_80", "mail-user": "lukas.kugler@univie.ac.at"},

    # WRF file format, will only change if WRF changes
    wrfout_format = '/wrfout_d01_%Y-%m-%d_%H:%M:%S',

    # pattern for the init_time folder in sim_archive
    pattern_init_time = "/%Y-%m-%d_%H:%M/",
    
    # how an obs_seq.out file is archived
    pattern_obs_seq_out = "<archivedir>/diagnostics/%Y-%m-%d_%H:%M_obs_seq.out",
        
    # how an obs_seq.final file is archived
    pattern_obs_seq_final = "<archivedir>/diagnostics/%Y-%m-%d_%H:%M_obs_seq.final",  

    )