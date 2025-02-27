import sys
import datetime as dt
import pandas as pd
from dartwrf.workflows import WorkFlows
from dartwrf.utils import Config


# import default config for jet
from config.jet import cluster_defaults
from config.defaults import dart_nml, CF_config


ensemble_size = 1
t0 = dt.datetime(2008, 7, 30, 8)

for c_s in [0.15, 0.2]:

    id = None
    cfg = Config(name='exp_nat250m_Cs'+str(c_s), 
        model_dx = 2000,
        ensemble_size = ensemble_size,
        geo_em_forecast = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
        time = t0,
        c_s = str(c_s),

        input_profile = '/jetfs/home/lkugler/data/sim_archive/nat_250m_1600x1600x100/2008-07-30_08:00/1/input_sounding',
        verify_against = 'nat_250m_blockavg2km',
        **cluster_defaults, # type: ignore
    )


    w = WorkFlows(cfg)
    w.prepare_WRFrundir(cfg)
    id = w.run_ideal(cfg, depends_on=id)

    timedelta_integrate = dt.timedelta(hours=10)
    restart_interval = 9999
    
    cfg.update( WRF_start=t0, 
                WRF_end=t0+timedelta_integrate, 
                restart=False, 
                restart_interval=restart_interval,
                hist_interval_s=300,
    )
    # only verification depends on the output
    id_long = w.run_WRF(cfg, depends_on=id)
    id_long = w.run_RTTOV(cfg, depends_on=id_long)
        
    w.verify(cfg, depends_on=id_long)