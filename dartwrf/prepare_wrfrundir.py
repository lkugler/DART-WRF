"""Prepare WRF run directories, to use wrf.exe later
Creates a directory where WRF will run (temporary);
Creates softlinks from WRF's `run/` directory;
Links executables set in `cfg.ideal` and `cfg.wrfexe`;
If `exp.input_profile` is set, links the input profiles.

Args:
    init_time (str): Initialization time in format YYYY-MM-DD_HH:MM

Returns:
    None
"""
import os, sys, shutil
import datetime as dt

from dartwrf.utils import Config, symlink, link_contents, try_remove
from dartwrf import prepare_namelist

def run(cfg: Config):
    """Prepare WRF run directories, to use ideal.exe or wrf.exe later
    """
    for iens in range(1, cfg.ensemble_size+1):
        rundir = cfg.dir_wrf_run.replace('<exp>', cfg.name).replace('<ens>', str(iens))
        os.makedirs(rundir, exist_ok=True)
        
        link_contents(cfg.dir_wrf_src, rundir)
        symlink(cfg.wrfexe, rundir+'/wrf.exe')
        
        if hasattr(cfg, 'idealexe'):
            symlink(cfg.idealexe, rundir+'/ideal.exe')
        
        if hasattr(cfg, 'input_profile'):
            input_prof = cfg.input_profile.replace('<iens>', str(iens).zfill(3))
            
            if not os.path.isfile(input_prof):
                raise FileNotFoundError(f'Input profile {input_prof} does not exist.')
            symlink(input_prof, rundir+'/input_sounding')

    prepare_namelist.run(cfg)
    print('All run_WRF directories have been set up.')

if __name__ == '__main__':
    
    cfg = Config.from_file(sys.argv[1])
    run(cfg)
    


