#!/usr/bin/python3
"""
high level control script
submitting jobs into SLURM queue
"""
import os, sys, shutil
import datetime as dt
from slurmpy import Slurm

# necessary to find modules in folder, since SLURM runs the script elsewhere
sys.path.append(os.getcwd())

from config.cfg import exp, cluster
from scripts.utils import script_to_str, symlink

# allow scripts to access the configuration
symlink(cluster.scriptsdir+'/../config', cluster.scriptsdir+'/config')

def my_Slurm(*args, cfg_update=dict(), **kwargs):
    """Shortcut to slurmpy's class; keep default kwargs
    and only update according to `cfg_update`
    see https://github.com/brentp/slurmpy
    """
    return Slurm(*args, slurm_kwargs=dict(cluster.slurm_cfg, **cfg_update), **kwargs)

class Cmdline(object):
    def __init__(self, name, cfg_update):
        self.name = name

    def run(self, cmd, **kwargs):
        print('running', self.name, 'without SLURM')
        os.system(cmd)

def slurm_submit(bashcmd, name=None, cfg_update=None, depends_on=None):
    """Submit a 'workflow task'=script=job to the SLURM queue.
    Args:
        bashcmd (str): command to run (i.e. call to script)
        name (str): SLURM job name (useful for debugging)
        cfg_update (dict): enforce these SLURM parameters
        depends_on (int): SLURM id; job starts as soon as this id has finished
    Returns:
        int : SLURM job id, can be used in `depends_on` of another `slurm_submit` call
    """
    if name is None:  # slurm job name = name of calling function
        name = sys._getframe(1).f_code.co_name
    id = my_Slurm(name, cfg_update=cfg_update).run(bashcmd, depends_on=depends_on)
    return id

def clear_logs(backup_existing_to_archive=True):
    dirs = ['/logs/', '/slurm-scripts/']
    for d in dirs:
        archdir = cluster.archivedir()+d
        if backup_existing_to_archive:
            os.makedirs(archdir, exist_ok=True)
        dir = cluster.scriptsdir+'/../'+d
        for f in os.listdir(dir):
            if backup_existing_to_archive:
                shutil.move(dir+f, archdir+f)
            else:
                os.remove(dir+f)

def prepare_wrfinput():
    """Create WRF/run directories and wrfinput files
    """
    # s = my_Slurm("pre_osse", cfg_update={"time": "5", "mail-type": "BEGIN"})
    # id = s.run(cluster.python+' '+cluster.scriptsdir+'/prepare_wrfinput.py')
    id = slurm_submit(cluster.python+' '+cluster.scriptsdir+'/prepare_wrfinput.py',
                      name='prep_wrfinput', cfg_update={"time": "5", "mail-type": "BEGIN"})

    cmd = """# run ideal.exe in parallel, then add geodata
export SLURM_STEP_GRES=none
for ((n=1; n<="""+str(exp.n_ens)+"""; n++))
do
    rundir="""+cluster.userdir+'/run_WRF/'+exp.expname+"""/$n
    echo $rundir
    cd $rundir
    mpirun -np 1 ./ideal.exe &
done
wait
for ((n=1; n<="""+str(exp.n_ens)+"""; n++))
do
    rundir="""+cluster.userdir+'/run_WRF/'+exp.expname+"""/$n
    mv $rundir/rsl.out.0000 $rundir/rsl.out.input
done
"""
    id = slurm_submit(cmd, name="ideal", cfg_update={"ntasks": str(exp.n_ens),
                      "time": "10", "mem-per-cpu": "2G"}, depends_on=[id])
    return id

def update_wrfinput_from_archive(time, background_init_time, exppath, depends_on=None):
    """Given that directories with wrfinput files exist,
    update these wrfinput files according to wrfout files
    """
    s = my_Slurm("upd_wrfinput", cfg_update={"time": "5"})

    # path of initial conditions, <iens> is replaced by member index
    IC_path = exppath + background_init_time.strftime('/%Y-%m-%d_%H:%M/')  \
              +'*iens*/'+time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/update_wrfinput_from_wrfout.py '
                +IC_path, depends_on=[depends_on])
    return id

def run_ENS(begin, end, depends_on=None):
    prev_id = depends_on

    s = my_Slurm("preWRF", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/prepare_namelist.py '
               + begin.strftime('%Y-%m-%d_%H:%M')+' '
               + end.strftime('%Y-%m-%d_%H:%M'),
               depends_on=[prev_id])

    runtime_real_hours = (end-begin).total_seconds()/3600
    runtime_wallclock_mins_expected = int(5+runtime_real_hours*9)  # usually below 8 min/hour
    s = my_Slurm("runWRF", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
                 "time": str(runtime_wallclock_mins_expected), "mem-per-cpu": "2G"})
    cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
    id2 = s.run(cmd, depends_on=[id])

    # not needed, since wrf.exe writes directly to archive folder
    #s = my_Slurm("archiveWRF", cfg_update=dict(nodes="1", ntasks="1", time="10"))
    #id3 = s.run(cluster.python+' '+cluster.scriptsdir+'/archive_wrf.py '
    #           + begin.strftime('%Y-%m-%d_%H:%M'), depends_on=[id2])
    return id2

