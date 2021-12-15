import os, sys, shutil
import datetime as dt

from config.cfg import exp, cluster
from utils import symlink, copy, link_contents
import prepare_namelist

if __name__ == '__main__':

    init_time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')

    for iens in range(1, exp.n_ens+1):
        print('preparing ens', iens)
        input_prof = (exp.input_profile).replace('<iens>', str(iens).zfill(3))

        rundir = cluster.wrf_rundir(iens)
        os.makedirs(rundir, exist_ok=True)
        link_contents(cluster.srcdir, rundir)
        print('linking ideal and wrf.exe:')
        symlink(cluster.ideal, rundir+'/ideal.exe')
        symlink(cluster.wrfexe, rundir+'/wrf.exe')

        # time not important, but general settings
        prepare_namelist.run(iens, begin=init_time, end=dt.datetime(2008, 7, 30, 23),
                            archive=False)

        symlink(input_prof, rundir+'/input_sounding')
    print('finished.')
