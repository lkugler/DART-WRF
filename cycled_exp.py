#!/usr/bin/python3
import os, sys, shutil, glob, warnings
import datetime as dt
from dartwrf.workflows import WorkFlows

if __name__ == "__main__":
    """
    Run a cycled OSSE with WRF and DART.
    """
    w = WorkFlows(exp_config='exp_template.py', server_config='jet.py')

    timedelta_integrate = dt.timedelta(minutes=15)
    timedelta_btw_assim = dt.timedelta(minutes=15)

    id = None

    if True:  # warm bubble
        prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P3_wbub7_noDA'

        init_time = dt.datetime(2008, 7, 30, 12)
        time = dt.datetime(2008, 7, 30, 12, 30)
        last_assim_time = dt.datetime(2008, 7, 30, 13,30)
        forecast_until = dt.datetime(2008, 7, 30, 18)
    
        w.prepare_WRFrundir(init_time)
        # id = w.run_ideal(depends_on=id)
        # id = w.wrfinput_insert_wbubble(depends_on=id)    

    if False:  # random
        prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P2_noDA'

        init_time = dt.datetime(2008, 7, 30, 7)
        time = dt.datetime(2008, 7, 30, 12)
        last_assim_time = dt.datetime(2008, 7, 30, 14)
        forecast_until = dt.datetime(2008, 7, 30, 18)

        w.prepare_WRFrundir(init_time)
        # id = w.run_ideal(depends_on=id)

    # prior_path_exp = w.cluster.archivedir
    
    prior_init_time = init_time
    prior_valid_time = time

    while time <= last_assim_time:

        # usually we take the prior from the current time
        # but one could use a prior from a different time from another run
        # i.e. 13z as a prior to assimilate 12z observations
        prior_valid_time = time

        id = w.assimilate(time, prior_init_time, prior_valid_time, prior_path_exp, depends_on=id)
        
        # 1) Set posterior = prior
        id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

        # 2) Update posterior += updates from assimilation
        id = w.update_IC_from_DA(time, depends_on=id)

        # How long shall we integrate?
        timedelta_integrate = timedelta_btw_assim
        output_restart_interval = timedelta_btw_assim.total_seconds()/60
        if time == last_assim_time:  # this_forecast_init.minute in [0,]:  # longer forecast every full hour
            timedelta_integrate = forecast_until - last_assim_time  # dt.timedelta(hours=4)
            output_restart_interval = 9999  # no restart file after last assim

        # 3) Run WRF ensemble
        id = w.run_ENS(begin=time,  # start integration from here
                    end=time + timedelta_integrate,  # integrate until here
                    output_restart_interval=output_restart_interval,
                    first_minutes=True,
                    depends_on=id)
        
        # as we have WRF output, we can use own exp path as prior
        prior_path_exp = w.cluster.archivedir
        # prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P2_noDA/'

        id_sat = w.create_satimages(time, depends_on=id)
        
        # increment time
        time += timedelta_btw_assim

        # update time variables
        prior_init_time = time - timedelta_btw_assim

    w.verify_sat(id_sat)
    w.verify_wrf(id)


# assim_times = [dt.datetime(2008,7,30,12,30), ] 
# time range from 12:30 to 13:30 every 15 minutes
assim_times = [dt.datetime(2008,7,30,12,30) + dt.timedelta(minutes=15*i) for i in range(5)]
tuples = []
for init in assim_times:
    for s in range(30,3*60+1,30):
        tuples.append((init, init+dt.timedelta(seconds=s)))


# evaluate the forecast at +1 minute after the assimilation time
w.evaluate_obs_posterior_after_analysis(tuples, depends_on=id)
