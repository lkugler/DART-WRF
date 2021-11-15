#!/usr/bin/python3
"""
high level control script
submitting jobs into SLURM queue
"""
import os, sys, shutil, glob
import datetime as dt
from slurmpy import Slurm

from config.cfg import exp, cluster
from scripts.utils import script_to_str, symlink, copy


# allow scripts to access the configuration
# symlink(cluster.scriptsdir+'/../config', cluster.scriptsdir+'/config')

log_dir = cluster.archivedir+'/logs/'
slurm_scripts_dir = cluster.archivedir+'/slurm-scripts/'
print('logging to', log_dir)
print('scripts, which are submitted to SLURM:', slurm_scripts_dir)

def my_Slurm(*args, cfg_update=dict(), **kwargs):
    """Shortcut to slurmpy's class; keep certain default kwargs
    and only update some with kwarg `cfg_update`
    see https://github.com/brentp/slurmpy
    """
    return Slurm(*args, slurm_kwargs=dict(cluster.slurm_cfg, **cfg_update), 
                 log_dir=log_dir, scripts_dir=slurm_scripts_dir, **kwargs)

def backup_scripts():
    os.makedirs(cluster.archivedir, exist_ok=True)

    try:
        shutil.copytree(cluster.scriptsdir, cluster.scripts_rundir)
    except FileExistsError:
        pass
    except:
        raise
    try:
        copy(os.path.basename(__file__), cluster.scripts_rundir+'/')
    except Exception as e:
        warnings.warn(str(e))

def prepare_WRFrundir(init_time):
    """Create WRF/run directories and wrfinput files
    """
    s = my_Slurm("prep_wrfrundir", cfg_update={"time": "5", "mail-type": "BEGIN"})
    id = s.run(cluster.python+' '+cluster.scripts_rundir+'/prepare_wrfrundir.py '
                +init_time.strftime('%Y-%m-%d_%H:%M'))
    return id

def run_ideal(depends_on=None):
    """Run ideal for every ensemble member"""
    cmd = """# run ideal.exe in parallel, then add geodata
export SLURM_STEP_GRES=none
for ((n=1; n<="""+str(exp.n_ens)+"""; n++))
do
    rundir="""+cluster.tmpfiledir+'/run_WRF/'+exp.expname+"""/$n
    echo $rundir
    cd $rundir
    mpirun -np 1 ./ideal.exe &
done
wait
for ((n=1; n<="""+str(exp.n_ens)+"""; n++))
do
    rundir="""+cluster.tmpfiledir+'/run_WRF/'+exp.expname+"""/$n
    mv $rundir/rsl.out.0000 $rundir/rsl.out.input
done
"""
    s = my_Slurm("ideal", cfg_update={"ntasks": str(exp.n_ens), "nodes": "1",
                                      "time": "10", "mem-per-cpu": "2G"})
    id = s.run(cmd, depends_on=[depends_on])
    return id

def update_wrfinput_from_archive(valid_time, background_init_time, exppath, depends_on=None):
    """Given that directories with wrfinput files exist,
    update these wrfinput files according to wrfout files
    """
    s = my_Slurm("upd_wrfinput", cfg_update={"time": "5"})

    # path of initial conditions, <iens> is replaced by member index
    IC_path = exppath + background_init_time.strftime('/%Y-%m-%d_%H:%M/')  \
              +'*iens*/'+valid_time.strftime('/wrfout_d01_%Y-%m-%d_%H:%M:%S')
    id = s.run(cluster.python+' '+cluster.scripts_rundir+'/update_wrfinput_from_wrfout.py '
                +IC_path, depends_on=[depends_on])
    return id

def wrfinput_insert_wbubble(perturb=True, depends_on=None):
    """Given that directories with wrfinput files exist,
    update these wrfinput files with warm bubbles
    """
    s = my_Slurm("ins_wbubble", cfg_update={"time": "5"})
    pstr = ' '
    if perturb:
        pstr = ' perturb'
    id = s.run(cluster.python+' '+cluster.scripts_rundir+'/create_wbubble_wrfinput.py'+pstr,
               depends_on=[depends_on])
    return id

