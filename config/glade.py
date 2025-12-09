"""Cluster configuration file, see docstring of ClusterConfig class in dartwrf/utils.py for details"""

cluster_defaults = dict(
    max_nproc = 10,
    max_nproc_for_each_ensemble_member = 9,

    # binaries
    python = '/glade/u/apps/casper/24.12/opt/view/bin/python',
    ncks = '/glade/u/apps/casper/24.12/spack/opt/spack/nco/5.3.1/gcc/12.4.0/xj2m/bin/ncks',
    wrfexe = '/glade/work/lkugler/compile/WRFV4.7.1/main/wrf.exe',
    dart_modules = 'module purge; module load nco',
    wrf_modules = 'module purge; module load netcdf-fortran',

    # paths for data output
    dir_wrf_run = '/glade/derecho/scratch/lkugler/run_WRF/<exp>/<ens>/',  # path for temporary files
    dir_dart_run = '/glade/derecho/scratch/lkugler/run_DART/<exp>/',  # path for temporary files
    dir_archive = '/glade/work/lkugler/sim_archive/<exp>/',

    # paths used as input
    dir_wrf_src = '/glade/work/lkugler/compile/WRFV4.7.1/run/',
    dir_dart_src = '/glade/work/lkugler/compile/DART/DART-10.8.3/models/wrf/work/',
    dir_rttov_src = '/glade/work/lkugler/compile/RTTOV13/rtcoef_rttov13/',
    dir_dartwrf_dev = '/glade/u/home/lkugler/DART-WRF/',
    
    WRF_namelist_template = '/glade/u/home/lkugler/DART-WRF/templates/namelist.input',
    rttov_nml = "/glade/u/home/lkugler/DART-WRF/templates/obs_def_rttov.VIS+WV.nml",
    
    WRF_exe_template = '/glade/u/home/lkugler/DART-WRF/templates/run_WRF.jet.sh',
    WRF_ideal_template = '/glade/u/home/lkugler/DART-WRF/templates/run_WRF_ideal.sh',

    scheduler = 'pbs',
    scheduler_kwargs = {"-A": "P86850054", "-q": "main", "-l": "walltime=01:00:00",
                        "mem": 10*1024, # in MB
                        "nodes": 1, "ppn": 1},

    # WRF file format, will only change if WRF changes
    wrfout_format = '/wrfout_d01_%Y-%m-%d_%H:%M:%S',

    # pattern for the init_time folder in sim_archive
    pattern_init_time = "/%Y-%m-%d_%H:%M/",
    
    # how an obs_seq.out file is archived
    pattern_obs_seq_out = "<archivedir>/diagnostics/%Y-%m-%d_%H:%M_obs_seq.out",
        
    # how an obs_seq.final file is archived
    pattern_obs_seq_final = "<archivedir>/diagnostics/%Y-%m-%d_%H:%M_obs_seq.final",  

    )