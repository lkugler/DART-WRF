#!/usr/bin/python3
"""
running the forecast model without assimilation
"""
import os
import sys
import datetime as dt
import pandas as pd
from dartwrf.workflows import WorkFlows


w = WorkFlows(exp_config='exp_noda.py', server_config='jet.py')
id = None


if False:  # generate_nature
    begin = dt.datetime(2008, 7, 30, 7)
    w.prepare_WRFrundir(begin)  # create initial conditions
    id = w.run_ideal(depends_on=id)

    # id = wrfinput_insert_wbubble(perturb=False, depends_on=id)
    end = dt.datetime(2008, 7, 30, 12)
    id = w.run_ENS(begin=begin, end=end,
                   input_is_restart=False,
                   output_restart_interval=(end-begin).total_seconds()/60,
                   depends_on=id)
    # id = w.create_satimages(begin, depends_on=id)


if False:  # to continue a nature

    start = dt.datetime(2008, 7, 30, 13, 45)
    w.prepare_WRFrundir(start)  # create initial conditions
    # id = w.run_ideal(depends_on=id)

    # w.cluster.archivedir
    prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive//exp_v1.18_P1_nature+1b/'

    time = start
    prior_init_time = dt.datetime(2008, 7, 30, 13, 30)
    end = start + dt.timedelta(minutes=15)

    id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, start,
                                 depends_on=id)
    id = w.run_ENS(begin=start, end=end,
                   input_is_restart=True,
                   first_second=True,  # to get a +1 minute forecast after each restart
                   # output_restart_interval=(end-start).total_seconds()/60,
                   output_restart_interval=9999,
                   depends_on=id)


    restarts = pd.date_range(start=dt.datetime(2008, 7, 30, 12, 30),
                             end=dt.datetime(2008, 7, 30, 14),
                             freq=dt.timedelta(minutes=30))

    for i, next_restart in enumerate(restarts):

        prior_valid_time = time
        id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time,
                                     depends_on=id)

        # integration time
        start = time
        end = next_restart

        id = w.run_ENS(begin=start, end=end,
                       input_is_restart=True,
                       first_second=True,  # to get a +1 minute forecast after each restart
                       output_restart_interval=(end-start).total_seconds()/60,
                       # output_restart_interval=9999,
                       depends_on=id)

        w.create_satimages(start, depends_on=id)

        prior_init_time = time  # this iteration's start
        time = end  # this iteration's end = next iteration's start

    # after last restart
    prior_valid_time = time
    id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time,
                                 depends_on=id)

    end = time + dt.timedelta(minutes=5)
    id = w.run_ENS(begin=time, end=end,
                   input_is_restart=True,
                   first_second=True,  # to get a +1 minute forecast after each restart
                   output_restart_interval=9999,
                   depends_on=id)

    w.create_satimages(start, depends_on=id)


if True:   # do a free run (all inits)

    inits = [dt.datetime(2008, 7, 30, 8)]
    inits += list(pd.date_range(start=dt.datetime(2008, 7, 30, 11),
                                end=dt.datetime(2008, 7, 30, 14),
                                freq=dt.timedelta(minutes=15)))
    
    input_is_restart = False
    
    # w.prepare_WRFrundir(inits[0])  # create initial conditions
    #id = w.run_ideal(depends_on=id)
    #sys.exit()

    # id = wrfinput_insert_wbubble(perturb=True, depends_on=id)
    time = inits[0]
    last_init = dt.datetime(2008, 7, 30, 8)
    
    for i, next_restart in enumerate(inits[1:]):
        print('run_WRF from', time, 'to', next_restart, 'rst intv', (next_restart-time).total_seconds()/60)

        prior_path_exp = w.cluster.archivedir #'/jetfs/scratch/lkugler/data/sim_archive/exp_v1.23_P2_noDA+1/'
        prior_init_time = last_init
        prior_valid_time = time
        
        if input_is_restart:
            id = w.prepare_IC_from_prior(
                prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

        id = w.run_ENS(begin=time, end=next_restart,
                       input_is_restart=input_is_restart,
                       output_restart_interval=(next_restart-time).total_seconds()/60,
                       depends_on=id)

        id_sat = w.create_satimages(time, depends_on=id)
        last_init = time
        time = next_restart
        input_is_restart = True


    # free run, no restart files anymore
    prior_init_time = last_init
    prior_valid_time = time
    id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)
    end = dt.datetime(2008, 7, 30, 18)
    print('run WRF from', time, 'until', end)
    id = w.run_ENS(begin=time, end=end,
             input_is_restart=input_is_restart,
             #output_restart_interval=(next_restart-time).total_seconds()/60,
             output_restart_interval=9999,
             depends_on=id)
    id = w.create_satimages(time, depends_on=id)

    w.verify_wrf(depends_on=id)
    w.verify_sat(depends_on=id_sat)

if False:  # to continue a free run
    start = dt.datetime(2008, 7, 30, 13, 30)
    end = dt.datetime(2008, 7, 30, 18)

    w.prepare_WRFrundir(start)  
    id = w.run_ideal(depends_on=id)

    # prior_path_exp = w.cluster.archivedir
    # # prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_v1.23_P2_noDA+1'
    # prior_init_time = dt.datetime(2008, 7, 30, 13, 15)
    # prior_valid_time = start

    # id = w.prepare_IC_from_prior(
    #     prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

    # id = w.run_ENS(begin=start, end=end, 
    #                input_is_restart=True,
    #                #output_restart_interval=(end-start).total_seconds()/60,
    #                output_restart_interval=9999,
    #                depends_on=id)
    # id = w.create_satimages(start, depends_on=id)
    # w.verify_sat(id)
    # w.verify_wrf(id)

if False:  # to continue a free run after spinup
    start = dt.datetime(2008, 7, 30, 12)
    end = dt.datetime(2008, 7, 30, 14)

    w.prepare_WRFrundir(start)  # create initial conditions
    # id = w.run_ideal(depends_on=id)

    # w.cluster.archivedir
    prior_path_exp = '/jetfs/home/lkugler/data/sim_archive/exp_v1.19_P2_noDA'
    prior_init_time = dt.datetime(2008, 7, 30, 13)
    prior_valid_time = dt.datetime(2008, 7, 30, 13, 30)

    id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time,
                                 # new_start_time=start, # <---------- to overwrite start time / leads to a call to `create_updated_wrfinput_from_wrfout()`
                                 depends_on=id)

    # frequency_restart = (end-start).total_seconds()/60
    frequency_restart = dt.timedelta(minutes=30).total_seconds()/60

    id = w.run_ENS(begin=start, end=end,
                   input_is_restart=True,
                   output_restart_interval=frequency_restart,
                   # output_restart_interval=9999,
                   depends_on=id)

    # id = w.create_satimages(start, depends_on=id)

    # # continue now with free run
    # # no restart files anymore
    # prior_path_exp = w.cluster.archivedir
    # prior_init_time = start
    # prior_valid_time = end
    # id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

    # start = end
    # end = dt.datetime(2008, 7, 30, 18)
    # print('run WRF from', start, 'until', end)
    # id = w.run_ENS(begin=start, end=end,
    #          input_is_restart=True,
    #          #output_restart_interval=(next_restart-time).total_seconds()/60,
    #          output_restart_interval=9999,
    #          depends_on=id)
    # id = w.create_satimages(start, depends_on=id)
    # w.verify(depends_on=id)