def run_ENS(begin, end, depends_on=None, first_minute=True, 
            input_is_restart=False, restart_path=False, output_restart_interval=720):
    """Run forecast for 1 minute, save output. 
    Then run whole timespan with 5 minutes interval.

    if input_is_restart:  # start WRF in restart mode
      if restart_path:  
        # restart from a wrfrst file in restart_path directory
        # e.g. when restarting from a state in an archivedir (from any existing experiment)
      else: 
        # restart from wrfrst files that are already in run_WRF directories
        # e.g. after updateIC, it puts wrfrst in run_WRF directories
    """
    id = depends_on
    restart_flag = '.false.' if not input_is_restart else '.true.'

    if False:  # doesnt work with restarts at the moment# first_minute:
        # first minute forecast (needed for validating an assimilation)
        hist_interval = 1
        radt = 1  # calc CFRAC also in first minute
        begin_plus1 = begin+dt.timedelta(minutes=1)
        s = my_Slurm("preWRF1", cfg_update=dict(time="2"))
        args = [cluster.python, cluster.scripts_rundir+'/prepare_namelist.py',
                begin.strftime('%Y-%m-%d_%H:%M'),
                begin_plus1.strftime('%Y-%m-%d_%H:%M'),
                str(hist_interval),
                '--radt='+str(radt),
                '--restart='+restart_flag,]
        if restart_path:  # restart from a wrfrst file in restart_path directory
            args.append('--rst_inname='+restart_path) 
        id = s.run(' '.join(args), depends_on=[id])

        s = my_Slurm("runWRF1", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
                    "time": "2", "mem-per-cpu": "2G"})
        cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
        id = s.run(cmd, depends_on=[id])

        # apply forward operator (DART filter without assimilation)
        s = my_Slurm("fwOP-1m", cfg_update=dict(time="10", ntasks=48))
        id = s.run(cluster.python+' '+cluster.scripts_rundir+'/apply_obs_op_dart.py '
                   + begin.strftime('%Y-%m-%d_%H:%M')+' '
                   + begin_plus1.strftime('%Y-%m-%d_%H:%M'),
                   depends_on=[id])

    # whole forecast timespan
    hist_interval = 5
    radt = 5
    args = [cluster.python,
                cluster.scripts_rundir+'/prepare_namelist.py',
                begin.strftime('%Y-%m-%d_%H:%M'),
                end.strftime('%Y-%m-%d_%H:%M'),
                str(hist_interval),
                '--radt='+str(radt),
                '--restart='+restart_flag,]
    if restart_path:
        args.append('--rst_inname='+restart_path)
    if output_restart_interval:
        args.append('--restart_interval='+str(int(float(output_restart_interval))))

    s = my_Slurm("preWRF2", cfg_update=dict(time="2"))
    id = s.run(' '.join(args), depends_on=[id])

    time_in_simulation_hours = (end-begin).total_seconds()/3600
    runtime_wallclock_mins_expected = int(8+time_in_simulation_hours*9.5)  # usually below 9 min/hour
    s = my_Slurm("runWRF2", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
                "time": str(runtime_wallclock_mins_expected), "mem-per-cpu": "2G"})
    cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
    id = s.run(cmd, depends_on=[id])

    # not needed, since wrf.exe writes directly to archive folder
    #s = my_Slurm("archiveWRF", cfg_update=dict(nodes="1", ntasks="1", time="10"))
    #id3 = s.run(cluster.python+' '+cluster.scripts_rundir+'/archive_wrf.py '
    #           + begin.strftime('%Y-%m-%d_%H:%M'), depends_on=[id2])
    return id

def assimilate(assim_time, prior_init_time, prior_valid_time,
               prior_path_exp=False, input_is_restart=False, depends_on=None):
    """Creates observations from a nature run and assimilates them.

    Args:
        assim_time (dt.datetime): timestamp of prior wrfout files
        prior_init_time (dt.datetime): 
            timestamp to find the directory where the prior wrfout files are
        prior_path_exp (bool or str):
            put a `str` to take the prior from a different experiment
            if False: use `archivedir` (defined in config) to get prior state
            if str: use this directory to get prior state
    """
    if not prior_path_exp:
        prior_path_exp = cluster.archivedir
    elif not isinstance(prior_path_exp, str):
        raise TypeError('prior_path_exp either str or False, is '+str(type(prior_path_exp)))

    id = my_Slurm("Assim", cfg_update={"nodes": "1", "ntasks": "96", "time": "60",
                             "mem": "300G", "ntasks-per-node": "96", "ntasks-per-core": "2"}
            ).run(cluster.python+' '+cluster.scripts_rundir+'/assim_synth_obs.py '
               +assim_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_init_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_path_exp, depends_on=[depends_on])
 
    id = my_Slurm("WRF_IC", cfg_update=dict(time="8")
            ).run(cluster.python+' '+cluster.scripts_rundir+'/prepare_wrf_initials.py '
                +assim_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_init_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_path_exp, depends_on=[id])
    return id


