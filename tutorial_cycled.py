import sys
import datetime as dt
import pandas as pd
from dartwrf.workflows import WorkFlows
from dartwrf.utils import Config

from config.jet import cluster_defaults
from config.defaults import dart_nml, CF_config, wv73, vis


ensemble_size = 40

dart_nml['&filter_nml'].update(num_output_state_members=ensemble_size,
                               ens_size=ensemble_size)

assimilate_these_observations = [wv73,]

time_start = dt.datetime(2008, 7, 30, 11)
time_end = dt.datetime(2008, 7, 30, 12, 30)

id = None
cfg = Config(name='exp1',
    model_dx = 2000,
    ensemble_size = ensemble_size,
    dart_nml = dart_nml,
    geo_em_forecast = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
    time = time_start,
    
    assimilate_these_observations = assimilate_these_observations,
    
    assimilate_existing_obsseq = False,
    #nature_wrfout_pattern = '/jetfs/home/lkugler/data/sim_archive/nat_250m_1600x1600x100/*/1/wrfout_d01_%Y-%m-%d_%H_%M_%S',
    #geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
    #geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.250m_1600x1600',
    
    update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QSNOW', 'PSFC'],
    **cluster_defaults)

w = WorkFlows(cfg)
w.prepare_WRFrundir(cfg)
# id = w.run_ideal(cfg, depends_on=id)

timedelta_btw_assim = dt.timedelta(minutes=15)
assim_times = pd.date_range(time_start, time_end, freq=timedelta_btw_assim)
last_assim_time = assim_times[-1]


# loop over assimilations
for i, t in enumerate(assim_times):
    
    if i == 0 and t == dt.datetime(2008, 7, 30, 11):
        cfg.update(
            time = t,
            prior_init_time = dt.datetime(2008, 7, 30, 8),
            prior_valid_time = t,
            prior_path_exp = '/jetfs/scratch/sim_archive/exp_another/',)
    else:
        cfg.update(
            time = t,
            prior_init_time = t - dt.timedelta(minutes=15),
            prior_valid_time = t,
            prior_path_exp = cfg.dir_archive,)

    id = w.assimilate(cfg, depends_on=id)

    # 1) Set posterior = prior
    id = w.prepare_IC_from_prior(cfg, depends_on=id)

    # 2) Update posterior += updates from assimilation
    id = w.update_IC_from_DA(cfg, depends_on=id)
    
    if t != last_assim_time:
        # integrate until next assimilation
        timedelta_integrate = dt.timedelta(minutes=15)
        restart_interval = timedelta_btw_assim.total_seconds()/60  # in minutes

        cfg.update( WRF_start=t, 
                    WRF_end=t+timedelta_integrate, 
                    restart=True, 
                    restart_interval=restart_interval,
                    hist_interval_s=300,
        )

        # 3) Run WRF ensemble
        id = w.run_WRF(cfg, depends_on=id)
        id = w.run_RTTOV(cfg, depends_on=id)
    
    if t.minute == 0 and i != 0:
        # full hour but not first one
        # make long forecasts without restart files
        timedelta_integrate = dt.timedelta(hours=4)
        restart_interval = 9999
        
        cfg.update( WRF_start=t, 
                    WRF_end=t+timedelta_integrate, 
                    restart=True, 
                    restart_interval=restart_interval,
                    hist_interval_s=300,
        )

        id = w.run_WRF(cfg, depends_on=id)
        id = w.run_RTTOV(cfg, depends_on=id)
    
w.verify(cfg, depends_on=id)