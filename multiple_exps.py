import sys
import datetime as dt
import pandas as pd
from dartwrf.workflows import WorkFlows
from dartwrf.utils import Config


# import default config for jet
from config.jet import cluster_defaults
from config.defaults import dart_nml, CF_config, vis


ensemble_size = 40

dart_nml['&filter_nml'].update(num_output_state_members=ensemble_size,
                               ens_size=ensemble_size)

# which DART version to use?
assimilate_cloudfractions = False

# scale_km = 2
# cf = dict(kind='CF{}km'.format(scale_km), loc_horiz_km=scale_km)

cf1 = dict(kind='CF192km', loc_horiz_km=9999,
           )
cf2 = dict(kind='CF96km', loc_horiz_km=96,
           )
cf3 = dict(kind='CF48km', loc_horiz_km=48,
           )
cf4 = dict(kind='CF24km', loc_horiz_km=24,
           )
cf5 = dict(kind='CF12km', loc_horiz_km=12,
           )
cf6 = dict(kind='CF6km', loc_horiz_km=6,
           )

assimilate_these_observations = [vis,] #cf3, cf4, cf5,]

if assimilate_cloudfractions:
    cluster_defaults.update(
        dir_dart_src = '/jetfs/home/lkugler/data/compile/DART/DART-v10.9.2-andrea/models/wrf/work/',
    )
else:
    for obs in assimilate_these_observations:
        if obs['kind'] == 'MSG_4_SEVIRI_BDRF':
            cluster_defaults.update(
                dir_dart_src = '/jetfs/home/lkugler/data/compile/DART/DART-10.8.3_10pct/models/wrf/work/',
                )


time0 = dt.datetime(2008, 7, 30, 11)
time_end = dt.datetime(2008, 7, 30, 15)

id = None
cfg = Config(name='exp_nat250_VIS_obs12_loc12_oe2_inf4-0.5',
    model_dx = 2000,
    ensemble_size = ensemble_size,
    dart_nml = dart_nml,
    geo_em_forecast = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
    time = time0,
    
    assimilate_these_observations = assimilate_these_observations,
    assimilate_cloudfractions = assimilate_cloudfractions,
    CF_config=CF_config,
    
    assimilate_existing_obsseq = False,
    nature_wrfout_pattern = '/jetfs/home/lkugler/data/sim_archive/nat_250m_1600x1600x100/*/1/wrfout_d01_%Y-%m-%d_%H_%M_%S',
    #geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.2km_200x200',
    geo_em_nature = '/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.250m_1600x1600',
    
    update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QSNOW', 'PSFC'],
    #input_profile = '/jetfs/home/lkugler/data/sim_archive/nat_250m_1600x1600x100/2008-07-30_08:00/1/input_sounding',
    verify_against = 'nat_250m_blockavg2km',
    **cluster_defaults)


w = WorkFlows(cfg)
w.prepare_WRFrundir(cfg)
# id = w.run_ideal(cfg, depends_on=id)

# assimilate at these times
timedelta_btw_assim = dt.timedelta(minutes=15)
assim_times = pd.date_range(time0, time_end, freq=timedelta_btw_assim)
#assim_times = [dt.datetime(2008, 7, 30, 12), dt.datetime(2008, 7, 30, 13), dt.datetime(2008, 7, 30, 14),]
last_assim_time = assim_times[-1]


# loop over assimilations
for i, t in enumerate(assim_times):

    # which scales?
    # if t.minute == 0:
    #     CF_config.update(scales_km=(48, 24, 12),)
    # else:
    #     CF_config.update(scales_km=(12,))
        
    #cfg.update(CF_config=CF_config)
    
    if i == 0 and t == dt.datetime(2008, 7, 30, 11):
        cfg.update(
            time = t,
            prior_init_time = dt.datetime(2008, 7, 30, 8),
            prior_valid_time = t,
            prior_path_exp = '/jetfs/home/lkugler/data/sim_archive/exp_nat250m_noDA/',)
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
        timedelta_integrate = dt.timedelta(hours=.25)
        restart_interval = 9999
        
        cfg.update( WRF_start=t, 
                    WRF_end=t+timedelta_integrate, 
                    restart=True, 
                    restart_interval=restart_interval,
                    hist_interval_s=300,
        )
        # only verification depends on the output
        # but we only have one run directory, so we need to wait until the other forecast is done
        id = w.run_WRF(cfg, depends_on=id)
        id = w.run_RTTOV(cfg, depends_on=id)
    
        w.verify(cfg, init=True, depends_on=id)
        
# verify the rest
w.verify(cfg, depends_on=id)