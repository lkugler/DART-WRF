import datetime as dt
import sys
import pandas as pd
from dartwrf.workflows import WorkFlows
from config import defaults


# test multiple assimilation windows (11-12, 12-13, 13-14, )
timedelta_btw_assim = dt.timedelta(minutes=15)
assim_times_start = pd.date_range('2000-01-01 11:00', '2000-01-01 13:00', freq='h')
    
for t0 in assim_times_start:

    # set constants
    w = WorkFlows(server_config='/jetfs/home/lkugler/DART-WRF/config/jet.py', 
                   expname=t0.strftime('test_%H%M'))
   
    # set potentially varying parameters
    ens_size = 3
    dart_nml = defaults.dart_nml
    dart_nml.update(ens_size=ens_size)
    
    w.configure(model_dx=2000, 
                ensemble_size=3,
                dart_nml = dart_nml,
                use_existing_obsseq=False,
                update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QSNOW', 'PSFC'],
                input_profile = '/mnt/jetfs/home/lkugler/data/initial_profiles/wrf/ens/2022-03-31/raso.fc.<iens>.wrfprof',
                nature_wrfout_pattern = '/jetfs/home/lkugler/data/sim_archive/exp_v1.18_P1_nature+1/*/1/wrfout_d01_%Y-%m-%d_%H:%M:%S',
                nature_exp = 'nat_250m_blockavg2km',)

    
    time = t0
    id = None
    w.prepare_WRFrundir(time)
    id = w.run_ideal(depends_on=id)
    sys.exit()
    
    prior_init_time = time - dt.timedelta(hours=1)
    prior_valid_time = time
    prior_path_exp = '/jetfs/home/lkugler/data/sim_archive/exp_v1.19_P2_noDA+1/'
    
    # assimilate at these times
    assim_times = pd.date_range(time, time + dt.timedelta(hours=1), freq=timedelta_btw_assim)
    last_assim_time = assim_times[-1]
    
    # loop over assimilations
    for i, t in enumerate(assim_times):
        
        id = w.assimilate(time, prior_init_time, prior_valid_time, prior_path_exp, depends_on=id)

        # 1) Set posterior = prior
        id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

        # 2) Update posterior += updates from assimilation
        id = w.update_IC_from_DA(time, depends_on=id)

        # How long shall we integrate?
        timedelta_integrate = timedelta_btw_assim
        output_restart_interval = timedelta_btw_assim.total_seconds()/60
        if time == last_assim_time:
            timedelta_integrate = dt.timedelta(hours=4)
            output_restart_interval = 9999  # no restart file after last assim

        # 3) Run WRF ensemble
        id = w.run_ENS(begin=time,  # start integration from here
                       end=time + timedelta_integrate,  # integrate until here
                       output_restart_interval=output_restart_interval,
                       depends_on=id)
        
        if t < last_assim_time:
            # continue the next cycle
            prior_init_time = assim_times[i]
            prior_valid_time = assim_times[i+1]
            prior_path_exp = w.archivedir  # use own exp path as prior
        else:
            # exit the cycles
            break
        