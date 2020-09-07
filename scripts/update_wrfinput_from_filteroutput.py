import os, sys, warnings
import datetime as dt

from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy, mkdir, mkdir_srvx8, clean_wrfdir

time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')

#if cluster.name != 'srvx8':
#    copy = copy_scp_srvx8
#    mkdir = mkdir_srvx8

update_vars = ['Times', 'U', 'V', 'PH', 'T', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'PSFC', 'TSK']

print('move output to WRF dir as new initial conditions')
for iens in range(1, exp.n_ens+1):
    clean_wrfdir(cluster.wrf_rundir(iens))
    filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
    wrf_ic = cluster.wrf_rundir(iens) + '/wrfinput_d01'

    # overwrite variables in wrfinput file
    vars = ','.join(update_vars)
    print('updating', vars, 'in', wrf_ic)
    os.system(cluster.ncks+' -A -v '+vars+' '+filter_out+' '+wrf_ic)

    # clean up
    #try:
    #    os.remove(cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01')
    #except:
    #    pass
