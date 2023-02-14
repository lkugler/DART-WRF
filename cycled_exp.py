#!/usr/bin/python3
"""
Run a cycled OSSE with WRF and DART.
"""
import os, sys, shutil, glob, warnings
import datetime as dt

from dartwrf.utils import script_to_str
from config.cfg import exp
from config.clusters import cluster

def prepare_WRFrundir(init_time):
    """Create WRF/run directories and wrfinput files
    """
    cmd = cluster.python+' '+cluster.scripts_rundir+'/prepare_wrfrundir.py '+init_time.strftime('%Y-%m-%d_%H:%M')
    print(cmd)
    os.system(cmd)

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
    s = cluster.create_job("ideal", cfg_update={"ntasks": str(exp.n_ens),
                                      "time": "10", "mem": "100G"})
    id = s.run(cmd, depends_on=[depends_on])
    return id

def wrfinput_insert_wbubble(perturb=True, depends_on=None):
    """Given that directories with wrfinput files exist,
    update these wrfinput files with warm bubbles
    """
    s = cluster.create_job("ins_wbubble", cfg_update={"time": "5"})
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
    #     s = cluster.create_job("preWRF1", cfg_update=dict(time="2"))
    #     args = [cluster.python, cluster.scripts_rundir+'/prepare_namelist.py',
    #             begin.strftime('%Y-%m-%d_%H:%M'),
    #             begin_plus1.strftime('%Y-%m-%d_%H:%M'),
    #             str(hist_interval),
    #             '--radt='+str(radt),
    #             '--restart='+restart_flag,]
    #     id = s.run(' '.join(args), depends_on=[id])

    #     s = cluster.create_job("runWRF1", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
    #                 "time": "2", "mem-per-cpu": "2G"})
    #     cmd = script_to_str(cluster.run_WRF).replace('<expname>', exp.expname)
    #     id = s.run(cmd, depends_on=[id])

    #     # apply forward operator (DART filter without assimilation)
    #     s = cluster.create_job("fwOP-1m", cfg_update=dict(time="10", ntasks=48))
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

    s = cluster.create_job("preWRF", cfg_update=dict(time="2"))
    id = s.run(' '.join(args), depends_on=[id])

    time_in_simulation_hours = (end-begin).total_seconds()/3600
    runtime_wallclock_mins_expected = int(8+time_in_simulation_hours*9.5)  # usually below 9 min/hour
    s = cluster.create_job("WRF", cfg_update={"array": "1-"+str(cluster.size_jobarray), "ntasks": "10", "nodes": "1",
                "time": str(runtime_wallclock_mins_expected), "mem": "140G"})
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

    id = cluster.create_job("Assim", cfg_update={"ntasks": "12", "time": "60",
                             "mem": "200G", "ntasks-per-node": "12", "ntasks-per-core": "2"}
            ).run(cluster.python+' '+cluster.scripts_rundir+'/assim_synth_obs.py '
               +assim_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_init_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
               +prior_path_exp, depends_on=[depends_on])
    return id


def prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, new_start_time=None, depends_on=None):

    if new_start_time != None:
        tnew = new_start_time.strftime(' %Y-%m-%d_%H:%M')
    else:
        tnew = ''

    id = cluster.create_job("IC-prior", cfg_update=dict(time="8")
            ).run(cluster.python+' '+cluster.scripts_rundir+'/prep_IC_prior.py '
                +prior_path_exp 
                +prior_init_time.strftime(' %Y-%m-%d_%H:%M')
                +prior_valid_time.strftime(' %Y-%m-%d_%H:%M')
                +tnew, depends_on=[depends_on])
    return id


def update_IC_from_DA(assim_time, depends_on=None):
    id = cluster.create_job("IC-update", cfg_update=dict(time="8")
            ).run(cluster.python+' '+cluster.scripts_rundir+'/update_IC.py '
                +assim_time.strftime('%Y-%m-%d_%H:%M'), depends_on=[depends_on])
    return id


def create_satimages(init_time, depends_on=None):
    s = cluster.create_job("RTTOV", cfg_update={"ntasks": "12", "time": "80", "mem": "200G"})
    id = s.run(cluster.python_verif+' ~/RTTOV-WRF/run_init.py '+cluster.archivedir
               +init_time.strftime('/%Y-%m-%d_%H:%M/'),
          depends_on=[depends_on])
    return id


