print('loading modules')
import os, sys, warnings
import datetime as dt
import netCDF4 as nc

from config.cfg import exp, cluster
from utils import symlink, copy, mkdir, clean_wrfdir

time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
background_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
exppath_firstguess = str(sys.argv[3])

"""
-) sets initial condition data (wrfinput file) in the run_WRF directory for each ensemble member 
   from a DART output state (set of filter_restart files)
-) cycles (copies) some state variables from the prior ensemble to the wrfinput of the next run

# assumes T = THM (dry potential temperature as prognostic variable)
"""
update_vars = ['Times',]
update_vars.extend(exp.update_vars) # 'U', 'V', 'T', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'TSK', 'CLDFRA']
updates = ','.join(update_vars)

print('move output to WRF dir as new initial conditions')
for iens in range(1, exp.n_ens+1):
    clean_wrfdir(cluster.wrf_rundir(iens))
    prior_wrf = exppath_firstguess + background_init_time.strftime('/%Y-%m-%d_%H:%M/') \
              +str(iens)+time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
    filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
    wrf_ic = cluster.wrf_rundir(iens) + '/wrfinput_d01'

    # cycles variables from wrfout (prior state)
    print('cycle some variables (copy from last init) => copy prior', prior_wrf, 'to wrfinput', wrf_ic)
    # os.system(cluster.ncks+' -A -v '+cycles+' '+prior_wrf+' '+wrf_ic)
    copy(prior_wrf, wrf_ic)

    print('update assimilated variables => overwrite', updates, 'in', wrf_ic, 'from', filter_out)
    os.system(cluster.ncks+' -A -v '+updates+' '+filter_out+' '+wrf_ic)

    print('writing T into THM of wrfinput')  # assumes T = THM (dry potential temperature as prognostic variable)
    thm_in = nc.Dataset(filter_out, 'r').variables['T'][:]
    dsout = nc.Dataset(wrf_ic, 'r+')
    dsout.variables['THM'][:] = thm_in
    dsout.close()

    # clean up
    #try:
    #    os.remove(cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01')
    #except:
    #    pass
