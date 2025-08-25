import sys, os
import datetime as dt
import pandas as pd
from dartwrf.workflows import WorkFlows
from dartwrf.utils import Config, symlink


# import default config for jet
from config.jet import cluster_defaults
#from config.defaults import dart_nml, CF_config


ensemble_size = 40
t0 = dt.datetime(2008, 7, 30, 8)
id = None

cfg = Config(name='exp_nat250m_noDA_b', 
    model_dx = 2000,
    ensemble_size = ensemble_size,
    #geo_em_forecast = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
    time = t0,

    input_profile = '/jetfs/home/lkugler/data/sim_archive/nat_250m_1600x1600x100/2008-07-30_08:00/1/input_sounding',
    verify_against = 'nat_250m_blockavg2km',
    **cluster_defaults, # type: ignore
)


w = WorkFlows(cfg)
#w.prepare_WRFrundir(cfg)
#id = w.run_ideal(cfg, depends_on=id)


# for iens in range(1, cfg.ensemble_size+1):
#     src = '/jetfs/home/lkugler/data/sim_archive/exp_nat250m_noDA/2008-07-30_08:00/'+str(iens)+'/wrfinput_d01'
#     dst = '/jetfs/home/lkugler/data/run_WRF/exp_nat250m_noDA_b/'+str(iens)+'/wrfinput_d01'
#     symlink(src, dst)

inits = [t0]
inits += list(pd.date_range(start=dt.datetime(2008, 7, 30, 11),
                            end=dt.datetime(2008, 7, 30, 11, 30),
                            freq=dt.timedelta(minutes=15)))
last_init = inits[-1]
time = t0


for i, time in enumerate(inits):
    print(i, time)
    
    if i != 0:
        cfg.update(
            time = time,
            prior_init_time = inits[i-1],
            prior_valid_time = time,
            prior_path_exp = cfg.dir_archive,)
    
        id = w.prepare_IC_from_prior(cfg, depends_on=id)
    
    if time == last_init:
        restart_interval = 9999
        t_end_integration = dt.datetime(2008, 7, 30, 18)
    else:
        restart_interval = (inits[i+1] - time).total_seconds()/60  # in minutes
        t_end_integration = inits[i+1]

    if i == 0:
        restart = False
    else:
        restart = True

    cfg.update( time=time,
                WRF_start=time, 
                WRF_end=t_end_integration, 
                restart=restart, 
                restart_interval=restart_interval,
                hist_interval_s=300,
    )
    id = w.run_WRF(cfg, depends_on=id)
    
    #id = w.run_RTTOV(cfg, depends_on=id)

#w.verify(cfg, depends_on=id)