def mailme(depends_on=None):
    if depends_on:
        s = cluster.create_job("AllFinished", cfg_update={"time": "1", "mail-type": "BEGIN"})
        s.run('sleep 1', depends_on=[depends_on])


def gen_obsseq(depends_on=None):
    s = cluster.create_job("obsseq_netcdf", cfg_update={"time": "10", "mail-type": "FAIL,END"})
    id = s.run(cluster.python+' '+cluster.scripts_rundir+'/obsseq_to_netcdf.py',
               depends_on=[depends_on])
    return id


def verify_sat(depends_on=None):
    s = cluster.create_job("verif-SAT-"+exp.expname, cfg_update={"time": "60", "mail-type": "FAIL,END", "ntasks": "20", 
            "ntasks-per-node": "20", "ntasks-per-core": "1", "mem": "100G",})
    cmd = cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py '+exp.expname+' has_node sat verif1d FSS BS'
    s.run(cmd, depends_on=[depends_on])

def verify_wrf(depends_on=None):
    s = cluster.create_job("verif-WRF-"+exp.expname, cfg_update={"time": "120", "mail-type": "FAIL,END", "ntasks": "20", 
                 "ntasks-per-node": "20", "ntasks-per-core": "1", "mem": "250G"})
    cmd = cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py '+exp.expname+' has_node wrf verif1d verif3d FSS BS'
    s.run(cmd, depends_on=[depends_on])

def verify_fast(depends_on=None):
    s = cluster.create_job("verif-fast-"+exp.expname, cfg_update={"time": "10", "mail-type": "FAIL", "ntasks": "1",
        "ntasks-per-node": "1", "ntasks-per-core": "1"})
    cmd = cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_fast/plot_single_exp.py '+exp.expname
    s.run(cmd, depends_on=[depends_on])

################################
if __name__ == "__main__":
    print('starting osse')
    cluster.setup()

    timedelta_integrate = dt.timedelta(minutes=15)
    timedelta_btw_assim = dt.timedelta(minutes=15)

    id = None

    if False:  # warm bubble
        prior_path_exp = '/jetfs/home/lkugler/data/sim_archive/exp_v1.19_P3_wbub7_noDA'

        init_time = dt.datetime(2008, 7, 30, 12)
        time = dt.datetime(2008, 7, 30, 12, 30)
        last_assim_time = dt.datetime(2008, 7, 30, 13,30)
        forecast_until = dt.datetime(2008, 7, 30, 18)
    
        prepare_WRFrundir(init_time)
        # id = run_ideal(depends_on=id)
        # id = wrfinput_insert_wbubble(depends_on=id)    

    if True:  # random
        prior_path_exp = '/jetfs/home/lkugler/data/sim_archive/exp_v1.19_P2_noDA'

        init_time = dt.datetime(2008, 7, 30, 12)
        time = dt.datetime(2008, 7, 30, 13)
        last_assim_time = dt.datetime(2008, 7, 30, 14)
        forecast_until = dt.datetime(2008, 7, 30, 18)

        prepare_WRFrundir(init_time)
        # id = run_ideal(depends_on=id)

    # prior_path_exp = cluster.archivedir
    # prior_path_exp = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.19_P5+su_noDA'
    
    prior_init_time = init_time
    prior_valid_time = time

    while time <= last_assim_time:

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
        if time == last_assim_time: #this_forecast_init.minute in [0,]:  # longer forecast every full hour
            timedelta_integrate = forecast_until - last_assim_time  # dt.timedelta(hours=4)
            output_restart_interval = 9999  # timedelta_btw_assim.total_seconds()/60 # 9999

        # 3) Run WRF ensemble
        id = run_ENS(begin=time,  # start integration from here
                    end=time + timedelta_integrate,  # integrate until here
                    output_restart_interval=output_restart_interval,
                    depends_on=id)
        
        # as we have WRF output, we can use own exp path as prior
        prior_path_exp = cluster.archivedir       

        id_sat = create_satimages(time, depends_on=id)
        
        # increment time
        time += timedelta_btw_assim

        # update time variables
        prior_init_time = time - timedelta_btw_assim

    verify_sat(id_sat)
    verify_wrf(id)
    verify_fast(id)
