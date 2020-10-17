import os, sys, shutil
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy, sed_inplace

assim_time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
background_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
exppath_firstguess = str(sys.argv[3])

#if cluster.name != 'srvx8':
#    copy = copy_scp_srvx8  # use scp

print('prepare prior state estimate')
for iens in range(1, exp.n_ens+1):
    #wrfout_run = cluster.wrf_rundir(iens) + time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')

    print('link wrfout file to DART background file')
    wrfout_run = exppath_firstguess+background_init_time.strftime('/%Y-%m-%d_%H:%M/')  \
                 +str(iens)+assim_time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
    dart_ensdir = cluster.dartrundir+'/advance_temp'+str(iens)
    wrfout_dart = dart_ensdir+'/wrfout_d01'

    os.makedirs(dart_ensdir, exist_ok=True)
    print('linking', wrfout_run, 'to', wrfout_dart)
    symlink(wrfout_run, wrfout_dart)
    symlink(wrfout_dart, dart_ensdir+'/wrfinput_d01')

fpath = cluster.dartrundir+'/input_list.txt'
print('writing', fpath)
os.remove(fpath)
with open(fpath, 'w') as f:
    for iens in range(1, exp.n_ens+1):
        f.write('./advance_temp'+str(iens)+'/wrfout_d01')
        f.write('\n')

fpath = cluster.dartrundir+'/output_list.txt'
print('writing', fpath)
os.remove(fpath)
with open(fpath, 'w') as f:
    for iens in range(1, exp.n_ens+1):
        f.write('./filter_restart_d01.'+str(iens).zfill(4))
        f.write('\n')


print('removing preassim and filter_restart')
os.system('rm -rf '+cluster.dartrundir+'/preassim_*')
os.system('rm -rf '+cluster.dartrundir+'/filter_restart*')
os.system('rm -rf '+cluster.dartrundir+'/output_mean*')
os.system('rm -rf '+cluster.dartrundir+'/output_sd*')
os.system('rm -rf '+cluster.dartrundir+'/perfect_output_*')

