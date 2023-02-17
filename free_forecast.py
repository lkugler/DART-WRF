#!/usr/bin/python3
"""
running the forecast model without assimilation
"""
import os, sys, shutil
import datetime as dt
import pandas as pd
from slurmpy import Slurm

from config.cfg import exp
from config.clusters import cluster
from dartwrf.utils import script_to_str, symlink
from cycled_exp import *


################################
print('starting')

cluster.setup()
id = None


if False: #True:  # is_nature
    begin = dt.datetime(2008, 7, 30, 7)
    id = prepare_WRFrundir(begin)  # create initial conditions
    id = run_ideal(depends_on=id)

    #id = wrfinput_insert_wbubble(perturb=False, depends_on=id)
    end = dt.datetime(2008, 7, 30, 12)
    id = run_ENS(begin=begin, end=end,
                     input_is_restart=False,
                     output_restart_interval=(end-begin).total_seconds()/60,
                     depends_on=id)
    # id = create_satimages(begin, depends_on=id)


if False:   # if free run (all inits)
    begin = dt.datetime(2008, 7, 30, 7)
    id = prepare_WRFrundir(begin)  # create initial conditions
    id = run_ideal(depends_on=id)

    #id = wrfinput_insert_wbubble(perturb=True, depends_on=id)

    restarts = pd.date_range(start=dt.datetime(2008, 7, 30, 10),
                              end=dt.datetime(2008, 7, 30, 12),
                              freq=dt.timedelta(minutes=60))
    #restarts = [dt.datetime(2008, 7, 30, 12, 30)]
    
    input_is_restart = False
    time = begin
    last_init = dt.datetime(2008, 7, 30, 9)  # dummy value
    for i, next_restart in enumerate(restarts):
        print('run_WRF from', time, 'to', next_restart)
        id = run_ENS(begin=time, end=next_restart, 
                     input_is_restart=input_is_restart,
                     output_restart_interval=(next_restart-time).total_seconds()/60,
                     #output_restart_interval=720,
                     depends_on=id)

        last_init = time
        time = next_restart
        input_is_restart = True
        create_satimages(last_init, depends_on=id)

        prior_path_exp = cluster.archivedir
        prior_init_time = last_init
        prior_valid_time = time
        id = prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

    # free run, no restart files anymore
    end = dt.datetime(2008, 7, 30, 18)
    print('run WRF from', time, 'until', end)
    id = run_ENS(begin=time, end=end,
             input_is_restart=input_is_restart,
             #output_restart_interval=(next_restart-time).total_seconds()/60,
             output_restart_interval=9999,
             depends_on=id)
    
    
    id = create_satimages(time, depends_on=id)
    verify(depends_on=id)

if False:  # continuation of free run
    start = dt.datetime(2008, 7, 30, 7)
    end = dt.datetime(2008, 7, 30, 10)

    id = prepare_WRFrundir(start)  # create initial conditions

    prior_path_exp = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.19_P5_noDA' # cluster.archivedir
    prior_init_time = dt.datetime(2008, 7, 30, 11)
    prior_valid_time = start

    id = prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

    id = run_ENS(begin=start, end=end,
             input_is_restart=True,
             output_restart_interval=(end-start).total_seconds()/60,
             #output_restart_interval=9999,
             depends_on=id)
        
    id = create_satimages(start, depends_on=id)
    verify(depends_on=id)

if True:  # continuation of free run after spinup
    start = dt.datetime(2008, 7, 30, 13,30)
    end = dt.datetime(2008, 7, 30, 14)

    id = prepare_WRFrundir(start)  # create initial conditions
    # id = run_ideal(depends_on=id)

    prior_path_exp = '/jetfs/home/lkugler/data/sim_archive/exp_v1.19_P2_noDA' # cluster.archivedir
    prior_init_time = dt.datetime(2008, 7, 30, 13)
    prior_valid_time = dt.datetime(2008, 7, 30, 13,30)

    id = prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, 
            # new_start_time=start, # <---------- to overwrite start time
            depends_on=id)

    #frequency_restart = (end-start).total_seconds()/60
    frequency_restart = dt.timedelta(minutes=30).total_seconds()/60

    id = run_ENS(begin=start, end=end,
             input_is_restart=True,
             output_restart_interval=frequency_restart,
             #output_restart_interval=9999,
             depends_on=id)
        
    # id = create_satimages(start, depends_on=id)
    
    # # continue now with free run
    # # no restart files anymore
    # prior_path_exp = cluster.archivedir
    # prior_init_time = start
    # prior_valid_time = end
    # id = prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

    # start = end
    # end = dt.datetime(2008, 7, 30, 18)
    # print('run WRF from', start, 'until', end)
    # id = run_ENS(begin=start, end=end,
    #          input_is_restart=True,
    #          #output_restart_interval=(next_restart-time).total_seconds()/60,
    #          output_restart_interval=9999,
    #          depends_on=id)
    # id = create_satimages(start, depends_on=id)
    # verify(depends_on=id)

if False:  # continuation of nature after spinup

    start = dt.datetime(2008, 7, 30, 7)
    end = dt.datetime(2008, 7, 30, 18)

    id = prepare_WRFrundir(start)  # create initial conditions
    id = run_ideal(depends_on=id)

    prior_path_exp = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.19_P5_nat2' # cluster.archivedir
    prior_init_time = dt.datetime(2008, 7, 30, 7)
    prior_valid_time = dt.datetime(2008, 7, 30, 12)

    id = prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, 
            new_start_time=start, # <---------- to start again after spinup
            depends_on=id)

    id = run_ENS(begin=start, end=end,
             input_is_restart=False,
             output_restart_interval=(end-start).total_seconds()/60,
             #output_restart_interval=9999,
             depends_on=id)
        
    id = create_satimages(start, depends_on=id)
    verify(depends_on=id)
