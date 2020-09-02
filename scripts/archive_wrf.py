import os, sys, warnings, glob
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy, mkdir, mkdir_srvx8, clean_wrfdir

# if cluster.name != 'srvx8':
#     copy = copy_scp_srvx8
#     mkdir = mkdir_srvx8

time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')

print('archive forecasts')
try:
    start = time.strftime('%Y-%m-%d_%H:%M')
    for iens in range(1, exp.n_ens+1):
        savedir = cluster.archivedir()+'/'+start+'/'+str(iens)
        mkdir(savedir)

        wrfout_files = glob.glob(cluster.wrf_rundir(iens)+'/wrfout_d01_*')
        wrfout_files.sort()
        for f in wrfout_files:
            copy(f, savedir+'/'+os.path.basename(f))
            print(savedir+'/'+os.path.basename(f), 'saved.')

except Exception as e:
    warnings.warn(str(e))
