import os, sys, shutil, warnings
import datetime as dt

sys.path.append(os.getcwd())
from config.cfg import exp, cluster
from utils import sed_inplace, copy, symlink, mkdir

def run(cluster, iens, begin, end):
    rundir = cluster.wrf_rundir(iens)
    print(rundir)
    copy(cluster.namelist, rundir+'/namelist.input')

    sed_inplace(rundir+'/namelist.input', '<dx>', str(int(exp.model_dx)))
    sed_inplace(rundir+'/namelist.input', '<timestep>', str(int(exp.timestep)))

    archdir = cluster.archivedir()+begin.strftime('/%Y-%m-%d_%H:%M/'+str(iens)+'/')
    print('namelist for run from', begin, end, 'output to', archdir)
    sed_inplace(rundir+'/namelist.input', '<archivedir>', archdir)
    os.makedirs(archdir, exist_ok=True)

    # set times
    for k, v in {'<y1>': '%Y', '<m1>': '%m', '<d1>': '%d',
                 '<HH1>': '%H', '<MM1>': '%M'}.items():
        sed_inplace(rundir+'/namelist.input', k, begin.strftime(v))
    for k, v in {'<y2>': '%Y', '<m2>': '%m', '<d2>': '%d',
                 '<HH2>': '%H', '<MM2>': '%M'}.items():
        sed_inplace(rundir+'/namelist.input', k, end.strftime(v))

    #########################
    try:
        print('copy wrfinput of this run to archive')
        wrfin_old = rundir+'/wrfinput_d01'
        init_dir = cluster.archivedir()+begin.strftime('/%Y-%m-%d_%H:%M/')+str(iens)
        os.makedirs(init_dir, exist_ok=True)
        wrfin_arch = init_dir+'/wrfinput_d01'
        copy(wrfin_old, wrfin_arch)
    except Exception as e:
        warnings.warn(str(e))


if __name__ == '__main__':
    begin = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    end = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')

    print('prepare namelists for all ens members')
    for iens in range(1, exp.n_ens+1):
        run(cluster, iens, begin, end)
