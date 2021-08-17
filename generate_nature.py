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

init_time = dt.datetime(2008, 7, 30, 9)
id = prepare_wrfinput(init_time)  # create initial conditions

# get initial conditions from archive
integration_end_time = dt.datetime(2008, 7, 30, 12)
#exppath_arch = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.16_P1_40mem'
#id = update_wrfinput_from_archive(integration_end_time, init_time, exppath_arch, depends_on=id)

id = wrfinput_insert_wbubble(depends_on=id)


begin = dt.datetime(2008, 7, 30, 9, 0)
end = dt.datetime(2008, 7, 30, 12, 0)

# whole forecast timespan
hist_interval = 5
radt = 5
s = my_Slurm("namelist", cfg_update=dict(time="2"))
id = s.run(' '.join([cluster.python,
            cluster.scriptsdir+'/prepare_namelist.py',
            begin.strftime('%Y-%m-%d_%H:%M'),
            end.strftime('%Y-%m-%d_%H:%M'),
            str(hist_interval), str(radt),]), 
        depends_on=[id])

s = my_Slurm("EnsWRF", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
             "mem-per-cpu": "2G", "mail-type": "BEGIN,FAIL,END"})
cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
id = s.run(cmd, depends_on=[id])