def create_satimages(init_time, depends_on=None):
    s = my_Slurm("pRTTOV", cfg_update={"ntasks": "48", "time": "60", "nodes": "1"})
    id = s.run(cluster.python+' /home/fs71386/lkugler/RTTOV-WRF/run_init.py '+cluster.archivedir
               +init_time.strftime('/%Y-%m-%d_%H:%M/'),
          depends_on=[depends_on])
    return id

def mailme(depends_on=None):
    if depends_on:
        s = my_Slurm("AllFinished", cfg_update={"time": "1", "mail-type": "BEGIN"})
        s.run('sleep 1', depends_on=[depends_on])

def gen_obsseq(depends_on=None):
    s = my_Slurm("obsseq_netcdf", cfg_update={"time": "10", "mail-type": "FAIL,END"})
    id = s.run(cluster.python+' '+cluster.scripts_rundir+'/obsseq_to_netcdf.py',
               depends_on=[depends_on])
    return id

def verify(depends_on=None):
    s = my_Slurm("verify", cfg_update={"time": "240", "mail-type": "FAIL,END", 
                 "ntasks": "96",  "ntasks-per-node": "96", "ntasks-per-core": "2"})
    s.run(cluster.python_enstools+' '+cluster.userdir+'/osse_analysis/analyze_fc.py '+exp.expname+' has_node',
          depends_on=[depends_on])

def copy_to_jet(depends_on=None):
    Slurm('rsync-jet', slurm_kwargs={"time": "30",
          "account": "p71386", "partition": "mem_0384", "qos": "p71386_0384",
          "ntasks": "1", "mem": "5gb",
          "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"},
          log_dir=log_dir, scripts_dir=slurm_scripts_dir,
    ).run("bash -c 'nohup rsync -avh "+cluster.archivedir+" lkugler@jet01.img.univie.ac.at:/jetfs/home/lkugler/data/sim_archive/ &'",
          depends_on=[depends_on])

################################
if __name__ == "__main__":
    print('starting osse')

    timedelta_integrate = dt.timedelta(minutes=30)
    timedelta_btw_assim = dt.timedelta(minutes=30)

    backup_scripts()
    id = None

    start_from_existing_state = True
    is_new_run = not start_from_existing_state

    init_time = dt.datetime(2008, 7, 30, 10)
    id = prepare_WRFrundir(init_time)

    if is_new_run:
        id = run_ideal(depends_on=id)
        id = wrfinput_insert_wbubble(depends_on=id)

        # spin up the ensemble
        integration_end_time = dt.datetime(2008, 7, 30, 14)
        id = run_ENS(begin=init_time,
                    end=integration_end_time,
                    first_minute=False,
                    depends_on=id)
        prior_path_exp = False  # for next assimilation
        
    elif start_from_existing_state:
        #prior_path_exp = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.16_Pwbub_40mem'
        #prior_path_exp = cluster.archivedir  # 
        prior_path_exp = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.18_Pwbub-1-ensprof_40mem_rst'
        #prior_path_exp = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.18_Pwbub_PriorPert10_40mem'
        #id = update_wrfinput_from_archive(integration_end_time, init_time, prior_path_exp, depends_on=id)
        #id = wrfinput_insert_wbubble(depends_on=id)

    # values for assimilation
    time = dt.datetime(2008, 7, 30, 11)
    assim_time = time
    prior_init_time = init_time

    while time <= dt.datetime(2008, 7, 30, 11):

        id = assimilate(assim_time,
                        prior_init_time, 
                        prior_valid_time=time, #+dt.timedelta(hours=2),
                        prior_path_exp=prior_path_exp,
                        input_is_restart=True,
                        depends_on=id)
        prior_path_exp = cluster.archivedir  # use own exp path as prior

        # integration
        this_forecast_init = assim_time  # start integration from here

        timedelta_integrate = timedelta_btw_assim
        if this_forecast_init.minute in [0,]:  # longer forecast every full hour
            timedelta_integrate = dt.timedelta(hours=3)

        this_forecast_end = assim_time + timedelta_integrate

        id = run_ENS(begin=this_forecast_init,
                    end=this_forecast_end,
                    input_is_restart=True, 
                    restart_path=False, #cluster.archivedir+prior_init_time.strftime('/%Y-%m-%d_%H:%M/'),
                    output_restart_interval=30, #timedelta_btw_assim.total_seconds()/60,
                    depends_on=id)
        
        create_satimages(this_forecast_init, depends_on=id)

        # increment time
        time += timedelta_btw_assim

        # values for next iteration
        assim_time = time
        prior_init_time = time - timedelta_btw_assim

    id = gen_obsseq(id)
    verify(id)
