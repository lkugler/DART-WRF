#!/usr/bin/python3
"""
high level control script
submitting jobs into SLURM queue
"""
import os, sys, shutil
import datetime as dt
from slurmpy import Slurm

from config.cfg import exp, cluster
from scripts.utils import script_to_str, symlink

# necessary to find modules in folder, since SLURM runs the script elsewhere
sys.path.append(os.getcwd())

# allow scripts to access the configuration
# symlink(cluster.scriptsdir+'/../config', cluster.scriptsdir+'/config')

log_dir = cluster.archivedir+'/logs/'
slurm_scripts_dir = cluster.archivedir+'/slurm-scripts/'
print('logging to', log_dir)
print('scripts, which are submitted to SLURM:', slurm_scripts_dir)

from scheduler import *

################################
print('starting osse')

backup_scripts()
id = None

init_time = dt.datetime(2008, 7, 30, 6)
id = prepare_wrfinput(init_time)  # create initial conditions

if False:
    init_time = dt.datetime(2008, 7, 30, 8)
    # get initial conditions from archive
    integration_end_time = dt.datetime(2008, 7, 30, 9)
    exppath_arch = cluster.archivedir #'/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.16_P1_40mem'
    id = update_wrfinput_from_archive(integration_end_time, init_time, exppath_arch, depends_on=id)
    
    #id = wrfinput_insert_wbubble(depends_on=id)
    

begin = dt.datetime(2008, 7, 30, 6)
end = dt.datetime(2008, 7, 31, 0)


id = run_ENS(begin=begin, end=end, first_minute=False, depends_on=id)
create_satimages(begin, depends_on=id)
