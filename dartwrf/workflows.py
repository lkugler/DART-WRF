#!/usr/bin/python3
"""
These functions mostly call python scripts via the shell,
e.g. assimilate() calls dartwrf/assim_synth_obs.py through the shell.

This would not be necessary, but some users might want to use queueing systems (e.g. SLURM) which must call scripts.
"""
import os, sys, shutil, glob, warnings
import datetime as dt
import importlib

from dartwrf.utils import script_to_str
from config.cfg import exp

class WorkFlows(object):
    def __init__(self, exp_config='cfg.py', server_config='server.py'):
        """Set up the experiment folder in `archivedir`.

        Args:
            exp (str): Path to exp config file
            config (str): Path to the cluster config file
        """
        # At first, load config from present folder (later from scripts_rundir)
        # exp = __import__('config/'+exp_config)
        self.cluster = importlib.import_module('config.'+server_config.strip('.py')).cluster

        # Set paths and backup scripts
        self.cluster.log_dir = self.cluster.archivedir+'/logs/'
        print('logging to', self.cluster.log_dir)

        if self.cluster.use_slurm:
            self.cluster.slurm_scripts_dir = self.cluster.archivedir+'/slurm-scripts/'
            print('scripts, which are submitted to SLURM:', self.cluster.slurm_scripts_dir)

        # Copy scripts to self.cluster.archivedir folder
        os.makedirs(self.cluster.archivedir, exist_ok=True)
        try:
            shutil.copytree(self.cluster.scriptsdir, self.cluster.scripts_rundir)
            print('scripts have been copied to', self.cluster.archivedir)
        except FileExistsError as e:
            warnings.warn(str(e))
        except:
            raise

        # Copy config files
        shutil.copy('config/'+exp_config, self.cluster.scripts_rundir+'/cfg.py')
        shutil.copy('config/'+server_config, self.cluster.scripts_rundir+'/cluster.py')  # whatever server, the config name is always the same!
        shutil.copy('config/'+server_config, 'config/cluster.py')  # whatever server, the config name is always the same!


    def prepare_WRFrundir(self, init_time):
        """Create WRF/run directories and wrfinput files
        """
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/prepare_wrfrundir.py '+init_time.strftime('%Y-%m-%d_%H:%M')
        print(cmd)
        os.system(cmd)

    def run_ideal(self, depends_on=None):
        """Run ideal for every ensemble member"""
        cmd = """# run ideal.exe in parallel, then add geodata
    export SLURM_STEP_GRES=none
    for ((n=1; n<="""+str(exp.n_ens)+"""; n++))
    do
        rundir="""+self.cluster.wrf_rundir_base+'/'+exp.expname+"""/$n
        echo $rundir
        cd $rundir
        mpirun -np 1 ./ideal.exe &
    done
    wait
    for ((n=1; n<="""+str(exp.n_ens)+"""; n++))
    do
        rundir="""+self.cluster.wrf_rundir_base+'/'+exp.expname+"""/$n
        mv $rundir/rsl.out.0000 $rundir/rsl.out.input
    done
    """
        id = self.cluster.run_job(cmd, "ideal", cfg_update={"ntasks": str(exp.n_ens),
                            "time": "10", "mem": "100G"}, depends_on=[depends_on])
        return id

    def wrfinput_insert_wbubble(self, perturb=True, depends_on=None):
        """Given that directories with wrfinput files exist,
        update these wrfinput files with warm bubbles
        """

        pstr = ' '
        if perturb:
            pstr = ' perturb'
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/create_wbubble_wrfinput.py'+pstr

        id = self.cluster.run_job(cmd, "ins_wbubble", cfg_update={"time": "5"}, depends_on=[depends_on])
        return id

    def run_ENS(self, begin, end, depends_on=None, first_minute=True, 
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
        #     s = self.cluster.run_job("preWRF1", cfg_update=dict(time="2"))
        #     args = [self.cluster.python, self.cluster.scripts_rundir+'/prepare_namelist.py',
        #             begin.strftime('%Y-%m-%d_%H:%M'),
        #             begin_plus1.strftime('%Y-%m-%d_%H:%M'),
        #             str(hist_interval),
        #             '--radt='+str(radt),
        #             '--restart='+restart_flag,]
        #     id = s.run(' '.join(args), depends_on=[id])

        #     s = self.cluster.run_job("runWRF1", cfg_update={"nodes": "1", "array": "1-"+str(exp.n_nodes),
        #                 "time": "2", "mem-per-cpu": "2G"})
        #     cmd = script_to_str(self.cluster.run_WRF).replace('<expname>', exp.expname)
        #     id = s.run(cmd, depends_on=[id])

        #     # apply forward operator (DART filter without assimilation)
        #     s = self.cluster.run_job("fwOP-1m", cfg_update=dict(time="10", ntasks=48))
        #     id = s.run(self.cluster.python+' '+self.cluster.scripts_rundir+'/apply_obs_op_dart.py '
        #                + begin.strftime('%Y-%m-%d_%H:%M')+' '
        #                + begin_plus1.strftime('%Y-%m-%d_%H:%M'),
        #                depends_on=[id])

        # whole forecast timespan
        hist_interval = 5
        radt = 5
        args = [self.cluster.python,
                    self.cluster.scripts_rundir+'/prepare_namelist.py',
                    begin.strftime('%Y-%m-%d_%H:%M'),
                    end.strftime('%Y-%m-%d_%H:%M'),
                    str(hist_interval),
                    '--radt='+str(radt),
                    '--restart='+restart_flag,]
        if output_restart_interval:
            args.append('--restart_interval='+str(int(float(output_restart_interval))))

        id = self.cluster.run_job(' '.join(args), "preWRF", cfg_update=dict(time="2"), depends_on=[id])

        cmd = script_to_str(self.cluster.run_WRF).replace('<exp.expname>', exp.expname
                                        ).replace('<cluster.wrf_rundir_base>', self.cluster.wrf_rundir_base)

        time_in_simulation_hours = (end-begin).total_seconds()/3600
        runtime_wallclock_mins_expected = int(8+time_in_simulation_hours*9.5)  # usually below 9 min/hour

        id = self.cluster.run_job(cmd, "WRF", cfg_update={"array": "1-"+str(self.cluster.size_jobarray), "ntasks": "10", "nodes": "1",
                            "time": str(runtime_wallclock_mins_expected), "mem": "140G"}, depends_on=[id])
        return id


    def assimilate(self, assim_time, prior_init_time, prior_valid_time, prior_path_exp, 
                depends_on=None):
        """Creates observations from a nature run and assimilates them.

        Args:
            assim_time (dt.datetime):       timestamp of prior wrfout files
            prior_init_time (dt.datetime):  timestamp to find the directory where the prior wrfout files are
            prior_path_exp (str):           use this directory to get prior state (i.e. self.cluster.archivedir)
        """
        if not os.path.exists(prior_path_exp):
            raise IOError('prior_path_exp does not exist: '+prior_path_exp)

        cmd = (self.cluster.python+' '+self.cluster.scripts_rundir+'/assim_synth_obs.py '
                +assim_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_init_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_path_exp)

        id = self.cluster.run_job(cmd, "Assim", cfg_update={"ntasks": "12", "time": "60",
                                "mem": "200G", "ntasks-per-node": "12", "ntasks-per-core": "2"}, depends_on=[depends_on])
        return id


    def prepare_IC_from_prior(self, prior_path_exp, prior_init_time, prior_valid_time, new_start_time=None, depends_on=None):

        if new_start_time != None:
            tnew = new_start_time.strftime(' %Y-%m-%d_%H:%M')
        else:
            tnew = ''

        cmd = (self.cluster.python+' '+self.cluster.scripts_rundir+'/prep_IC_prior.py '
                    +prior_path_exp 
                    +prior_init_time.strftime(' %Y-%m-%d_%H:%M')
                    +prior_valid_time.strftime(' %Y-%m-%d_%H:%M')
                    +tnew)
        id = self.cluster.run_job(cmd, "IC-prior", cfg_update=dict(time="8"), depends_on=[depends_on])
        return id


    def update_IC_from_DA(self, assim_time, depends_on=None):
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/update_IC.py '+assim_time.strftime('%Y-%m-%d_%H:%M')
        id = self.cluster.run_job(cmd, "IC-update", cfg_update=dict(time="8"), depends_on=[depends_on])
        return id


    def create_satimages(self, init_time, depends_on=None):
        cmd = self.cluster.python_verif+' ~/RTTOV-WRF/run_init.py '+self.cluster.archivedir+init_time.strftime('/%Y-%m-%d_%H:%M/')
        id = self.cluster.run_job(cmd, "RTTOV", cfg_update={"ntasks": "12", "time": "80", "mem": "200G"}, depends_on=[depends_on])
        return id


    def gen_obsseq(self, depends_on=None):
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/obsseq_to_netcdf.py'
        id = self.cluster.run_job("obsseq_netcdf", cfg_update={"time": "10", "mail-type": "FAIL,END"}, 
                depends_on=[depends_on])
        return id


    def verify_sat(self, depends_on=None):
        cmd = self.cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py '+exp.expname+' has_node sat verif1d FSS BS'

        self.cluster.run_job(cmd, "verif-SAT-"+exp.expname, 
                        cfg_update={"time": "60", "mail-type": "FAIL,END", "ntasks": "20", 
                                    "ntasks-per-node": "20", "ntasks-per-core": "1", "mem": "100G",}, depends_on=[depends_on])

    def verify_wrf(self, depends_on=None):
        cmd = self.cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py '+exp.expname+' has_node wrf verif1d verif3d FSS BS'
        
        self.cluster.run_job(cmd, "verif-WRF-"+exp.expname, 
                        cfg_update={"time": "120", "mail-type": "FAIL,END", "ntasks": "20", 
                                    "ntasks-per-node": "20", "ntasks-per-core": "1", "mem": "250G"}, depends_on=[depends_on])

    def verify_fast(self, depends_on=None):
        cmd = self.cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_fast/plot_single_exp.py '+exp.expname

        self.cluster.run_job(cmd, "verif-fast-"+exp.expname, 
                        cfg_update={"time": "10", "mail-type": "FAIL", "ntasks": "1",
                                    "ntasks-per-node": "1", "ntasks-per-core": "1"}, depends_on=[depends_on])