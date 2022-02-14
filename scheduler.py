#!/usr/bin/python3
"""
high level control script
submitting jobs into SLURM queue
"""
import os, sys, shutil, glob, warnings
import datetime as dt
from slurmpy import Slurm

from config.cfg import exp, cluster
from dartwrf.utils import script_to_str, symlink, copy

log_dir = cluster.archivedir+'/logs/'
slurm_scripts_dir = cluster.archivedir+'/slurm-scripts/'
print('logging to', log_dir)
print('scripts, which are submitted to SLURM:', slurm_scripts_dir)

class Shellslurm():
    def __init__(self, *args, **kwargs):
        pass
    def run(self, *args, **kwargs):
        print(args[0])
        os.system(args[0])

def my_Slurm(*args, cfg_update=dict(), **kwargs):
    """Shortcut to slurmpy's class; keep certain default kwargs
    and only update some with kwarg `cfg_update`
    see https://github.com/brentp/slurmpy
    """
    debug = False  # run without SLURM, locally on headnode
    if debug:
        return Shellslurm(*args)
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
    rundir="""+cluster.wrf_rundir_base+'/'+exp.expname+"""/$n
    echo $rundir
    cd $rundir
    mpirun -np 1 ./ideal.exe &
done
wait
for ((n=1; n<="""+str(exp.n_ens)+"""; n++))
do
    rundir="""+cluster.wrf_rundir_base+'/'+exp.expname+"""/$n
    mv $rundir/rsl.out.0000 $rundir/rsl.out.input
