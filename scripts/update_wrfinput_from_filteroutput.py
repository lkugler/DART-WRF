import os, sys, warnings
import datetime as dt
import netCDF4 as nc

from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy, mkdir, mkdir_srvx8, clean_wrfdir

time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
background_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
exppath_firstguess = str(sys.argv[3])

#if cluster.name != 'srvx8':
#    copy = copy_scp_srvx8
#    mkdir = mkdir_srvx8
cycle_vars = ['U', 'V', 'P', 'PH', 'T', 'MU', 'QVAPOR', 'QCLOUD', 'QRAIN', 'QICE', 'QSNOW',
              'QGRAUP', 'QNICE', 'QNRAIN', 'U10', 'V10', 'T2', 'Q2', 'PSFC', 'TSLB',
              'SMOIS', 'TSK']

update_vars = ['Times', 'U', 'V', 'T', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'PSFC', 'TSK']

# variables which are updated need not to be cycled
for var in update_vars:
    if var in cycle_vars:
        cycle_vars.remove(var)

cycles = ','.join(cycle_vars)
updates = ','.join(update_vars)

print('move output to WRF dir as new initial conditions')
for iens in range(1, exp.n_ens+1):
    clean_wrfdir(cluster.wrf_rundir(iens))
    prior_wrf = exppath_firstguess + background_init_time.strftime('/%Y-%m-%d_%H:%M/') \
              +str(iens)+time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
    filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
    wrf_ic = cluster.wrf_rundir(iens) + '/wrfinput_d01'

    # cycles variables from wrfout (prior state)
    print('cycling', cycles, 'into', wrf_ic, 'from', prior_wrf)
    os.system(cluster.ncks+' -A -v '+cycles+' '+prior_wrf+' '+wrf_ic)

    print('updating', updates, 'in', wrf_ic, 'from', filter_out)
    os.system(cluster.ncks+' -A -v '+updates+' '+filter_out+' '+wrf_ic)

    print('writing T into THM of wrfinput')
    thm_in = nc.Dataset(filter_out, 'r').variables['T'][:]
    dsout = nc.Dataset(wrf_ic, 'r+')
    dsout.variables['THM'][:] = thm_in
    dsout.close()

    # clean up
    #try:
    #    os.remove(cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01')
    #except:
    #    pass
