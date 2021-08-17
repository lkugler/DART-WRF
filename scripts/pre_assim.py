import os, sys, shutil
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy, sed_inplace
import wrfout_add_geo

def run(assim_time, background_init_time, exppath_firstguess):
    """Prepares DART files for running filter 
    i.e.
    - links first guess state to DART first guess filenames
    - creates wrfinput_d01 files
    - adds geo-reference (xlat,xlon) coords so that DART can deal with the files
    - writes txt files so DART knows what input and output is
    - removes probably pre-existing files which could lead to problems
    """

    print('prepare prior state estimate')
    for iens in range(1, exp.n_ens+1):
        #wrfout_run = cluster.wrf_rundir(iens) + time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')

        print('link wrfout file to DART background file')
        wrfout_run = exppath_firstguess+background_init_time.strftime('/%Y-%m-%d_%H:%M/')  \
                    +str(iens)+assim_time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        dart_ensdir = cluster.dartrundir+'/advance_temp'+str(iens)
        wrfout_dart = dart_ensdir+'/wrfout_d01'

        os.makedirs(dart_ensdir, exist_ok=True)
        print('linking', wrfout_run, 'to', wrfout_dart)
        symlink(wrfout_run, wrfout_dart)
        symlink(wrfout_dart, dart_ensdir+'/wrfinput_d01')

        # this seems to be necessary (else wrong level selection)
        wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', wrfout_dart) 

    fpath = cluster.dartrundir+'/input_list.txt'
    print('writing', fpath)
    os.remove(fpath)
    with open(fpath, 'w') as f:
        for iens in range(1, exp.n_ens+1):
            f.write('./advance_temp'+str(iens)+'/wrfout_d01')
            f.write('\n')

    fpath = cluster.dartrundir+'/output_list.txt'
    print('writing', fpath)
    os.remove(fpath)
    with open(fpath, 'w') as f:
        for iens in range(1, exp.n_ens+1):
            f.write('./filter_restart_d01.'+str(iens).zfill(4))
            f.write('\n')


    print('removing preassim and filter_restart')
    os.system('rm -rf '+cluster.dartrundir+'/preassim_*')
    os.system('rm -rf '+cluster.dartrundir+'/filter_restart*')
    os.system('rm -rf '+cluster.dartrundir+'/output_mean*')
    os.system('rm -rf '+cluster.dartrundir+'/output_sd*')
    os.system('rm -rf '+cluster.dartrundir+'/perfect_output_*')
    os.system('rm -rf '+cluster.dartrundir+'/obs_seq.fina*')

    os.system(cluster.python+' '+cluster.scriptsdir+'/link_rttov.py')


if __name__ == '__main__':
    assim_time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    background_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
    exppath_firstguess = str(sys.argv[3])

    run(assim_time, background_init_time, exppath_firstguess)
