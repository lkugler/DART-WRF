import os, sys, glob
import datetime as dt
from dartwrf.utils import copy, Config

"""
Sets initial condition data (wrfinput/wrfrst file) in the run_WRF directory for each ensemble member 

You have 2 options to restart:
1) using wrfout files  (function create_wrfinput_from_wrfout)
2) using wrfrst files  (function create_wrfrst_in_WRF_rundir)

Ad 1: copy wrfout from prior to archivedir

Ad 2: copies wrfrst to run_WRF directory

"""

def create_wrfrst_in_WRF_rundir(time: dt.datetime, prior_init_time: dt.datetime, prior_path_exp: str) -> None:
    """Copy WRF restart files to run_WRF directory 
    These files will be used as initial conditions for the next WRF run
    """
    for iens in range(1, cfg.ensemble_size+1):
        dir_wrf_run = cfg.dir_wrf_run.replace('<exp>', cfg.name).replace('<ens>', str(iens))
        
        for f in glob.glob(dir_wrf_run+'/wrfrst_*'):
            os.remove(f)
    
        prior_wrfrst = prior_path_exp + prior_init_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+time.strftime('/wrfrst_d01_%Y-%m-%d_%H:%M:%S')
        wrfrst = dir_wrf_run + time.strftime('/wrfrst_d01_%Y-%m-%d_%H:%M:%S')
        print('copy prior (wrfrst)', prior_wrfrst, 'to', wrfrst)
        copy(prior_wrfrst, wrfrst)
        

def create_updated_wrfinput_from_wrfout(time: dt.datetime, prior_init_time: dt.datetime, prior_path_exp: str, new_start_time: dt.datetime) -> None:
    """Create a new wrfinput file from wrfout file
    Output is created inside the WRF run directory
    
    Args:
        time: time of the wrfout file
        prior_init_time: initial time of the prior run
        prior_path_exp: path to the prior run
        new_start_time: time of the new wrfinput file
                        If provided, overwrites the valid time of the initial conditions; 
                        This hack allows you to use a prior of a different time than your forecast start time.
                        Usually, you don't want to do this.
    
    """
    print('writing updated wrfout to WRF run directory as wrfinput')
    for iens in range(1, cfg.ensemble_size+1):
        dir_wrf_run = cfg.dir_wrf_run.replace('<exp>', cfg.name).replace('<ens>', str(iens))
        
        prior_wrfout = prior_path_exp + prior_init_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        new_start_wrfinput = dir_wrf_run + '/wrfinput_d01' 
        copy(prior_wrfout, new_start_wrfinput)
        print(new_start_wrfinput, 'created.')

        template_time = prior_path_exp + new_start_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+new_start_time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        os.system('ncks -A -v XTIME,Times '+template_time+' '+new_start_wrfinput)
        print('overwritten times from', template_time)


if __name__ == '__main__':
    cfg = Config.from_file(sys.argv[1])
    
    prior_valid_time = cfg.prior_valid_time
    prior_init_time = cfg.prior_init_time
    prior_path_exp = cfg.prior_path_exp
    
    if 'start_from_wrfout' in cfg:
        if cfg.start_from_wrfout:
            # use_wrfout_as_wrfinput
            # Caution: Even without assimilation increments, this will change the model forecast
            new_start_time = cfg.new_start_time
            create_updated_wrfinput_from_wrfout(prior_valid_time, prior_init_time, prior_path_exp, new_start_time)
            sys.exit(0)

    # other case:
    create_wrfrst_in_WRF_rundir(prior_valid_time, prior_init_time, prior_path_exp)
