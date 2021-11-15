#!/usr/bin/python3
"""
running the forecast model without assimilation
"""
import os, sys, shutil
import datetime as dt
import pandas as pd
from slurmpy import Slurm

from config.cfg import exp, cluster
from scripts.utils import script_to_str, symlink

log_dir = cluster.archivedir+'/logs/'
slurm_scripts_dir = cluster.archivedir+'/slurm-scripts/'
print('logging to', log_dir)
print('scripts, which are submitted to SLURM:', slurm_scripts_dir)

from scheduler import *

################################
print('starting osse')

backup_scripts()
id = None

is_nature = True

begin = dt.datetime(2008, 7, 30, 9)
id = prepare_WRFrundir(begin)  # create initial conditions
id = run_ideal(depends_on=id)

if is_nature:
    id = wrfinput_insert_wbubble(perturb=False, depends_on=id)
    end = dt.datetime(2008, 7, 30, 16)
    id = run_ENS(begin=begin, end=end,
                     first_minute=False,
                     input_is_restart=False,
                     output_restart_interval=(end-begin).total_seconds()/60,
                     depends_on=id)
    id = create_satimages(begin, depends_on=id)
else:
    id = wrfinput_insert_wbubble(perturb=True, depends_on=id)

    restarts = pd.date_range(start=dt.datetime(2008, 7, 30, 10),
                             end=dt.datetime(2008, 7, 30, 12),
                             freq=dt.timedelta(minutes=60))
    
    input_is_restart = True
    time = begin
    for next_restart in restarts:
         
        id = run_ENS(begin=time, end=next_restart, 
                     first_minute=False,
                     input_is_restart=input_is_restart,
                     restart_path=cluster.archivedir+time.strftime('/%Y-%m-%d_%H:%M/'),
                     output_restart_interval=(next_restart-time).total_seconds()/60,
                     output_restart_interval=720,
                     depends_on=id)

        time = next_restart
        input_is_restart = True
    
    
    #id = create_satimages(begin, depends_on=id)
    verify(depends_on=id)
