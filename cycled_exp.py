#!/usr/bin/python3
import os
import sys
import datetime as dt
from dartwrf.workflows import WorkFlows
from dartwrf.utils import save_dict

if __name__ == "__main__":
    """
    Run a cycled OSSE with WRF and DART.
    """
    w = WorkFlows(exp_config='exp_hires.py', server_config='jet_ACF.py')

    timedelta_integrate = dt.timedelta(minutes=15)
    timedelta_btw_assim = dt.timedelta(minutes=15)

    id = None

    if False:  # warm bubble
        prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P3_wbub7_noDA'

        init_time = dt.datetime(2008, 7, 30, 12)
        time = dt.datetime(2008, 7, 30, 12, 30)
        last_assim_time = dt.datetime(2008, 7, 30, 13, 30)
        forecast_until = dt.datetime(2008, 7, 30, 18)

        w.prepare_WRFrundir(init_time)
        # id = w.run_ideal(depends_on=id)
        # id = w.wrfinput_insert_wbubble(depends_on=id)

        prior_path_exp = '/jetfs/scratch/a11716773/master_thesis_2023/data2/sim_archive/free_ens/'
        init_time = dt.datetime(2008, 7, 30, 11)
        time = dt.datetime(2008, 7, 30, 12)
        last_assim_time = dt.datetime(2008, 7, 30, 13)
        forecast_until = dt.datetime(2008, 7, 30, 17)

        prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P2_noDA+1/'
        init_time = dt.datetime(2008, 7, 30, 12, 30)
        time = dt.datetime(2008, 7, 30, 13)
        last_assim_time = dt.datetime(2008, 7, 30, 14)
        forecast_until = dt.datetime(2008, 7, 30, 18)

    if True:  # random
        # exp_v1.19_P2_noDA+1/'
        prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_nat250m_noDA_f/'
        init_time = dt.datetime(2008, 7, 30, 11,45)
        time = dt.datetime(2008, 7, 30, 12)
        last_assim_time = dt.datetime(2008, 7, 30, 13)
        forecast_until = dt.datetime(2008, 7, 30, 18)

        w.prepare_WRFrundir(init_time)
        # id = w.run_ideal(depends_on=id)

    # prior_path_exp = w.cluster.archivedir
    prior_init_time = init_time

    while time <= last_assim_time:

        # usually we take the prior from the current time
        # but one could use a prior from a different time from another run
        # i.e. 13z as a prior to assimilate 12z observations
        prior_valid_time = time

        if True:
            ACF_config = dict(
                var='WV73',
                scales_km=(192, 96, 48, 24, 12),
                observed_width_km=384,
                dx_km_obs=1.0,
                dx_km_forecast=2.0,
                # ('value', 0.6), #('percentile', 30), #('value', 230), #('value', 0.6), #('value', 230), #('percentile', 90),  # ('value', 0.6),  #
                threshold=('value', 230),
                difference=True,
                first_guess_pattern='/RT_wrfout_d01_%Y-%m-%d_%H:%M:%S.nc',

                # observed_data='/jetfs/scratch/a11716773/master_thesis_2023/data2/sim_archive/nature_dx=2000m/RT_wrfout_d01_%Y-%m-%d_%H:%M:%S.nc',
                observed_data='/jetfs/home/lkugler/data/sim_archive/nat_250m_obs1km/2008-07-30_12:00/1/RT_wrfout_d01_%Y-%m-%d_%H_%M_%S.nc',
                # observed_data='/jetfs/home/lkugler/data/sim_archive/exp_v1.18_P1_nature+1/2008-07-30_06:00/1/RT_wrfout_d01_%Y-%m-%d_%H_%M_%S.nc',
                f_grid_obs='/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.250m-1km_400x400',

                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/hrNat_VIS/OE_VIS_CF_0.6.csv',
                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/hrNat_VIS/OE_VIS_CF_0.6_difference.csv',
                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/hrNat_VIS/OE_VIS_SO_difference.csv',
                #obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/hrNat_IR/OE-WV73_CF_230.csv',
                obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/hrNat_IR/OE-WV73_CF_230_difference.csv',
                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/hrNat_IR/OE-WV73_superobs.csv',
                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/hrNat_IR/OE-WV73_SO_difference.csv',

                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/exp_v1.18_P1_nature+1/OE-STDEV_delta_192-6_12z-14z.csv',
                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/exp_v1.18_P1_nature+1/obs_error_stddev_delta_approach_12z-14z.csv'
                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/OE_WV73_SO_theoretical.csv',
                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/OE_VIS_SO_theoretical.csv',
                # obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/obs_error_stddev_andrea.csv',
                inflation_OE_var=2.0,
            )
            # if time.minute == 0:  # first and last assimilation
            #     ACF_config['scales_km'] = (192, 96, 48, 24, 12)
            # else:
            #     ACF_config['scales_km'] = (24, 12)

            save_dict(ACF_config, time.strftime(
                w.cluster.scripts_rundir+'/ACF_config_%H%M.pkl'))

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
                       first_second=False,  # to get a +1 second forecast after each restart
                       depends_on=id)

        # evaluate the forecast at +1 second after the assimilation time
        # _ = w.evaluate_obs_posterior_after_analysis(time, time+dt.timedelta(seconds=1), depends_on=id)

        # as we have WRF output, we can use own exp path as prior
        # prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P2_noDA/'
        prior_path_exp = w.cluster.archivedir

        id = w.create_satimages(time, depends_on=id)

        # increment time
        time += timedelta_btw_assim

        # update time variables
        prior_init_time = time - timedelta_btw_assim

    w.verify_sat(id)
    w.verify_wrf(id)
