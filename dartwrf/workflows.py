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
import inspect

from dartwrf.utils import script_to_str, shell
from dartwrf.utils import Config


class WorkFlows(object):
    def __init__(self, cfg: Config):
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
        print('------------------------------------------------------')
        print('>>> Experiment name:         "'+cfg.name+'"')
        
        ############### ARCHIVE SCRIPTS AND CONFIGS
        # Copy scripts and config files to `self.archivedir` folder
        dirs_exist_ok = False
        if os.path.exists(cfg.dir_archive+'/DART-WRF/'):
            if input('The experiment name already exists! Overwrite existing experiment? (Y/n) ') in ['Y', 'y']:
                dirs_exist_ok = True

        shutil.copytree(cfg.dir_dartwrf_dev,
                        cfg.dir_archive+'/DART-WRF/',
                        ignore=shutil.ignore_patterns('*.git','config/','__*','tests/'),
                        dirs_exist_ok=dirs_exist_ok)
        
        
        ################# INFORM USER
        print(" ")
        print('>>> Main directory           "'+cfg.dir_archive+'"')
        print('>>> DART will run in         "'+cfg.dir_dart_run+'"')
        print('>>> WRF will run in          "'+cfg.dir_wrf_run+'"')
        
        # do we run slurm?
        self.use_slurm = cfg.use_slurm
        self.dir_log = cfg.dir_log
        self.dir_slurm = cfg.dir_slurm
        
        if self.use_slurm:
            print(" ")
            print('>>> Using SLURM, see logs in "'+self.dir_log+'"')
        print('------------------------------------------------------')
        
        # use this python path
        run_wrf_from_this_folder = cfg.dir_dartwrf_run+'/../'
        self.dir_dartwrf_run = cfg.dir_dartwrf_run
        self.python = 'export PYTHONPATH=' +run_wrf_from_this_folder+ '; '+cfg.python
        self.cfg = cfg

    def run_job(self, cmd, cfg, depends_on=None, **kwargs):
        """Run scripts in a shell

        If not using SLURM: calls scripts through shell
        if using SLURM: uses slurmpy to submit jobs, keep certain default kwargs and only update some with kwarg `overwrite_these_configurations`

        Args:
            cmd (str): Bash command(s) to run
            jobname (str, optional): Name of SLURM job
            cfg_update (dict): The config keywords will be overwritten with values
            depends_on (int or None): SLURM job id of dependency, job will start after this id finished.

        Returns 
            None
        """
        if self.use_slurm:
            from slurmpy import Slurm
            # name of calling function
            path_to_script = inspect.stack()[1].function
            jobname = path_to_script.split('/')[-1]+'-'+cfg.f_cfg_current.split('/')[-1].replace('.py','')
            print('> SLURM job:', jobname)
            
            slurm_kwargs = cfg.slurm_kwargs.copy()
            for key, value in kwargs.items():
                slurm_kwargs[key] = value
                
            return Slurm(jobname,
                        slurm_kwargs=slurm_kwargs,
                        log_dir=self.dir_log, 
                        scripts_dir=self.dir_slurm,
                        ).run(cmd, depends_on=depends_on)
        else:
            print(cmd)
            returncode = os.system(cmd)
            if returncode != 0:
                raise Exception('Error running command >>> '+cmd)

