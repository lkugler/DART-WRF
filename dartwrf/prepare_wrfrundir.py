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
from dartwrf.server_config import cluster

from dartwrf.utils import symlink, link_contents, try_remove, read_dict_from_pyfile
from dartwrf import prepare_namelist

if __name__ == '__main__':
    
    time = sys.argv[1]
    exp = read_dict_from_pyfile(sys.argv[2])
    

    for iens in range(1, exp.ensemble_size+1):
        rundir = cluster.wrf_rundir(iens)
        os.makedirs(rundir, exist_ok=True)
        link_contents(cluster.srcdir, rundir)
        symlink(cluster.wrfexe, rundir+'/wrf.exe')
        
        if hasattr(cluster, 'ideal'):
            symlink(cluster.ideal, rundir+'/ideal.exe')

        # prepare input profiles
        try_remove(rundir+'/input_sounding')   # remove existing file
        
        if hasattr(exp, 'input_profile'):
            init_time = dt.datetime.strptime(time, '%Y-%m-%d_%H:%M')
            # prep namelist for ./ideal.exe
            prepare_namelist.run(iens, begin=init_time, end=init_time, archive=False) # time not important
            
            input_prof = (exp.input_profile).replace('<iens>', str(iens).zfill(3))
            if not os.path.isfile(input_prof):
                raise FileNotFoundError(f'Input profile {input_prof} does not exist.')
            symlink(input_prof, rundir+'/input_sounding')

    print('All run_WRF directories have been set up.')
