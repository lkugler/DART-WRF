print('loading modules')
import os, sys, warnings, glob
import datetime as dt
import netCDF4 as nc

from config.cfg import exp, cluster
from utils import symlink, copy, mkdir, clean_wrfdir, try_remove

"""
Sets initial condition data (wrfinput/wrrst file) in the run_WRF directory for each ensemble member 
 1) copies wrfrst to run_WRF directory
 2) overwrites DA-updated variables with DART output fields

 (for verification later on, since a restart run does not write the first wrfout) 
 3) copy wrfout from prior to archivedir
 4) overwrite DA-updated variables with DART output

# assumes T = THM (dry potential temperature as prognostic variable)
"""
update_vars = ['Times',]
update_vars.extend(exp.update_vars) # 'U', 'V', 'T', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'TSK', 'CLDFRA']
updates = ','.join(update_vars)

def create_wrfrst_in_WRF_rundir(time, prior_init_time, exppath_firstguess):
    """copies wrfrst to run_WRF directory (for next WRF run)
    """
    for iens in range(1, exp.n_ens+1):
        clean_wrfdir(cluster.wrf_rundir(iens))
    
        prior_wrfrst = exppath_firstguess + prior_init_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+time.strftime('/wrfrst_d01_%Y-%m-%d_%H:%M:%S')
        wrfrst = cluster.wrf_rundir(iens) + time.strftime('/wrfrst_d01_%Y-%m-%d_%H:%M:%S')
        print('copy prior (wrfrst)', prior_wrfrst, 'to', wrfrst)
        copy(prior_wrfrst, wrfrst)
    
        filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
        print('update assimilated variables => overwrite', updates, 'in', wrfrst, 'from', filter_out) 
        os.system(cluster.ncks+' -A -v '+updates+' '+filter_out+' '+wrfrst)
    
        print('writing T into THM of wrfrst')  # assumes T = THM (dry potential temperature as prognostic variable)
        with nc.Dataset(filter_out, 'r') as ds_filter:
            with nc.Dataset(wrfrst, 'r+') as ds_wrfrst:
                ds_wrfrst.variables['THM_1'][:] = ds_filter.variables['T'][:]
                ds_wrfrst.variables['THM_2'][:] = ds_filter.variables['T'][:]
        print(wrfrst, 'created.')
        
        # remove all wrfrst (but not the one used)
        files_rst = glob.glob(exppath_firstguess + prior_init_time.strftime('/%Y-%m-%d_%H:%M/'+str(iens)+'/wrfrst_*'))
        files_rst.remove(prior_wrfrst)
        for f in files_rst:
            try_remove(f)

def create_wrfout_in_archivedir(time, prior_init_time, exppath_firstguess):
    """Put updated wrfout in archive dir (because wrf restart writes no 0 minute wrfout)
    """
    print('writing updated wrfout to archive (for verification)')
    for iens in range(1, exp.n_ens+1):
        prior_wrfout = exppath_firstguess + prior_init_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        post_wrfout_archive = cluster.archivedir +time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        # copy template wrfout (including cycled variables)
        os.makedirs(os.path.dirname(post_wrfout_archive), exist_ok=True)
        copy(prior_wrfout, post_wrfout_archive) 

        # overwrite DA updated variables
        filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
        #filter_out = cluster.archivedir +time.strftime('/%Y-%m-%d_%H:%M/assim_stage0/filter_restart_d01.'+str(iens).zfill(4))
        os.system(cluster.ncks+' -A -v '+updates+' '+filter_out+' '+post_wrfout_archive)
        
        # need to overwrite THM manually
        with nc.Dataset(filter_out, 'r') as ds_filter:
            with nc.Dataset(post_wrfout_archive, 'r+') as ds_wrfout:
                ds_wrfout.variables['THM'][:] = ds_filter.variables['T'][:]
        print(post_wrfout_archive, 'created.')


def create_updated_wrfinput_from_wrfout(time, prior_init_time, exppath_firstguess):
    """Same as create_wrfout_in_archivedir, but output is `wrfinput` in WRF run directory"""

    print('writing updated wrfout to WRF run directory as wrfinput')
    for iens in range(1, exp.n_ens+1):
        prior_wrfout = exppath_firstguess + prior_init_time.strftime('/%Y-%m-%d_%H:%M/') \
                       +str(iens)+time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        post_wrfout = cluster.wrf_rundir(iens) + '/wrfinput_d01' 
        copy(prior_wrfout, post_wrfout)

        if True: # overwrite DA updated variables
            filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
            os.system(cluster.ncks+' -A -v '+updates+' '+filter_out+' '+post_wrfout)

            # need to overwrite THM manually
            with nc.Dataset(filter_out, 'r') as ds_filter:
                with nc.Dataset(post_wrfout, 'r+') as ds_wrfout:
                    ds_wrfout.variables['THM'][:] = ds_filter.variables['T'][:]
        print(post_wrfout, 'created.')


if __name__ == '__main__':
    time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    prior_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
    exppath_firstguess = str(sys.argv[3])


    use_wrfout_as_wrfinput = False
    if use_wrfout_as_wrfinput:
        create_updated_wrfinput_from_wrfout(time, prior_init_time, exppath_firstguess)
    else:
        create_wrfrst_in_WRF_rundir(time, prior_init_time, exppath_firstguess)

        # this is done with the right WRF namelist entry (write first wrfout)
        #create_wrfout_in_archivedir(time, prior_init_time, exppath_firstguess)