###########################################################
# USER FUNCTIONS

    def prepare_WRFrundir(self, cfg):
        """Prepare WRF run directories for all ensemble members

        Note: 
            Optionally copy input sounding profiles to WRF run directories 
            if defined in cfg.py

        Args:
            init_time (datetime): WRF initialization time

        Returns:
            None
        """
        cmd = self.python+' '+self.dir_dartwrf_run + '/prepare_wrfrundir.py '+cfg.f_cfg_current
        shell(cmd)


    def generate_obsseq_out(self, cfg, depends_on=None):
        """Creates observations from a nature run for a list of times

        Args:
            times (list): list of datetime objects

        Returns:
            str: job ID of the submitted job
        """
        path_to_script = self.dir_dartwrf_run + '/obs/create_obsseq_out.py'
        cmd = ' '.join([self.python, path_to_script, cfg.f_cfg_current])

        id = self.run_job(cmd, cfg, depends_on=[depends_on],
                          **{"ntasks": "20", "time": "30", "mem": "200G", "ntasks-per-node": "20"})
        return id


    def wrfinput_insert_wbubble(self, cfg, depends_on=None):
        """Inserts warm-bubble temperature perturbations into wrfinput files

        Note:
            Assumes that WRF run directories with wrfinput files exist.

        Args:
            perturb (bool, optional): if True, perturb the location of the warm-bubble (False: nature run)
            depends_on (str, optional): job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """ 
        path_to_script = self.dir_dartwrf_run + '/create_wbubble_wrfinput.py'
        cmd = ' '.join([self.python, path_to_script, cfg.f_cfg_current])

        id = self.run_job(cmd, cfg, depends_on=[depends_on])
        return id

    def run_ideal(self, cfg, depends_on=None):
        """Run WRF's ideal.exe for every ensemble member

        Args:
            depends_on (str, optional): job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        cmd = script_to_str(self.cfg.WRF_ideal_template
                            ).replace('<expname>', cfg.name
                            ).replace('<wrf_rundir_base>', cfg.dir_wrf_run
                            ).replace('<wrf_modules>', cfg.wrf_modules,
                            )
        id = self.run_job(cmd, cfg, depends_on=[depends_on], time="30")
        return id
    
    def run_WRF(self, cfg, depends_on=None):
        """Run the forecast ensemble
        """
        ###########################################
        start = cfg.WRF_start
        end = cfg.WRF_end
        
        # SLURM configuration for WRF
        slurm_kwargs = {"array": "1-"+str(self.cfg.ensemble_size),
                      "nodes": "1", 
                      "ntasks": str(self.cfg.max_nproc_for_each_ensemble_member), 
                      "ntasks-per-core": "1", "mem": "90G", }

        # command from template file
        wrf_cmd = script_to_str(self.cfg.WRF_exe_template
                            ).replace('<dir_wrf_run>', self.cfg.dir_wrf_run.replace('<ens>', '$IENS')
                            ).replace('<wrf_modules>', self.cfg.wrf_modules,
                            ).replace('<WRF_number_of_processors>', str(self.cfg.max_nproc_for_each_ensemble_member),
                                      )
        # prepare namelist
        path_to_script = self.dir_dartwrf_run + '/prepare_namelist.py'
        cmd = ' '.join([self.python, path_to_script, self.cfg.f_cfg_current])
        id = self.run_job(cmd, cfg, depends_on=[depends_on])

        # run WRF ensemble
        time_in_simulation_hours = (end-start).total_seconds()/3600
        runtime_wallclock_mins_expected = int(
            time_in_simulation_hours*30 + 10)  # usually <15 min/hour
        slurm_kwargs.update({"time": str(runtime_wallclock_mins_expected)})
        
        if runtime_wallclock_mins_expected > 25:
            slurm_kwargs.update({"partition": "amd"})
        #     #cfg_update.update({"exclude": "jet03"})

        id = self.run_job(wrf_cmd, cfg, depends_on=[id], **slurm_kwargs)
        return id

    def assimilate(self, cfg, depends_on=None):
        """Creates observations from a nature run and assimilates them.
        
        Returns:
            str: job ID of the submitted job
        """
        path_to_script = self.dir_dartwrf_run + '/assimilate.py'
        cmd = ' '.join([self.python, path_to_script, cfg.f_cfg_current])

        id = self.run_job(cmd, cfg, depends_on=[depends_on], 
                          **{"ntasks": "20", "time": "30", "mem": "110G",
                            "ntasks-per-node": "20", "ntasks-per-core": "1"}, 
                     )
        return id

    def prepare_IC_from_prior(self, cfg: Config, depends_on=None):
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
        path_to_script = self.dir_dartwrf_run + '/prep_IC_prior.py'
        cmd = ' '.join([self.python, path_to_script, cfg.f_cfg_current])
        id = self.run_job(cmd, cfg, depends_on=[depends_on], time="10")
        return id

    def update_IC_from_DA(self, cfg, depends_on=None):
        """Update existing initial conditions with the output from the assimilation

        Args:
            assim_time (dt.datetime):       Timestamp of the assimilation
            depends_on (str, optional):     job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        path_to_script = self.dir_dartwrf_run + '/update_IC.py'
        cmd = ' '.join([self.python, path_to_script, cfg.f_cfg_current])

        id = self.run_job(cmd, cfg, depends_on=[depends_on], time="10")
        return id

    def create_satimages(self, cfg, depends_on=None):
        """Run a job array, one job per ensemble member, to create satellite images"""
        
        prefix = 'module purge; module load rttov/v13.2-gcc-8.5.0; python'
        path_to_script = '~/RTTOV-WRF/run_init.py'
        cmd = ' '.join([prefix, path_to_script, cfg.f_cfg_current])

        id = self.run_job(cmd, cfg, depends_on=[depends_on],
                          **{"ntasks": "1", "time": "60", "mem": "10G", 
                                "array": "1-"+str(self.cfg.ensemble_size)})
        return id

    def evaluate_obs_posterior_after_analysis(self, cfg, depends_on=None):

        path_to_script = self.dir_dartwrf_run + '/evaluate_obs_space.py'
        cmd = ' '.join([self.python, path_to_script, cfg.f_cfg_current])

        id = self.run_job(cmd, cfg, depends_on=[depends_on],
                          **{"ntasks": "16", "mem": "80G", "ntasks-per-node": "16", 
                            "ntasks-per-core": "2", "time": "9", "mail-type": "FAIL"})

        # cmd = self.python+' '+self.dir_dartwrf_run + \
        #     '/calc_linear_posterior.py '+init.strftime('%Y-%m-%d_%H:%M')
        # id = self.run_job(cmd, 'linpost'+self.cfg.name, cfg_update={"ntasks": "16", "mem": "80G", "ntasks-per-node": "16", "ntasks-per-core": "2",
        #                                                                        "time": "15", "mail-type": "FAIL"},
        #                           depends_on=[id])
        return id

    def verify(self, cfg, depends_on=None):
        """Not included in DART-WRF"""
        cmd = ' '.join(['python /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py', 
                        cfg.f_cfg_current])
        id = self.run_job(cmd, cfg, depends_on=[depends_on],
                         **{"time": "210", "mail-type": "FAIL,END", 
                                    "ntasks": "10", "ntasks-per-node": "10", 
                                    "ntasks-per-core": "1", "mem": "250G"})
