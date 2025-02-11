"""Create namelist.input files

Usage:
prepare_namelist.py <config> <begin> <end> <intv> [--radt=<minutes>] [--restart=<flag>] [--restart_interval=<minutes>]

Options:
--radt=<minutes>   		Radiation interval [default: 5]
--restart=<flag> 		Restart flag (.true., .false.) [default: .false.]
--restart_interval=<minutes>	Restart frequency [default: 720]
"""
import os, sys
import datetime as dt
from docopt import docopt

from dartwrf.namelist_handler import WRF_namelist
from dartwrf.server_config import cluster
from dartwrf.utils import sed_inplace, copy, read_dict_from_pyfile


if __name__ == '__main__':
    
    args = docopt(__doc__)
    archive = True
    
    f_config = args['<config>']
    exp = read_dict_from_pyfile(f_config)
    
    begin = dt.datetime.strptime(args['<begin>'], '%Y-%m-%d_%H:%M:%S')
    end = dt.datetime.strptime(args['<end>'], '%Y-%m-%d_%H:%M:%S')
    hist_interval_s = int(args['<intv>'])
    
    radt = int(args['--radt']) 
    if not radt:
        radt = '5'

    restart = False
    if args['--restart'] == '.true.':
        restart = True
    rst_flag = '.true.' if restart else '.false.'

    restart_interval = args['--restart_interval']
    if not restart_interval:
        restart_interval = 720
        
    # replace these variables in the namelist
    replace_dict = {
    'time_control': {
        # time start
        '<y1>': begin.strftime('%Y'),
        '<m1>': begin.strftime('%m'),
        '<d1>': begin.strftime('%d'),
        '<HH1>': begin.strftime('%H'),
        '<MM1>': begin.strftime('%M'),
        '<SS1>': begin.strftime('%S'),
        
        # time end
        '<y2>': end.strftime('%Y'),
        '<m2>': end.strftime('%m'),
        '<d2>': end.strftime('%d'),
        '<HH2>': end.strftime('%H'),
        '<MM2>': end.strftime('%M'),
        '<SS2>': end.strftime('%S'),
        
        # other variables
        '<dx>': str(int(exp.model_dx)),
        '<hist_interval_s>': str(int(hist_interval_s)),
        '<radt>': str(int(radt)),
        '<restart>': rst_flag,
        '<restart_interval>': str(int(float(restart_interval))),
        },
    }
        
    print('prepare namelists for all ens members',radt,restart,restart_interval)
    for iens in range(1, exp.ensemble_size+1):

        nml = WRF_namelist()
        nml.read(cluster.WRF_namelist_template)
        
        # replace parameters
        for section, section_dict in replace_dict.items():
            for key, value in section_dict.items():
                nml.namelist[section][key] = value
                
        f_out = cluster.wrf_rundir_base +'/'+ exp.name + '/'+str(iens)+'/namelist.input'
        nml.write(f_out)
        print('saved', f_out)

        
        if archive:
            archdir = cluster.archive_base+'/'+exp.name+begin.strftime('/%Y-%m-%d_%H:%M/'+str(iens)+'/')
            os.makedirs(archdir, exist_ok=True)
        else:
            archdir = './'