import os, sys, warnings
import datetime as dt
import netCDF4 as nc

from config.cfg import exp, cluster
"""
Updates initial condition (wrfinput/wrfrst files) in the run_WRF directories with ./filter output

# assumes T = THM (dry potential temperature as prognostic variable)
"""

def update_initials_in_WRF_rundir(time):
    """Updates wrfrst-files in `/run_WRF/` directory 
    with posterior state from ./filter output, e.g. filter_restart_d01.0001

    Args:
        time (dt.datetime):     time of assimilation (directory preceeding ./assim_stage0/...)
    """
    use_wrfrst = True  # if wrfrst is used to restart (recommended)
    if use_wrfrst:
        initials_fmt = '/wrfrst_d01_%Y-%m-%d_%H:%M:%S'
    else:
        initials_fmt = '/wrfinput_d01' 

    # which WRF variables will be updated?
    update_vars = ['Times',]
    update_vars.extend(exp.update_vars)

    for iens in range(1, exp.n_ens+1):
        ic_file = cluster.wrf_rundir(iens) + time.strftime(initials_fmt)
        if not os.path.isfile(ic_file):
            raise IOError(ic_file+' does not exist, updating impossible!')
        else:
            # overwrite DA updated variables
            filter_out = cluster.archivedir+time.strftime('/%Y-%m-%d_%H:%M/assim_stage0/filter_restart_d01.'+str(iens).zfill(4))

            with nc.Dataset(filter_out, 'r') as ds_filter:
                with nc.Dataset(ic_file, 'r+') as ds_new:

                    # assumes T = THM (dry potential temperature as prognostic variable)
                    if use_wrfrst:
                        ds_new.variables['THM_2'][:] = ds_filter.variables['T'][:]
                    else:
                        ds_new.variables['THM'][:] = ds_filter.variables['T'][:]

                    # update all other variables
                    for var in update_vars:
                        if var in ds_new.variables:
                            var_new = var
                        else:
                            var_new = var+'_2'  # e.g. U_2, W_2, THM_2
                        
                        ds_new.variables[var_new][:] = ds_filter.variables[var][:]

                print(ic_file, 'created, updated from', filter_out)


if __name__ == '__main__':
    time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    update_initials_in_WRF_rundir(time)