done
"""
    s = my_Slurm("ideal", cfg_update={"ntasks": str(exp.n_ens), "nodes": "1",
                                      "time": "10", "mem-per-cpu": "2G"})
    id = s.run(cmd, depends_on=[depends_on])
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
            input_is_restart=True, restart_path=False, output_restart_interval=720):
    """Run forecast for 1 minute, save output. 
    Then run whole timespan with 5 minutes interval.

    if input_is_restart:  # start WRF in restart mode
    """
    id = depends_on
    restart_flag = '.false.' if not input_is_restart else '.true.'

    # if False:  # doesnt work with restarts at the moment# first_minute:
    #     # first minute forecast (needed for validating an assimilation)
    #     hist_interval = 1
    #     radt = 1  # calc CFRAC also in first minute
    #     begin_plus1 = begin+dt.timedelta(minutes=1)
    #     s = my_Slurm("preWRF1", cfg_update=dict(time="2"))
    #     args = [cluster.python, cluster.scripts_rundir+'/prepare_namelist.py',
    #             begin.strftime('%Y-%m-%d_%H:%M'),
    #             begin_plus1.strftime('%Y-%m-%d_%H:%M'),
    #             str(hist_interval),
    #             '--radt='+str(radt),
    #             '--restart='+restart_flag,]
    #     id = s.run(' '.join(args), depends_on=[id])

    #     s = my_Slurm("runWRF1", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
    #                 "time": "2", "mem-per-cpu": "2G"})
    #     cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
    #     id = s.run(cmd, depends_on=[id])

    #     # apply forward operator (DART filter without assimilation)
    #     s = my_Slurm("fwOP-1m", cfg_update=dict(time="10", ntasks=48))
    #     id = s.run(cluster.python+' '+cluster.scripts_rundir+'/apply_obs_op_dart.py '
    #                + begin.strftime('%Y-%m-%d_%H:%M')+' '
    #                + begin_plus1.strftime('%Y-%m-%d_%H:%M'),
    #                depends_on=[id])

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
    if output_restart_interval:
        args.append('--restart_interval='+str(int(float(output_restart_interval))))

    s = my_Slurm("preWRF2", cfg_update=dict(time="2"))
    id = s.run(' '.join(args), depends_on=[id])

    time_in_simulation_hours = (end-begin).total_seconds()/3600
    runtime_wallclock_mins_expected = int(8+time_in_simulation_hours*9.5)  # usually below 9 min/hour
    s = my_Slurm("runWRF2", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
                "time": str(runtime_wallclock_mins_expected), "mem-per-cpu": "2G"})
    cmd = script_to_str(cluster.run_WRF).replace('<exp.expname>', exp.expname
                                       ).replace('<cluster.wrf_rundir_base>', cluster.wrf_rundir_base)
    id = s.run(cmd, depends_on=[id])
    return id


def assimilate(assim_time, prior_init_time, prior_valid_time, prior_path_exp, 
               depends_on=None):
    """Creates observations from a nature run and assimilates them.

    Args:
        assim_time (dt.datetime):       timestamp of prior wrfout files
        prior_init_time (dt.datetime):  timestamp to find the directory where the prior wrfout files are
        prior_path_exp (str):           use this directory to get prior state (i.e. cluster.archivedir)
    """
    if not os.path.exists(prior_path_exp):
        raise IOError('prior_path_exp does not exist: '+prior_path_exp)

    id = my_Slurm("Assim", cfg_update={"nodes": "1", "ntasks": "96", "time": "60",
                             "mem": "300G", "ntasks-per-node": "96", "ntasks-per-core": "2"}
            ).run(cluster.python+' '+cluster.scripts_rundir+'/assim_synth_obs.py '
               +assim_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_init_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_path_exp, depends_on=[depends_on])
    return id


def prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=None):
    id = my_Slurm("IC-prior", cfg_update=dict(time="8")
            ).run(cluster.python+' '+cluster.scripts_rundir+'/prep_IC_prior.py '
                +prior_path_exp 
                +prior_init_time.strftime(' %Y-%m-%d_%H:%M')
                +prior_valid_time.strftime(' %Y-%m-%d_%H:%M'), depends_on=[depends_on])
    return id


def update_IC_from_DA(assim_time, depends_on=None):
    id = my_Slurm("IC-update", cfg_update=dict(time="8")
            ).run(cluster.python+' '+cluster.scripts_rundir+'/update_IC.py '
                +assim_time.strftime('%Y-%m-%d_%H:%M'), depends_on=[depends_on])
    return id


def create_satimages(init_time, depends_on=None):
    s = my_Slurm("pRTTOV", cfg_update={"ntasks": "48", "time": "60", "nodes": "1"})
    id = s.run('/home/fs71386/lkugler/RTTOV-WRF/withmodules /home/fs71386/lkugler/RTTOV-WRF/run_init.py '+cluster.archivedir
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
    s = my_Slurm("verify-"+exp.expname, cfg_update={"time": "240", "mail-type": "FAIL,END", "ntasks": "1", 
            "ntasks-per-node": "1", "ntasks-per-core": "1"})
    s.run(cluster.python_enstools+' /home/fs71386/lkugler/osse_analysis/analyze_fc.py '+exp.expname+' has_node plot',
          depends_on=[depends_on])


################################
if __name__ == "__main__":
    print('starting osse')

    timedelta_integrate = dt.timedelta(minutes=15)
    timedelta_btw_assim = dt.timedelta(minutes=15)

    backup_scripts()
    id = None

    init_time = dt.datetime(2008, 7, 30, 12)
    time = dt.datetime(2008, 7, 30, 13)

    id = prepare_WRFrundir(init_time)
    #id = run_ideal(depends_on=id)

    #prior_path_exp = cluster.archivedir  # 
    prior_path_exp = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.19_P1_noDA'
    #id = wrfinput_insert_wbubble(depends_on=id)
    
    prior_init_time = init_time
    prior_valid_time = time

    while time <= dt.datetime(2008, 7, 30, 14):

        # usually we take the prior from the current time
        # but one could use a prior from a different time from another run
        # i.e. 13z as a prior to assimilate 12z observations
        prior_valid_time = time

        id = assimilate(time, prior_init_time, prior_valid_time, prior_path_exp, depends_on=id)

        # 1) Set posterior = prior
        id = prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

        # 2) Update posterior += updates from assimilation
        id = update_IC_from_DA(time, depends_on=id)

        # How long shall we integrate?
        timedelta_integrate = timedelta_btw_assim
        output_restart_interval = timedelta_btw_assim.total_seconds()/60
        if time == dt.datetime(2008, 7, 30, 14): #this_forecast_init.minute in [0,]:  # longer forecast every full hour
            timedelta_integrate = dt.timedelta(hours=1)
            output_restart_interval = 9999

        # 3) Run WRF ensemble
        id = run_ENS(begin=time,  # start integration from here
                    end=time + timedelta_integrate,  # integrate until here
                    output_restart_interval=output_restart_interval,
                    depends_on=id)

        # as we have WRF output, we can use own exp path as prior
        prior_path_exp = cluster.archivedir       
 
        create_satimages(time, depends_on=id)

        # increment time
        time += timedelta_btw_assim

        # update time variables
        prior_init_time = time - timedelta_btw_assim

    id = gen_obsseq(id)
    verify(id)
