"""Prepare WRF run directories, to use wrf.exe later
Creates a directory where WRF will run (temporary);
Creates softlinks from WRF's `run/` directory;
Links executables set in `cluster.ideal` and `cluster.wrfexe`;
If `exp.input_profile` is set, links the input profiles.

Args:
    init_time (str): Initialization time in format YYYY-MM-DD_HH:MM

Returns:
    None
"""
import os, sys, shutil
import datetime as dt

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster

from dartwrf.utils import symlink, copy, link_contents
from dartwrf import prepare_namelist

if __name__ == '__main__':

    init_time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')

    for iens in range(1, exp.n_ens+1):
        print('preparing ens', iens)

        rundir = cluster.wrf_rundir(iens)
        os.makedirs(rundir, exist_ok=True)
        link_contents(cluster.srcdir, rundir)
        print('linking ideal and wrf.exe:')
        symlink(cluster.ideal, rundir+'/ideal.exe')
        symlink(cluster.wrfexe, rundir+'/wrf.exe')

        # prepare input profiles
        if hasattr(exp, 'input_profile'):
            # prep namelist for ./ideal.exe
            prepare_namelist.run(iens, begin=init_time, end=init_time, archive=False) # time not important
            
            input_prof = (exp.input_profile).replace('<iens>', str(iens).zfill(3))
            symlink(input_prof, rundir+'/input_sounding')

    print('finished.')
