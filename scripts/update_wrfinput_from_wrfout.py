import os, sys, shutil
import datetime as dt

from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy
import prepare_namelist

exppath = str(sys.argv[1])
# time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
# background_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')

update_vars = ['Times', 'U', 'V', 'PH', 'T', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'PSFC', 'TSK']
vars = ','.join(update_vars)

for iens in range(1, exp.n_ens+1):
    print('update state in wrfinput  wrfout file to DART background file')
    wrfout = exppath.replace('*iens*', str(iens))
    wrfin = cluster.wrf_rundir(iens)+'/wrfinput_d01'

    print('updating', wrfin, 'to state in', wrfout)
    assert os.path.isfile(wrfout)

    # overwrite variables in wrfinput file
    os.system(cluster.ncks+' -A -v '+vars+' '+wrfout+' '+wrfin)
