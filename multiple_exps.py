import datetime as dt
import pandas as pd
from dartwrf.workflows import WorkFlows
from dartwrf.utils import Config


# import default config for jet
from config.jet import cluster_defaults
from config.defaults import dart_nml

# test multiple assimilation windows (11-12, 12-13, 13-14, )
timedelta_btw_assim = dt.timedelta(minutes=15)
assim_times_start = pd.date_range('2008-07-30 11:00', '2008-07-30 13:00', freq='h')

for t0 in assim_times_start:


    id = None
    ensemble_size = 3
    
    dart_nml['&filter_nml'].update(num_output_state_members=ensemble_size,
                                   ens_size=ensemble_size)
            
    t_raso = dict(var_name='Temperature', unit='[K]',
            kind='RADIOSONDE_TEMPERATURE',
            obs_locations=[(45., 0.)],
            error_generate=0.2, error_assimilate=0.6,
            heights=range(1000, 15001, 500),
            loc_horiz_km=100, loc_vert_km=3)
            
    cfg = Config(name='test_exp', 
        model_dx = 2000,
        ensemble_size = ensemble_size,
        dart_nml = dart_nml,
        geo_em_forecast = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
        time = dt.datetime(2008, 7, 30, 11),
        
        use_existing_obsseq = False,
        nature_wrfout_pattern = '/jetfs/home/lkugler/data/sim_archive/nat_250m_1600x1600x100/*/1/wrfout_d01_%Y-%m-%d_%H_%M_%S',
        #geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
        geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.250m_1600x1600',
        
        update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QSNOW', 'PSFC'],
        input_profile = '/jetfs/home/lkugler/data/sim_archive/nat_250m_1600x1600x100/2008-07-30_08:00/1/input_sounding',
        nature_exp_verif = 'nat_250m_blockavg2km',
        assimilate_these_observations = [t_raso,],
        **cluster_defaults, # type: ignore
    )

    # test multiple assimilation windows (11-12, 12-13, 13-14, )
    timedelta_btw_assim = dt.timedelta(minutes=15)
    #pd.date_range('2008-07-30 11:00', '2008-07-30 13:00', freq='h')

    
    w = WorkFlows(cfg)
    w.prepare_WRFrundir(cfg)
    #id = w.run_ideal(cfg, depends_on=id)
    
    # assimilate at these times
    time0 = cfg.time
    assim_times = pd.date_range(time0, time0 + timedelta_btw_assim, freq=timedelta_btw_assim)
    last_assim_time = assim_times[-1]

    # loop over assimilations
    for i, t in enumerate(assim_times):
        
        if i == 0:
            cfg.update(time = t,
                prior_init_time = dt.datetime(2008, 7, 30, 8),
                prior_valid_time = t,
                prior_path_exp = '/jetfs/home/lkugler/data/sim_archive/exp_nat250m_noDA/',)
        else:
            cfg.update(time = t,
                prior_init_time = assim_times[i-1],
                prior_valid_time = t,
                prior_path_exp = cfg.dir_archive,)
                    
                    
        id = w.assimilate(cfg, depends_on=id)

        # 1) Set posterior = prior
        id = w.prepare_IC_from_prior(cfg, depends_on=id)

        # 2) Update posterior += updates from assimilation
        id = w.update_IC_from_DA(cfg, depends_on=id)

        # How long shall we integrate?
        timedelta_integrate = dt.timedelta(minutes=5)

        cfg.update( WRF_start=t, 
                    WRF_end=t+timedelta_integrate, 
                    restart=True, 
                    restart_interval=9999,
                    hist_interval_s=300,
        )

        # 3) Run WRF ensemble
        id = w.run_WRF(cfg, depends_on=id)