#!/usr/bin/python3
"""
running the forecast model without assimilation
"""
import os, sys, shutil
import datetime as dt
import pandas as pd
from slurmpy import Slurm

from config.cfg import exp, cluster
from dartwrf.utils import script_to_str, symlink

log_dir = cluster.archivedir+'/logs/'
slurm_scripts_dir = cluster.archivedir+'/slurm-scripts/'
print('logging to', log_dir)
print('scripts, which are submitted to SLURM:', slurm_scripts_dir)

from scheduler import *

################################
print('starting osse')

backup_scripts()
id = None

is_nature = False

begin = dt.datetime(2008, 7, 30, 12)
id = prepare_WRFrundir(begin)  # create initial conditions
id = run_ideal(depends_on=id)

if is_nature:
    #id = wrfinput_insert_wbubble(perturb=False, depends_on=id)
    end = dt.datetime(2008, 7, 30, 14)
    id = run_ENS(begin=begin, end=end,
                     input_is_restart=False,
                     output_restart_interval=(end-begin).total_seconds()/60,
                     depends_on=id)
    #id = create_satimages(begin, depends_on=id)
else:
    #id = wrfinput_insert_wbubble(perturb=True, depends_on=id)

    restarts = pd.date_range(start=dt.datetime(2008, 7, 30, 12,30),
                             end=dt.datetime(2008, 7, 30, 13),
                             freq=dt.timedelta(minutes=30))
    #restarts = [dt.datetime(2008, 7, 30, 11)]
    
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
        #create_satimages(last_init, depends_on=id)

        prior_path_exp = cluster.archivedir
        prior_init_time = last_init
        prior_valid_time = time
        id = prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

    #sys.exit()

    # free run, no restart files anymore
    end = dt.datetime(2008, 7, 30, 14)
    print('run WRF from', time, 'until', end)
    id = run_ENS(begin=time, end=end,
             input_is_restart=input_is_restart,
             #output_restart_interval=(next_restart-time).total_seconds()/60,
             output_restart_interval=9999,
             depends_on=id)
    
    
    #id = create_satimages(time, depends_on=id)
    verify(depends_on=id)
