
import os, sys, shutil
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy_contents, copy
import prepare_namelist

# archive configuration
os.makedirs(cluster.archivedir(), exist_ok=True)
shutil.copy(cluster.scriptsdir+'/config/clusters.py', cluster.archivedir()+'/clusters.py')
shutil.copy(cluster.scriptsdir+'/config/cfg.py', cluster.archivedir()+'/cfg.py')

for iens in range(1, exp.n_ens+1):
    print('preparing ens', iens)
    #input_prof=$USERDIR"/wrf_sounding/data/wrf/ens/from_uwyo/06610_2008073000_uwyo."$(printf "%.3d" $IENS)".wrfprof"
    input_prof=cluster.userdir+"/wrf_sounding/data/wrf/ens/LMU+shear/raso.raso."+str(iens).zfill(3)+".wrfprof"

    rundir = cluster.wrf_rundir(iens)
    os.makedirs(rundir, exist_ok=True)
    copy_contents(cluster.srcdir, rundir)
    print('linking ideal and wrf.exe:')
    symlink(cluster.ideal, rundir+'/ideal.exe')
    symlink(cluster.wrfexe, rundir+'/wrf.exe')

    prepare_namelist.run(cluster, iens, begin=dt.datetime(2008, 7, 30, 6, 0),
                                        end=dt.datetime(2008, 7, 30, 6, 30))

    symlink(input_prof, rundir+'/input_sounding')
print('finished.')