def assimilate(assim_time, background_init_time,
               prior_from_different_exp=False, depends_on=None):
    """Creates observations from a nature run and assimilates them.

    Args:
        assim_time (dt.datetime): timestamp of prior wrfout files
        background_init_time (dt.datetime): 
            timestamp to find the directory where the prior wrfout files are
        prior_from_different_exp (bool or str):
            put a `str` to take the prior from a different experiment
            if False: use `archivedir` (defined in config) to get prior state
            if str: use this directory to get prior state
    """
    id = depends_on

    if prior_from_different_exp:
        prior_expdir = prior_from_different_exp
    else:
        prior_expdir = cluster.archivedir()

    # prepare state of nature run, from which observation is sampled
    id = slurm_submit(cluster.python+' '+cluster.scriptsdir+'/prepare_nature.py '
                      +time.strftime('%Y-%m-%d_%H:%M'), name='prep_nature',
         cfg_update=dict(time="2"), depends_on=[depends_on])

    # prepare prior model state
    s = my_Slurm("preAssim", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/pre_assim.py '
               +assim_time.strftime('%Y-%m-%d_%H:%M ')
               +background_init_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_expdir,
               depends_on=[id])

    # generate observations
    s = my_Slurm("gensynthobs", cfg_update=dict(ntasks="48", time="10"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/gen_synth_obs.py '
               +time.strftime('%Y-%m-%d_%H:%M'),
               depends_on=[id])
 
    # actuall assimilation step
    s = my_Slurm("Assim", cfg_update=dict(ntasks="48", time="50", mem="200G"))
    cmd = 'cd '+cluster.dartrundir+'; mpirun -np 48 ./filter; rm obs_seq_all.out'
    id = s.run(cmd, depends_on=[id])

    s = my_Slurm("archiveAssim", cfg_update=dict(time="10"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/archive_assim.py '
               + assim_time.strftime('%Y-%m-%d_%H:%M'), depends_on=[id])

    s = my_Slurm("updateIC", cfg_update=dict(time="8"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/update_wrfinput_from_filteroutput.py '
                +assim_time.strftime('%Y-%m-%d_%H:%M ')
                +background_init_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_expdir, depends_on=[id])
    return id


def create_satimages(depends_on=None):
    s = my_Slurm("pRTTOV", cfg_update={"ntasks": "48", "time": "20"})
    s.run(cluster.python+' /home/fs71386/lkugler/RTTOV-WRF/loop.py '+exp.expname,
          depends_on=[depends_on])

def mailme(depends_on=None):
    if depends_on:
        s = my_Slurm("AllFinished", cfg_update={"time": "1", "mail-type": "BEGIN"})
        s.run('sleep 1', depends_on=[depends_on])


################################
print('starting osse')

timedelta_integrate = dt.timedelta(minutes=30)
timedelta_btw_assim = dt.timedelta(minutes=30)

clear_logs(backup_existing_to_archive=True)
id = None

start_from_existing_state = False
is_new_run = not start_from_existing_state

if is_new_run:
    id = prepare_wrfinput()  # create initial conditions

    # spin up the ensemble
    background_init_time = dt.datetime(2008, 7, 30, 6, 0)
    integration_end_time = dt.datetime(2008, 7, 30, 10, 0)
    id = run_ENS(begin=background_init_time,
                end=integration_end_time,
                depends_on=id)
    time = integration_end_time
    first_guess = False
    
elif start_from_existing_state:
    id = prepare_wrfinput()  # create initial conditions
    
    # get initial conditions from archive
    background_init_time = dt.datetime(2008, 7, 30, 10)
    time = dt.datetime(2008, 7, 30, 10,30)
    exppath_arch = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.11_LMU_filter'
    first_guess = exppath_arch
    id = update_wrfinput_from_archive(time, background_init_time, exppath_arch,
                                      depends_on=id)

while time <= dt.datetime(2008, 7, 30, 16):
     assim_time = time
     id = assimilate(assim_time,
                     background_init_time,
                     prior_from_different_exp=first_guess,
                     depends_on=id)
     first_guess = False

     background_init_time = assim_time  # start integration from here
     integration_end_time = assim_time + timedelta_integrate
     id = run_ENS(begin=background_init_time,
                  end=integration_end_time,
                  depends_on=id)
     time += timedelta_btw_assim

     create_satimages(depends_on=id)

mailme(id)
