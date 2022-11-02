"""Create namelist.input files

Usage:
  prepare_namelist.py <begin> <end> <intv> [--radt=<minutes>] [--restart=<flag>] [--restart_interval=<minutes>]

Options:
  --radt=<minutes>   		Radiation interval [default: 5]
  --restart=<flag> 		Restart flag (.true., .false.) [default: .false.]
  --restart_interval=<minutes>	Restart frequency [default: 720]
"""
import os, sys, shutil, warnings
import datetime as dt
from docopt import docopt

from config.cfg import exp, cluster
from utils import sed_inplace, copy, symlink, mkdir

def run(iens, begin, end, hist_interval=5, radt=5, archive=True,
        restart=False, restart_interval=720):
    """Create namelist.input files

    Args:
    archive (bool): if True, write to archivedir of experiment
        if False, write to WRF run directory
    restart (str): fortran bool whether to use wrfinput or wrfrst
    restart_interval (int): output frequency of wrfrst (minutes)
    """
    rundir = cluster.wrf_rundir(iens)
    copy(cluster.namelist, rundir+'/namelist.input')

    sed_inplace(rundir+'/namelist.input', '<dx>', str(int(exp.model_dx)))
    #sed_inplace(rundir+'/namelist.input', '<timestep>', str(int(exp.timestep)))
    sed_inplace(rundir+'/namelist.input', '<hist_interval>', str(int(hist_interval)))
    sed_inplace(rundir+'/namelist.input', '<radt>', str(int(radt)))

    rst_flag = '.true.' if restart else '.false.'
    sed_inplace(rundir+'/namelist.input', '<restart>', rst_flag)
    sed_inplace(rundir+'/namelist.input', '<restart_interval>', str(int(float(restart_interval))))

    if archive:
        archdir = cluster.archivedir+begin.strftime('/%Y-%m-%d_%H:%M/'+str(iens)+'/')
        os.makedirs(archdir, exist_ok=True)
    else:
        archdir = './'
    sed_inplace(rundir+'/namelist.input', '<archivedir>', archdir)

    # set times
    for k, v in {'<y1>': '%Y', '<m1>': '%m', '<d1>': '%d',
                 '<HH1>': '%H', '<MM1>': '%M'}.items():
        sed_inplace(rundir+'/namelist.input', k, begin.strftime(v))
    for k, v in {'<y2>': '%Y', '<m2>': '%m', '<d2>': '%d',
                 '<HH2>': '%H', '<MM2>': '%M'}.items():
        sed_inplace(rundir+'/namelist.input', k, end.strftime(v))

    print(rundir+'/namelist.input created')
    print('runtime:', begin, end, 'output to', archdir)
    #########################
    if archive:
        
        init_dir = cluster.archivedir+begin.strftime('/%Y-%m-%d_%H:%M/')+str(iens)
        os.makedirs(init_dir, exist_ok=True)
        print('copy namelist to archive')
        copy(rundir+'/namelist.input', init_dir+'/namelist.input')
        try:
            if not restart:
                print('copy wrfinput of this run to archive')
                wrfin_old = rundir+'/wrfinput_d01'
                wrfin_arch = init_dir+'/wrfinput_d01'
                copy(wrfin_old, wrfin_arch)
        except Exception as e:
            warnings.warn(str(e))


if __name__ == '__main__':
    args = docopt(__doc__)
    begin = dt.datetime.strptime(args['<begin>'], '%Y-%m-%d_%H:%M')
    end = dt.datetime.strptime(args['<end>'], '%Y-%m-%d_%H:%M')
    intv = int(args['<intv>'])

    radt = int(args['--radt']) 
    if not radt:
        radt = '5'

    restart = False
    if args['--restart'] == '.true.':
        restart = True

    restart_interval = args['--restart_interval']
    if not restart_interval:
        restart_interval = 720

    print('prepare namelists for all ens members',intv,radt,restart,restart_interval)
    for iens in range(1, exp.n_ens+1):

        run(iens, begin, end, hist_interval=intv, radt=radt, 
            restart=restart, restart_interval=restart_interval)
