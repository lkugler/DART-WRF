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

def slurm_submit(bashcmd, slurm_cfg_update=None, depends_on=None):
    function_name = sys._getframe(1).f_code.co_name  # magic
    id = my_Slurm(function_name, cfg_update=slurm_cfg_update, **kwargs
                 ).run(bashcmd, depends_on=[depends_on])
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
    s = my_Slurm("pre_osse", cfg_update={"time": "5", "mail-type": "BEGIN"})
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/prepare_wrfinput.py')

    s = my_Slurm("ideal", cfg_update={"ntasks": str(exp.n_nens), "time": "10",
                                      "mem-per-cpu": "2G"})
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
    mkdir -p """+cluster.archivedir()+"""/wrfinput/$n
    cp $rundir/wrfinput_d01 """+cluster.archivedir()+"""/wrfinput/$n/wrfinput_d01
done
"""
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

def run_ENS(begin, end, depends_on=None, **kwargs):
    prev_id = depends_on

    s = my_Slurm("preWRF", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/prepare_namelist.py '
               + begin.strftime('%Y-%m-%d_%H:%M')+' '
               + end.strftime('%Y-%m-%d_%H:%M'),
               depends_on=[prev_id])

    runtime_real_hours = (end-begin).total_seconds()/3600
    runtime_wallclock_mins_expected = int(11+runtime_real_hours*10)  # usually below 8 min/hour
    s = my_Slurm("runWRF", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
                 "time": str(runtime_wallclock_mins_expected), "mem-per-cpu": "2G"})
    cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
    id2 = s.run(cmd, depends_on=[id])

    # not needed, since wrf.exe writes directly to archive folder
    #s = my_Slurm("archiveWRF", cfg_update=dict(nodes="1", ntasks="1", time="10"))
    #id3 = s.run(cluster.python+' '+cluster.scriptsdir+'/archive_wrf.py '
    #           + begin.strftime('%Y-%m-%d_%H:%M'), depends_on=[id2])
    return id2


def gen_synth_obs(time, depends_on=None):

    # prepare state of nature run, from which observation is sampled
    id = slurm_submit(cluster.python+' '+cluster.scriptsdir+'/prepare_nature.py '
                      +time.strftime('%Y-%m-%d_%H:%M ') + str(channel_id),
         cfg_update=dict(time="2"), depends_on=[depends_on])

    for channel_id in exp.sat_channels:
        s = my_Slurm("pre_gensynthobs", cfg_update=dict(time="2"))
        id = s.run(cluster.python+' '+cluster.scriptsdir+'/pre_gen_synth_obs.py '
                   +time.strftime('%Y-%m-%d_%H:%M ') + str(channel_id),
                   depends_on=[id])

        s = my_Slurm("gensynth", cfg_update=dict(time="20"))
        cmd = 'cd '+cluster.dartrundir+'; mpirun -np 24 ./perfect_model_obs; '  \
              + 'obs_seq.out >> obs_seq_all.out'  # combine all observations
        id2 = s.run(cmd, depends_on=[id])
    return id2


def assimilate(assim_time, background_init_time,
               first_guess=None, depends_on=None, **kwargs):
    prev_id = depends_on

    if first_guess is None:
        first_guess = cluster.archivedir()

    s = my_Slurm("preAssim", cfg_update=dict(time="2"))
    id = s.run(cluster.python+' '+cluster.scriptsdir+'/pre_assim.py ' \
               +assim_time.strftime('%Y-%m-%d_%H:%M ')
               +background_init_time.strftime('%Y-%m-%d_%H:%M ')
               +first_guess,
               depends_on=[prev_id])

    s = my_Slurm("Assim", cfg_update=dict(time="50", mem="200G"))
    cmd = 'cd '+cluster.dartrundir+'; mpirun -np 48 ./filter; rm obs_seq_all.out'
    id2 = s.run(cmd, depends_on=[id])

    s = my_Slurm("archiveAssim", cfg_update=dict(time="10"))
    id3 = s.run(cluster.python+' '+cluster.scriptsdir+'/archive_assim.py '
               + assim_time.strftime('%Y-%m-%d_%H:%M'), depends_on=[id2])

    s = my_Slurm("updateIC", cfg_update=dict(time="3"))
    id4 = s.run(cluster.python+' '+cluster.scriptsdir+'/update_wrfinput_from_filteroutput.py '
                +assim_time.strftime('%Y-%m-%d_%H:%M'), depends_on=[id3])
    return id4

def mailme(depends_on=None):
    id = depends_on
    if id:
        s = my_Slurm("AllFinished", cfg_update={"time": "1", "mail-type": "BEGIN"})
        s.run('sleep 1', depends_on=[id])


################################
print('starting osse')


clear_logs(backup_existing_to_archive=True)

is_new_run = True
if is_new_run:
    id = prepare_wrfinput()  # create initial conditions

    # spin up the ensemble
    background_init_time = dt.datetime(2008, 7, 30, 6, 0)
    integration_end_time = dt.datetime(2008, 7, 30, 10, 0)
    id = run_ENS(begin=background_init_time,
                end=integration_end_time,
                depends_on=id)
    time = integration_end_time
else:
    # get initial conditions from archive
    background_init_time = dt.datetime(2008, 7, 30, 10, 45)
    time = dt.datetime(2008, 7, 30, 11, 0)
    exppath_arch = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.11_LMU_filter'
    first_guess = exppath_arch
    id = update_wrfinput_from_archive(time, background_init_time, exppath_arch)

# now, start the ensemble data assimilation cycles
timedelta_integrate = dt.timedelta(minutes=15)
timedelta_btw_assim = dt.timedelta(minutes=15)

while time < dt.datetime(2008, 7, 30, 14, 15):

     assim_time = time
     id = gen_synth_obs(assim_time, depends_on=id)
     id = assimilate(assim_time,
                     background_init_time,
                     first_guess=first_guess,
                     depends_on=id)

     # first_guess = None  #

     background_init_time = assim_time  # start integration from here
     integration_end_time = assim_time + timedelta_integrate
     id = run_ENS(begin=background_init_time,
                  end=integration_end_time,
                  depends_on=id)

     time += timedelta_btw_assim

mailme(id)
