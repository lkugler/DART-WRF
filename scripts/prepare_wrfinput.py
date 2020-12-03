import os, sys, shutil
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy, link_contents

import prepare_namelist

for iens in range(1, exp.n_ens+1):
    print('preparing ens', iens)
    input_prof = (cluster.input_profile).replace('<iens>', str(iens).zfill(3))

    rundir = cluster.wrf_rundir(iens)
    os.makedirs(rundir, exist_ok=True)
    link_contents(cluster.srcdir, rundir)
    print('linking ideal and wrf.exe:')
    symlink(cluster.ideal, rundir+'/ideal.exe')
    symlink(cluster.wrfexe, rundir+'/wrf.exe')

    prepare_namelist.run(iens, begin=dt.datetime(2008, 7, 30, 6, 0),
                         end=dt.datetime(2008, 7, 30, 6, 30)) # not necessary

    symlink(input_prof, rundir+'/input_sounding')
print('finished.')
