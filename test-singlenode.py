from timer import Timer


with Timer('imports'):
    import datetime as dt
    import pandas as pd
    from dartwrf.workflows import WorkFlows
    from dartwrf.utils import Config, run_bash_command_in_directory

    # import default config for jet
    from config.jet_1node import cluster_defaults
    from config.defaults import dart_nml


ensemble_size = 5

dart_nml['&filter_nml'].update(num_output_state_members=ensemble_size,
                               ens_size=ensemble_size)


t = dict(var_name='Temperature', unit='[K]',
         kind='RADIOSONDE_TEMPERATURE',
         # n_obs=22500,
         n_obs=1, obs_locations=[(45., 0.)],
         error_generate=0.2, error_assimilate=0.2,
         heights=range(1000, 17001, 2000),
         loc_horiz_km=1000, loc_vert_km=4)

assimilate_these_observations = [t,] #cf3, cf4, cf5,]


time0 = dt.datetime(2008, 7, 30, 11)
time_end = dt.datetime(2008, 7, 30, 11)

id = None
with Timer('Config()'):
    cfg = Config(name='test-1node',
        model_dx = 2000,
        ensemble_size = ensemble_size,
        dart_nml = dart_nml,
        geo_em_forecast = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
        time = time0,
        
        assimilate_these_observations = assimilate_these_observations,
        assimilate_existing_obsseq = False,
        
        nature_wrfout_pattern = '/jetfs/home/lkugler/data/sim_archive/exp_v1.18_P1_nature+1/*/1/wrfout_d01_%Y-%m-%d_%H:%M:%S',
        geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
        
        update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QSNOW', 'PSFC'],
        #input_profile = '/jetfs/home/lkugler/data/sim_archive/nat_250m_1600x1600x100/2008-07-30_08:00/1/input_sounding',
        verify_against = 'nat_250m_blockavg2km',
        **cluster_defaults)

with Timer('prepare_WRFrundir'):
    w = WorkFlows(cfg)
    import dartwrf.prepare_wrfrundir as prepwrf
    prepwrf.run(cfg)
    # w.prepare_WRFrundir(cfg)

# id = w.run_ideal(cfg, depends_on=id)

# assimilate at these times
timedelta_btw_assim = dt.timedelta(minutes=15)
assim_times = pd.date_range(time0, time_end, freq=timedelta_btw_assim)
#assim_times = [dt.datetime(2008, 7, 30, 12), dt.datetime(2008, 7, 30, 13), dt.datetime(2008, 7, 30, 14),]
last_assim_time = assim_times[-1]


# loop over assimilations
for i, t in enumerate(assim_times):

    if i == 0 and t == dt.datetime(2008, 7, 30, 11):
        cfg.update(
            time = t,
            prior_init_time = dt.datetime(2008, 7, 30, 8),
            prior_valid_time = t,
            prior_path_exp = '/jetfs/home/lkugler/data/sim_archive/exp_nat250m_noDA/')
    else:
        cfg.update(
            time = t,
            prior_init_time = t - dt.timedelta(minutes=15),
            prior_valid_time = t,
            prior_path_exp = cfg.dir_archive,)

    with Timer('assimilate'):
        #id = w.assimilate(cfg, depends_on=id)
        import dartwrf.assimilate as da
        da.main(cfg)

    with Timer('prepare_IC_from_prior'):
        # 1) Set posterior = prior
        #id = w.prepare_IC_from_prior(cfg, depends_on=id)
        import dartwrf.prep_IC_prior as prep
        prep.main(cfg)

    with Timer('update_IC_from_DA'):
        # 2) Update posterior += updates from assimilation
        #id = w.update_IC_from_DA(cfg, depends_on=id)
        import dartwrf.update_IC as upd
        upd.update_initials_in_WRF_rundir(cfg)
    
    # integrate until next assimilation
    timedelta_integrate = dt.timedelta(minutes=15)
    restart_interval = timedelta_btw_assim.total_seconds()/60  # in minutes

    cfg.update( WRF_start=t, 
                WRF_end=t+timedelta_integrate, 
                restart=True, 
                restart_interval=restart_interval,
                hist_interval_s=300,
    )

    import dartwrf.prepare_namelist as prepnl
    prepnl.run(cfg)

    # 3) Run WRF ensemble
    #id = w.run_WRF(cfg, depends_on=id)

    with Timer('run_WRF'):
        # Example usage:
        cmd = cfg.wrf_modules +'; '
        
        for iens in range(1, cfg.ensemble_size+1):
            dir_wrf_run = cfg.dir_wrf_run.replace('<exp>', cfg.name).replace('<ens>', str(iens))

            cmd += 'cd ' + dir_wrf_run + '; '
            cmd += 'echo "'+dir_wrf_run+'"; '
            cmd += 'mpirun -np 4 ./wrf.exe & '

        cmd += 'wait; '
        cmd += 'echo "WRF run completed."'

        # Run the command in the specified directory
        run_bash_command_in_directory(cmd, dir_wrf_run)
