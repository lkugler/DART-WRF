import os, sys, warnings
import datetime as dt
import netCDF4 as nc

from config.cfg import exp, cluster
"""
Updates initial condition (wrfinput/wrfrst files) in the run_WRF directories with ./filter output

# assumes T = THM (dry potential temperature as prognostic variable)
"""

use_wrfrst = True  # recommended to be True
if use_wrfrst:
    initials_fmt = '/wrfrst_d01_%Y-%m-%d_%H:%M:%S'
else:
    initials_fmt = '/wrfinput_d01' 


def update_initials_in_WRF_rundir(time):
    """updates wrfrst in run_WRF directory with posterior state from ./filter

    Args:
        time (dt.datetime):     time of assimilation (directory preceeding ./assim_stage0/...)
    """

    # which WRF variables will be updated?
    update_vars = ['Times',]
    update_vars.extend(exp.update_vars)
    updates = ','.join(update_vars)

    for iens in range(1, exp.n_ens+1):
        ic_file = cluster.wrf_rundir(iens) + time.strftime(initials_fmt)
        if not os.path.isfile(ic_file):
            raise IOError(ic_file+' does not exist, updating impossible!')
        else:
            # overwrite DA updated variables
            filter_out = cluster.archivedir+time.strftime('/%Y-%m-%d_%H:%M/assim_stage0/filter_restart_d01.'+str(iens).zfill(4))
            print('update assimilated variables => overwrite', updates, 'from', filter_out) 
            os.system(cluster.ncks+' -A -v '+updates+' '+filter_out+' '+ic_file)
        
            # assumes T = THM (dry potential temperature as prognostic variable)
            print('writing T into THM')  
            with nc.Dataset(filter_out, 'r') as ds_filter:

                if use_wrfrst:
                    with nc.Dataset(ic_file, 'r+') as ds_wrfrst:
                        ds_wrfrst.variables['THM_1'][:] = ds_filter.variables['T'][:]
                        ds_wrfrst.variables['THM_2'][:] = ds_filter.variables['T'][:]
                else:
                    with nc.Dataset(ic_file, 'r+') as ds_wrfout:
                        ds_wrfout.variables['THM'][:] = ds_filter.variables['T'][:]

            print(ic_file, 'updated.')


if __name__ == '__main__':
    time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    update_initials_in_WRF_rundir(time)
