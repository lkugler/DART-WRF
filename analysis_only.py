#!/usr/bin/python3
"""
running the forecast model without assimilation
"""
import os, sys, shutil
import datetime as dt

from dartwrf import utils
from config.cfg import exp
from config.clusters import cluster

log_dir = cluster.archivedir+'/logs/'
slurm_scripts_dir = cluster.archivedir+'/slurm-scripts/'
print('logging to', log_dir)
print('scripts, which are submitted to SLURM:', slurm_scripts_dir)


###############################
utils.backup_scripts()


prior_path_exp = '/mnt/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P3_wbub7_noDA'
prior_init_time = dt.datetime(2008,7,30,12)
prior_valid_time = dt.datetime(2008,7,30,12,30)
assim_time = prior_valid_time


os.system(
    cluster.python+' '+cluster.scripts_rundir+'/assim_synth_obs.py '
                +assim_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_init_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_path_exp
    )



# id_sat = create_satimages(time, depends_on=id)