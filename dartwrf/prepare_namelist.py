"""Create namelist.input files

Usage:
prepare_namelist.py <config>
"""
import os, sys
import datetime as dt
from dartwrf.namelist_handler import WRF_namelist
from dartwrf.utils import Config, copy, try_remove

def run(cfg: Config) -> None:
    """Prepare WRF namelist files.
    
    Note:
        Important parameters are:
        restart, restart_interval, hist_interval_s, WRF_start, WRF_end, WRF_namelist_template
    """
    # defaults
    hist_interval_s = 300
    restart_interval = 9999  # dummy
    
    # overwrite with config
    restart = True
    if 'restart' in cfg:
        restart = cfg.restart

    if 'WRF_start' in cfg:
        start = cfg.WRF_start
        if 'WRF_end' in cfg:
            end = cfg.WRF_end
    else:  
        start = cfg.time  # dummy time for ideal.exe
        end = start
        
    if 'restart_interval' in cfg:
        restart_interval = cfg.restart_interval
        
    if 'hist_interval_s' in cfg:
        hist_interval_s = cfg.hist_interval_s

    # replace these variables in the namelist
    rst_flag = '.true.' if restart else '.false.'
        
    replace_dict = {
        'time_control': {
            'start_year': start.strftime('%Y'),
            'start_month': start.strftime('%m'),
            'start_day': start.strftime('%d'),
            'start_hour': start.strftime('%H'),
            'start_minute': start.strftime('%M'),
            'start_second': start.strftime('%S'),
            'end_year': end.strftime('%Y'),
            'end_month': end.strftime('%m'),
            'end_day': end.strftime('%d'),
            'end_hour': end.strftime('%H'),
            'end_minute': end.strftime('%M'),
            'end_second': end.strftime('%S'),
            'history_interval_s': str(int(hist_interval_s)),
            'restart_interval': str(int(restart_interval)),
            'restart': rst_flag,
            },
        'domains': {
            'dx': str(cfg.model_dx),
        }}
        
    print('prepare namelists from', start, 'to', end, 
          ', restart=', restart, 'restart_interval=', restart_interval)
    for iens in range(1, cfg.ensemble_size+1):

        replace_dict['time_control'].update({
            'history_outname': "'"+cfg.dir_archive+'/'+start.strftime('%Y-%m-%d_%H:%M')+"/"+str(iens)+"/wrfout_d<domain>_<date>'",
            'rst_outname': "'"+cfg.dir_archive+'/'+start.strftime('%Y-%m-%d_%H:%M')+"/"+str(iens)+"/wrfrst_d<domain>_<date>'",
            })
        
        # define defaults from Config
        nml = WRF_namelist()
        nml.read(cfg.WRF_namelist_template)
        
        # replace parameters
        for section, section_dict in replace_dict.items():
            for key, value in section_dict.items():
                nml.namelist[section][key] = value

        f_out = cfg.dir_wrf_run.replace('<ens>', str(iens)
                                        )+'/namelist.input'
        
        try_remove(f_out)
        nml.write(f_out)

        # copy to archive
        init = start.strftime('/%Y-%m-%d_%H:%M/')
        archdir = '/'.join([cfg.dir_archive, init, str(iens)])
        os.makedirs(archdir, exist_ok=True)
        copy(f_out, archdir+'/namelist.input')

if __name__ == '__main__':
    
    cfg = Config.from_file(sys.argv[1])
    run(cfg)
