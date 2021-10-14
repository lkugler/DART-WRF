import os, sys, shutil
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy, sed_inplace, try_remove
import wrfout_add_geo

def run(assim_time, prior_init_time, prior_valid_time, prior_path_exp)
    """Prepares DART files for running filter 
    i.e.
    - links first guess state to DART first guess filenames
    - creates wrfinput_d01 files
    - adds geo-reference (xlat,xlon) coords so that DART can deal with the files
    - writes txt files so DART knows what input and output is
    - removes probably pre-existing files which could lead to problems
    """
    os.makedirs(cluster.dartrundir, exist_ok=True)

    print('prepare prior state estimate')
    for iens in range(1, exp.n_ens+1):
        print('link wrfout file to DART background file')
        wrfout_run = prior_path_exp \
                    +prior_init_time.strftime('/%Y-%m-%d_%H:%M/')  \
                    +str(iens) \
                    +prior_valid_time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
        dart_ensdir = cluster.dartrundir+'/advance_temp'+str(iens)
        wrfout_dart = dart_ensdir+'/wrfout_d01'

        os.makedirs(dart_ensdir, exist_ok=True)
        print('copy', wrfout_run, 'to', wrfout_dart)
        copy(wrfout_run, wrfout_dart)
        symlink(wrfout_dart, dart_ensdir+'/wrfinput_d01')

        # ensure prior time matches assim time (can be off intentionally)
        if assim_time != prior_valid_time:
            print('overwriting time in prior from nature wrfout')
            os.system(cluster.ncks+' -A -v XTIME '
                      +cluster.dartrundir+'/wrfout_d01 '+wrfout_dart)

        # this seems to be necessary (else wrong level selection)
        wrfout_add_geo.run(cluster.dartrundir+'/../geo_em.d01.nc', wrfout_dart) 

    fpath = cluster.dartrundir+'/input_list.txt'
    print('writing', fpath)
    try_remove(fpath)
    with open(fpath, 'w') as f:
        for iens in range(1, exp.n_ens+1):
            f.write('./advance_temp'+str(iens)+'/wrfout_d01')
            f.write('\n')

    fpath = cluster.dartrundir+'/output_list.txt'
    print('writing', fpath)
    try_remove(fpath)
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
    prior_init_time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
    prior_valid_time = dt.datetime.strptime(sys.argv[3], '%Y-%m-%d_%H:%M')
    prior_path_exp = str(sys.argv[4])

    run(assim_time, prior_init_time, prior_valid_time, prior_path_exp)
