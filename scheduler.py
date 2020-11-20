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
    s = my_Slurm("prep_wrfinput", cfg_update={"time": "5", "mail-type": "BEGIN"})
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/prepare_wrfinput.py')

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
    s = my_Slurm("ideal", cfg_update={"ntasks": str(exp.n_ens),
                                      "time": "10", "mem-per-cpu": "2G"})
    id = s.run(cmd, depends_on=[id])
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
    """Run forecast for 1 minute, save output. 
    Then run whole timespan with 5 minutes interval.
    """
    id = depends_on

    # first minute forecast (needed for validating an assimilation)
    hist_interval = 1
    begin_plus1 = begin+dt.timedelta(minutes=1)
    s = my_Slurm("preWRF1", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/prepare_namelist.py '
            + begin.strftime('%Y-%m-%d_%H:%M')+' '
            + begin_plus1.strftime('%Y-%m-%d_%H:%M')+' '
            + str(hist_interval), 
            depends_on=[id])

    s = my_Slurm("runWRF1", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
                "time": "2", "mem-per-cpu": "2G"})
    cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
    id = s.run(cmd, depends_on=[id])

    # apply forward operator (DART filter without assimilation)
    s = my_Slurm("fwOP-1m", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/apply_obs_op_dart.py '
               + begin.strftime('%Y-%m-%d_%H:%M')+' '
               + begin_plus1.strftime('%Y-%m-%d_%H:%M'),
               depends_on=[id])

    # whole forecast timespan
    hist_interval = 5
    s = my_Slurm("preWRF2", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/prepare_namelist.py '
            + begin.strftime('%Y-%m-%d_%H:%M')+' '
            + end.strftime('%Y-%m-%d_%H:%M')+' '
            + str(hist_interval), 
            depends_on=[id])

    time_in_simulation_hours = (end-begin).total_seconds()/3600
    runtime_wallclock_mins_expected = int(4+time_in_simulation_hours*9)  # usually below 8 min/hour
    s = my_Slurm("runWRF2", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
                "time": str(runtime_wallclock_mins_expected), "mem-per-cpu": "2G"})
    cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
    id = s.run(cmd, depends_on=[id])

    # not needed, since wrf.exe writes directly to archive folder
    #s = my_Slurm("archiveWRF", cfg_update=dict(nodes="1", ntasks="1", time="10"))
    #id3 = s.run(cluster.python+' '+cluster.scriptsdir+'/archive_wrf.py '
    #           + begin.strftime('%Y-%m-%d_%H:%M'), depends_on=[id2])
    return id

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
    s = my_Slurm("prepNature", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/prepare_nature.py '
               +time.strftime('%Y-%m-%d_%H:%M'), depends_on=[depends_on])

    # prepare prior model state
    s = my_Slurm("preAssim", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/pre_assim.py '
               +assim_time.strftime('%Y-%m-%d_%H:%M ')
               +background_init_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_expdir, depends_on=[id])

    # generate observations
    s = my_Slurm("genSynthObs", cfg_update=dict(ntasks="48", time="10"))
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
    s = my_Slurm("pRTTOV", cfg_update={"ntasks": "48", "time": "40"})
    s.run(cluster.python+' /home/fs71386/lkugler/RTTOV-WRF/loop.py '+exp.expname,
          depends_on=[depends_on])

def mailme(depends_on=None):
    if depends_on:
        s = my_Slurm("AllFinished", cfg_update={"time": "1", "mail-type": "BEGIN"})
        s.run('sleep 1', depends_on=[depends_on])


################################
print('starting osse')

timedelta_integrate = dt.timedelta(minutes=45)
timedelta_btw_assim = dt.timedelta(minutes=30)

clear_logs(backup_existing_to_archive=False)
id = None

start_from_existing_state = True
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
    background_init_time = dt.datetime(2008, 7, 30, 11, 30)
    time = dt.datetime(2008, 7, 30, 12)
    exppath_arch = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.12_LMU_so_VIS2'
    first_guess = exppath_arch
    id = update_wrfinput_from_archive(time, background_init_time, exppath_arch, depends_on=id)

while time <= dt.datetime(2008, 7, 30, 15):
    assim_time = time
     id = assimilate(assim_time,
                     background_init_time,
                     prior_from_different_exp=first_guess,
                     depends_on=id)
    first_guess = False

    prev_forecast_init = assim_time - timedelta_btw_assim
    this_forecast_init = assim_time  # start integration from here
    this_forecast_end = assim_time + timedelta_btw_assim

    id = run_ENS(begin=this_forecast_init,
                end=this_forecast_end,
                depends_on=id)
    time += timedelta_btw_assim

    create_satimages(depends_on=id)

mailme(id)
