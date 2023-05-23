import os, sys, warnings, glob
import datetime as dt
import numpy as np

from exp_config import exp
from server_config import cluster
from dartwrf.utils import copy, clean_wrfdir, try_remove

"""
Sets initial condition data (wrfinput/wrfrst file) in the run_WRF directory for each ensemble member 

You have 2 options to restart:
1) using wrfout files  (function create_wrfinput_from_wrfout)
2) using wrfrst files  (function create_wrfrst_in_WRF_rundir)

Ad 1: copy wrfout from prior to archivedir

Ad 2: copies wrfrst to run_WRF directory

"""

def create_wrfrst_in_WRF_rundir(time, prior_init_time, prior_path_exp):
    """copies wrfrst to run_WRF directory (for next WRF run)
    """
    # for documentation: Which prior was used? -> write into txt file
    os.makedirs(cluster.archivedir + time.strftime('/%Y-%m-%d_%H:%M/'), exist_ok=True)
    os.system('echo "'+prior_path_exp+'\n'+prior_init_time.strftime('/%Y-%m-%d_%H:%M/')
                +'\n'+time.strftime('/wrfrst_d01_%Y-%m-%d_%H:%M:%S')+'" > '
                +cluster.archivedir + time.strftime('/%Y-%m-%d_%H:%M/')+'link_to_prior.txt')

    for iens in range(1, exp.n_ens+1):
        clean_wrfdir(cluster.wrf_rundir(iens))
    
        prior_wrfrst = prior_path_exp + prior_init_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+time.strftime('/wrfrst_d01_%Y-%m-%d_%H:%M:%S')
        wrfrst = cluster.wrf_rundir(iens) + time.strftime('/wrfrst_d01_%Y-%m-%d_%H:%M:%S')
        print('copy prior (wrfrst)', prior_wrfrst, 'to', wrfrst)
        copy(prior_wrfrst, wrfrst)
        
        # remove all wrfrst (but not the one used) - WHY? NO!
        # files_rst = glob.glob(prior_path_exp + prior_init_time.strftime('/%Y-%m-%d_%H:%M/'+str(iens)+'/wrfrst_*'))
        # files_rst.remove(prior_wrfrst)
        # for f in files_rst:
        #     print('removing', f)
        #     try_remove(f)

def create_updated_wrfinput_from_wrfout(time, prior_init_time, prior_path_exp, new_start_time):
    """Same as create_wrfout_in_archivedir, but output is `wrfinput` in WRF run directory"""

    print('writing updated wrfout to WRF run directory as wrfinput')
    for iens in range(1, exp.n_ens+1):
        prior_wrfout = prior_path_exp + prior_init_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        new_start_wrfinput = cluster.wrf_rundir(iens) + '/wrfinput_d01' 
        copy(prior_wrfout, new_start_wrfinput)
        print(new_start_wrfinput, 'created.')

        template_time = prior_path_exp + new_start_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+new_start_time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        os.system('ncks -A -v XTIME,Times '+template_time+' '+new_start_wrfinput)
        print('overwritten times from', template_time)


if __name__ == '__main__':
    prior_path_exp = sys.argv[1]
    prior_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
    prior_valid_time = dt.datetime.strptime(sys.argv[3], '%Y-%m-%d_%H:%M')

    if len(sys.argv) == 5:
        # to start new simulation at different time than prior_valid_time
        new_start_time = dt.datetime.strptime(sys.argv[4], '%Y-%m-%d_%H:%M')

        # use_wrfout_as_wrfinput
        create_updated_wrfinput_from_wrfout(prior_valid_time, prior_init_time, prior_path_exp, new_start_time)
    else:
        # restart 
        create_wrfrst_in_WRF_rundir(prior_valid_time, prior_init_time, prior_path_exp)
