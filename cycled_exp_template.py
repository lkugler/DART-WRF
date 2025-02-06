#!/usr/bin/python3
import datetime as dt
from dartwrf.workflows import WorkFlows

if __name__ == "__main__":
    """
    Run a cycled OSSE with WRF and DART.
    """
    w = WorkFlows(exp_config='exp_template.py', server_config='jet.py')

    timedelta_integrate = dt.timedelta(minutes=15)
    timedelta_btw_assim = dt.timedelta(minutes=15)
    
    prior_path_exp = '/path_to/sim_archive/experiment_name/'
    init_time = dt.datetime(2008, 7, 30, 11,45)
    time = dt.datetime(2008, 7, 30, 12)
    last_assim_time = dt.datetime(2008, 7, 30, 13)
    forecast_until = dt.datetime(2008, 7, 30, 13,15)

    w.prepare_WRFrundir(init_time)
    # id = w.run_ideal(depends_on=id)

    # prior_path_exp = w.cluster.archivedir
    prior_init_time = init_time

    while time <= last_assim_time:

        # usually we take the prior from the current time
        # but one could use a prior from a different time from another run
        # i.e. 13z as a prior to assimilate 12z observations
        prior_valid_time = time

        id = w.assimilate(time, prior_init_time,
                          prior_valid_time, prior_path_exp, depends_on=id)

        # 1) Set posterior = prior
        id = w.prepare_IC_from_prior(
            prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

        # 2) Update posterior += updates from assimilation
        id = w.update_IC_from_DA(time, depends_on=id)

        # How long shall we integrate?
        timedelta_integrate = timedelta_btw_assim
        output_restart_interval = timedelta_btw_assim.total_seconds()/60
        if time == last_assim_time:
            timedelta_integrate = forecast_until - \
                last_assim_time  # dt.timedelta(hours=4)
            output_restart_interval = 9999  # no restart file after last assim

        # 3) Run WRF ensemble
        id = w.run_ENS(begin=time,  # start integration from here
                       end=time + timedelta_integrate,  # integrate until here
                       output_restart_interval=output_restart_interval,
                       depends_on=id)
        
        # as we have WRF output, we can use own exp path as prior
        prior_path_exp = w.cluster.archivedir

        # depends on the RTTOV-WRF repository
        id = w.create_satimages(time, depends_on=id)

        # increment time
        time += timedelta_btw_assim

        # update time variables
        prior_init_time = time - timedelta_btw_assim

    # not publically available
    # w.verify_sat(id)
    # w.verify_wrf(id)
