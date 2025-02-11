#!/usr/bin/python3
"""
These functions call python scripts via the shell,
e.g. assimilate() calls dartwrf/assimilate.py through the shell.

This would not be necessary, but some users might want to use queueing systems (e.g. SLURM) which must call scripts.
"""
import os
import sys
import shutil
import warnings
import datetime as dt
import random
import string

from dartwrf.utils import script_to_str, shell, import_from_path, read_dict_from_pyfile, write_dict_to_pyfile
from dartwrf.utils import Config


class WorkFlows(object):
    def __init__(self, expname: str, server_config: str='server_config.py'):
        """Set up the experiment folder in `archivedir`.

        1. Copy the selected config files
        2. Import configurations
        3. Prepare obskind.py file (dictionary of observation types)
        4. Copy the scripts and configs to `archivedir`
        5. Set python path
        6. Set log path and slurm scripts path

        Args:
            exp_config (str): Path to exp config file
            server_config (str): Path to the cluster config file

        Attributes:
            cluster (obj): cluster configuration as defined in server_config file
            exp (obj): experiment configuration as defined in exp_config file
        """

        def _save_config_to(src: str, dst: str):
            try:
                shutil.copyfile(src, dst)
            except shutil.SameFileError:
                pass

        print('------------------------------------------------------')
        self.expname = expname
        print('>>> Experiment name:           "'+self.expname+'"')
        print('>>> Server configuration:      "'+server_config+'"')

        self.cluster = import_from_path('config', server_config).cluster

        # some helpful variables
        self.archivedir = self.cluster.archive_base+'/'+self.expname+'/'
        dart_rundir = self.cluster.dart_rundir_base+'/'+self.expname+'/'
        self.scripts_rundir = self.archivedir+'/DART-WRF/dartwrf/'
        pattern_obs_seq_out = self.cluster.pattern_obs_seq_out.replace(
            '<archivedir>', self.archivedir)
        pattern_obs_seq_final = self.cluster.pattern_obs_seq_final.replace(
            '<archivedir>', self.archivedir)
        
        # collect all variables to put into the config file
        self.configure_defaults = {
            'expname': self.expname,
            'archivedir': self.archivedir,
            'dart_rundir': dart_rundir,
            'scripts_rundir': self.scripts_rundir,
            'pattern_obs_seq_out': pattern_obs_seq_out,
            'pattern_obs_seq_final': pattern_obs_seq_final,
        }

        self.f_cfg_base = self.archivedir + '/DART-WRF/configs/'
        self.f_cfg_current = None

        ############### ARCHIVE SCRIPTS AND CONFIGS
        # Copy scripts and config files to `self.archivedir` folder
        dirs_exist_ok = False
        if os.path.exists(self.archivedir):
            if input('The experiment name already exists! Overwrite existing experiment? (Y/n) ') in ['Y', 'y']:
                dirs_exist_ok = True

        shutil.copytree(self.cluster.dartwrf_dir_dev,
                        self.archivedir+'/DART-WRF/',
                        ignore=shutil.ignore_patterns('*.git','config/','__*','tests/'),
                        dirs_exist_ok=dirs_exist_ok)
        
        # copy cluster config to /DART-WRF/dartwrf/
        _save_config_to(server_config, self.scripts_rundir + '/server_config.py')
        
        print(" ")
        print('>>> Running experiment in  "'+self.archivedir+'"')
        self.cluster.log_dir = self.archivedir+'/logs/'

        if self.cluster.use_slurm:
            self.cluster.slurm_scripts_dir = self.archivedir+'/slurm-scripts/'
            
        print(" ")
        print('>>> DART will run in       "'+dart_rundir+'"')
        print('>>> WRF will run in        "'+self.cluster.wrf_rundir_base+'/'+self.expname+'"')

        # 6
        # we set the path from where python should import dartwrf modules
        # every python command then imports DART-WRF from self.archivedir+'/DART-WRF/dartwrf/'
        self.cluster.python = 'export PYTHONPATH=' +  \
            self.scripts_rundir+'/../; '+self.cluster.python
        print('>>> DART-WRF experiment initialized. ')
        print('------------------------------------------------------')

    def configure(self, **kwargs):
        """Update the config in Experiment.cfg
        because we cant just forward arguments to command line calls, 
        we write a config file in a specified directory
        """
        # is there an already existing config?
        if self.f_cfg_current is None:
            # there is no config, we write a new one
            cfg = Config(name=self.expname, 
                         **self.configure_defaults,
                         **kwargs) 
            self.cfg = cfg  # this will be accessed by the module functions below
            
        else:
            # there is already a config, we update it
            
            # read existing config
            cfg = read_dict_from_pyfile(self.f_cfg_current)

            # set attributes in existing object
            for key, value in kwargs.items():
                setattr(cfg, key, value)
                
        # finally, write cfg to file
        # generate random string for filename
        random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        self.f_cfg_current = self.f_cfg_base+'/cfg_'+random_str+'.py'
        write_dict_to_pyfile(cfg.__dict__, self.f_cfg_current)


    def prepare_WRFrundir(self, init_time):
        """Prepare WRF run directories for all ensemble members

        Note: 
            Optionally copy input sounding profiles to WRF run directories 
            if defined in cfg.py

        Args:
            init_time (datetime): WRF initialization time

        Returns:
            None
        """
        cmd = self.cluster.python+' '+self.scripts_rundir + \
            '/prepare_wrfrundir.py '+init_time.strftime('%Y-%m-%d_%H:%M')
        shell(cmd)

    def generate_obsseq_out(self, times, depends_on=None):
        """Creates observations from a nature run for a list of times

        Args:
            times (list): list of datetime objects

        Returns:
            str: job ID of the submitted job
        """
        times_str = ','.join([t.strftime('%Y-%m-%d_%H:%M') for t in times])

        cmd = self.cluster.python+' '+self.scripts_rundir + \
            '/obs/create_obsseq_out.py '+times_str

        id = self.cluster.run_job(cmd, "obsgen-"+self.expname,
                                  cfg_update={"ntasks": "20", "time": "30", "mem": "200G", "ntasks-per-node": "20"}, depends_on=[depends_on])
        return id


    def wrfinput_insert_wbubble(self, perturb=True, depends_on=None):
        """Inserts warm-bubble temperature perturbations into wrfinput files

        Note:
            Assumes that WRF run directories with wrfinput files exist.

        Args:
            perturb (bool, optional): if True, perturb the location of the warm-bubble (False: nature run)
            depends_on (str, optional): job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        pstr = ' '
        if perturb:
            pstr = ' perturb'
        cmd = self.cluster.python+' '+self.scripts_rundir + \
            '/create_wbubble_wrfinput.py'+pstr

        id = self.cluster.run_job(
            cmd, "ins_wbub-"+self.expname, cfg_update={"time": "5"}, depends_on=[depends_on])
        return id

    def run_ideal(self, depends_on=None):
        """Run WRF's ideal.exe for every ensemble member

        Args:
            depends_on (str, optional): job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        cmd = script_to_str(self.cluster.WRF_ideal_template
                            ).replace('<expname>', self.expname
                            ).replace('<wrf_rundir_base>', self.cluster.wrf_rundir_base
                            ).replace('<wrf_modules>', self.cluster.wrf_modules,
                            )
        id = self.cluster.run_job(cmd, "ideal-"+self.expname, 
                cfg_update={"ntasks": "1", "time": "30", "mem": "200G"}, depends_on=[depends_on])
        return id
    
    def run_ENS(self, begin, end, first_second=False,
                input_is_restart=True, output_restart_interval=360, hist_interval_s=300,
                depends_on=None):
        """Run the forecast ensemble

        Args:
            begin (datetime): start time of the forecast
            end (datetime): end time of the forecast
            depends_on (str, optional): job ID of a previous job after which to run this job
            first_second (bool, optional): if True, get wrfout of first second
            input_is_restart (bool, optional): if True, start WRF from WRFrst file (restart mode)
            output_restart_interval (int, optional): interval in minutes between output of WRFrst files
            hist_interval_s (float, optional): interval in seconds between output of WRF history files

        Returns:
            str: job ID of the submitted job
        """
        def _prepare_WRF_inputfiles(begin, end, hist_interval_s=300, radt=1,
                                   output_restart_interval: int | None = None, 
                                   depends_on=None):

            args = [self.cluster.python, self.scripts_rundir+'/prepare_namelist.py',
                    self.f_cfg_current,
                    begin.strftime('%Y-%m-%d_%H:%M:%S'), 
                    end.strftime('%Y-%m-%d_%H:%M:%S'),
                    str(hist_interval_s), 
                    '--radt='+str(radt), 
                    '--restart='+restart_flag,]

            if output_restart_interval:
                args.append('--restart_interval=' +
                            str(int(float(output_restart_interval))))

            return self.cluster.run_job(' '.join(args), "preWRF",
                                        cfg_update=dict(time="2"), depends_on=[depends_on])
            
        ###########################################
        # SLURM configuration for WRF
        cfg_wrf = {"array": "1-"+str(self.cfg.ensemble_size),
                      "nodes": "1", 
                      "ntasks": str(self.cluster.max_nproc_for_each_ensemble_member), 
                      "ntasks-per-core": "1", "mem": "90G", }

        id = depends_on
        restart_flag = '.false.' if not input_is_restart else '.true.'
        
        # command from template file
        wrf_cmd = script_to_str(self.cluster.WRF_exe_template
                            ).replace('<expname>', self.expname
                            ).replace('<wrf_rundir_base>', self.cluster.wrf_rundir_base
                            ).replace('<wrf_modules>', self.cluster.wrf_modules,
                            ).replace('<WRF_number_of_processors>', "16")

        # if 1-second forecast is required
        if first_second:
            id = _prepare_WRF_inputfiles(begin, begin+dt.timedelta(seconds=1),
                                        hist_interval_s=1,  # to get an output every 1 s
                                        radt=0,  # to get a cloud fraction CFRAC after 1 s
                                        output_restart_interval=output_restart_interval,
                                        depends_on=id)

            id = self.cluster.run_job(wrf_cmd, "WRF-"+self.expname,
                                      cfg_update=cfg_wrf,  depends_on=[id])

        # forecast for the whole forecast duration
        id = _prepare_WRF_inputfiles(begin, end,
                                    hist_interval_s=hist_interval_s,
                                    output_restart_interval=output_restart_interval,
                                    depends_on=id)

        time_in_simulation_hours = (end-begin).total_seconds()/3600
        runtime_wallclock_mins_expected = int(
            time_in_simulation_hours*30 + 10)  # usually <15 min/hour

        cfg_wrf.update({"time": str(runtime_wallclock_mins_expected)})
        
        if runtime_wallclock_mins_expected > 25:
            cfg_wrf.update({"partition": "amd"})
        #     #cfg_update.update({"exclude": "jet03"})

        id = self.cluster.run_job(
            wrf_cmd, "WRF-"+self.expname, cfg_update=cfg_wrf, depends_on=[id])
        return id

    def assimilate(self, assim_time, prior_init_time, prior_valid_time, prior_path_exp,
                   depends_on=None):
        """Creates observations from a nature run and assimilates them.

        Args:
            assim_time (dt.datetime):       timestamp of prior wrfout files
            prior_init_time (dt.datetime):  timestamp to find the directory where the prior wrfout files are
            prior_path_exp (str):           use this directory to get prior state (i.e. self.archivedir)

        Returns:
            str: job ID of the submitted job
        """
        if not os.path.exists(prior_path_exp):
            raise IOError('prior_path_exp does not exist: '+prior_path_exp)

        cmd = (self.cluster.python+' '+self.scripts_rundir+'/assimilate.py '
               + assim_time.strftime('%Y-%m-%d_%H:%M ')
               + prior_init_time.strftime('%Y-%m-%d_%H:%M ')
               + prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
               + prior_path_exp)

        id = self.cluster.run_job(cmd, "Assim-"+self.expname,
                                  cfg_update={"ntasks": "20", "time": "30", "mem": "110G",
                                              "ntasks-per-node": "20", "ntasks-per-core": "1"}, depends_on=[depends_on])
        return id

    def prepare_IC_from_prior(self, prior_path_exp, prior_init_time, prior_valid_time, new_start_time=None, depends_on=None):
        """Create initial conditions from prior wrfrst files

        Args:
            prior_path_exp (str):           Path to experiment which provides the prior
            prior_init_time (dt.datetime):  Timestamp of the prior's initialization (directory of prior wrfrst files)
            prior_valid_time (dt.datetime): Timestamp of prior wrfrst files
            new_start_time (dt.datetime, optional):   If provided, overwrites the valid time of the initial conditions; 
                                                      This hack allows you to use a prior of a different time than your forecast start time.
                                                      Usually, you don't want to do this.
            depends_on (str, optional):     job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        if new_start_time != None:
            tnew = new_start_time.strftime(' %Y-%m-%d_%H:%M')
        else:
            tnew = ''

        cmd = (self.cluster.python+' '+self.scripts_rundir+'/prep_IC_prior.py '
               + prior_path_exp
               + prior_init_time.strftime(' %Y-%m-%d_%H:%M')
               + prior_valid_time.strftime(' %Y-%m-%d_%H:%M')
               + tnew)
        id = self.cluster.run_job(
            cmd, "IC-prior-"+self.expname, cfg_update=dict(time="18"), depends_on=[depends_on])
        return id

    def update_IC_from_DA(self, assim_time, depends_on=None):
        """Update existing initial conditions with the output from the assimilation

        Args:
            assim_time (dt.datetime):       Timestamp of the assimilation
            depends_on (str, optional):     job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        cmd = self.cluster.python+' '+self.scripts_rundir + \
            '/update_IC.py '+assim_time.strftime('%Y-%m-%d_%H:%M')
        id = self.cluster.run_job(cmd, "IC-update-"+self.expname,
                                  cfg_update=dict(time="18"), depends_on=[depends_on])
        return id

    def create_satimages(self, init_time, depends_on=None):
        """Run a job array, one job per ensemble member, to create satellite images"""
        cmd = 'module purge; module load rttov/v13.2-gcc-8.5.0; ' \
            + 'python ~/RTTOV-WRF/run_init.py '+self.archivedir+init_time.strftime('/%Y-%m-%d_%H:%M/ ') \
            + '$SLURM_ARRAY_TASK_ID'
        id = self.cluster.run_job(cmd, "RTTOV-"+self.expname,
                                  cfg_update={"ntasks": "1", "time": "60", "mem": "10G", 
                                              "array": "1-"+str(self.cfg.ensemble_size)}, 
                                  depends_on=[depends_on])
        return id

    def gen_obsseq(self, depends_on=None):
        """(not included in DART-WRF)"""
        cmd = self.cluster.python+' '+self.scripts_rundir+'/obsseq_to_netcdf.py'
        id = self.cluster.run_job("obsseq_netcdf", cfg_update={"time": "10", "mail-type": "FAIL,END"},
                                  depends_on=[depends_on])
        return id

    def evaluate_obs_posterior_after_analysis(self, init, valid, depends_on=None):

        cmd = self.cluster.python+' '+self.scripts_rundir+'/evaluate_obs_space.py ' + \
            init.strftime('%Y-%m-%d_%H:%M,') + \
            valid.strftime('%Y-%m-%d_%H:%M:%S')
        id = self.cluster.run_job(cmd, 'eval+1'+self.expname, cfg_update={"ntasks": "16", "mem": "80G", "ntasks-per-node": "16", "ntasks-per-core": "2",
                                                                              "time": "9", "mail-type": "FAIL"},
                                  depends_on=[depends_on])

        # cmd = self.cluster.python+' '+self.scripts_rundir + \
        #     '/calc_linear_posterior.py '+init.strftime('%Y-%m-%d_%H:%M')
        # id = self.cluster.run_job(cmd, 'linpost'+self.expname, cfg_update={"ntasks": "16", "mem": "80G", "ntasks-per-node": "16", "ntasks-per-core": "2",
        #                                                                        "time": "15", "mail-type": "FAIL"},
        #                           depends_on=[id])
        return id

    def verify_sat(self, depends_on=None):
        """(not included in DART-WRF)"""
        cmd = self.cluster.python+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py ' + \
            self.expname+' '+self.cfg.nature_exp + ' sat has_node np=2 mem=110G'

        self.cluster.run_job(cmd, "verif-SAT-"+self.expname,
                             cfg_update={"time": "60", "mail-type": "FAIL,END", "ntasks": "2",
                                         "ntasks-per-node": "1", "ntasks-per-core": "2", "mem": "110G", }, depends_on=[depends_on])

    def verify_wrf(self, depends_on=None):
        """(not included in DART-WRF)"""
        cmd = self.cluster.python+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py ' + \
            self.expname+' '+self.cfg.nature_exp + ' wrf has_node np=10 mem=250G'

        self.cluster.run_job(cmd, "verif-WRF-"+self.expname,
                             cfg_update={"time": "210", "mail-type": "FAIL,END", "ntasks": "10",
                                         "ntasks-per-node": "10", "ntasks-per-core": "1", "mem": "250G"}, depends_on=[depends_on])
