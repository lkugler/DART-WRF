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

from dartwrf.utils import script_to_str, shell


class WorkFlows(object):
    def __init__(self, exp_config='cfg.py', server_config='server.py'):
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

        def _copy_dartwrf_to_archive(dirs_exist_ok=False):
            # Copy DART-WRF/dartwrf/ to self.cluster.archivedir folder
            # copy the dartwrf python package
            shutil.copytree(self.cluster.dartwrf_dir+'/dartwrf/',
                            self.cluster.archivedir+'/DART-WRF/dartwrf/',
                            ignore=shutil.ignore_patterns('*.git',),
                            dirs_exist_ok=dirs_exist_ok)
            print('>>> DART-WRF scripts:          "' +
                  self.cluster.archivedir+'/DART-WRF/"')

            # copy this script for reproducibility
            script_executing_this_process = sys.argv[0]
            shutil.copy(script_executing_this_process,
                        self.cluster.archivedir+'/DART-WRF/')

        def _save_config_to(config_fname, destination):
            try:
                shutil.copyfile('config/'+config_fname, destination)
            except shutil.SameFileError:
                pass

        print('------------------------------------------------------')
        print('>>> Starting experiment ... ')
        print('>>> Experiment configuration:  "./config/'+exp_config+'" ')
        print('>>> Server configuration:      "./config/'+server_config+'"')

        # 1
        # copy the selected config files (arguments to Workflows(...)) to the scripts directory
        # ./DART-WRF/dartwrf/server_config.py and ./DART-WRF/dartwrf/exp_config.py
        # these config files will be used later, and no others!
        # usually /home/DART-WRF/dartwrf/
        original_scripts_dir = '/'.join(__file__.split('/')[:-1])
        _save_config_to(server_config, original_scripts_dir +
                        '/server_config.py')
        _save_config_to(exp_config, original_scripts_dir+'/exp_config.py')

        # 2
        # import the configuration files from where we copied them just before
        sys.path.append(original_scripts_dir)
        from server_config import cluster
        self.cluster = cluster
        from exp_config import exp
        self.exp = exp

        print(" ")
        print('>>> Main data folder:          "'+self.cluster.archivedir+'"')
        print('>>> Temporary DART folder:     "'+self.cluster.dart_rundir+'"')
        print('>>> Temporary WRF folder:      "' +
              self.cluster.wrf_rundir_base+'"')

        # 3
        # Set paths and backup scripts
        self.cluster.log_dir = self.cluster.archivedir+'/logs/'
        print(" ")
        print('>>> Log-files:        "'+self.cluster.log_dir+'"')
        if self.cluster.use_slurm:
            self.cluster.slurm_scripts_dir = self.cluster.archivedir+'/slurm-scripts/'
            print('>>> SLURM scripts:    "'+self.cluster.slurm_scripts_dir+'"')
        print(" ")

        # 4
        # to be able to generate obs_seq.in files, we need a dictionary to convert obs kinds to numbers
        # a) we read the obs kind definitions (obs_kind_mod.f90 from DART code)
        # b) we generate a python file with this dictionary
        import create_obskind_table
        create_obskind_table.run(server_config)

        # 5
        # Copy scripts and config files to `self.cluster.archivedir` folder
        try:
            _copy_dartwrf_to_archive()
        except FileExistsError as e:
            if input('The experiment name already exists! Overwrite existing experiment? (Y/n) ') in ['Y', 'y']:
                _copy_dartwrf_to_archive(dirs_exist_ok=True)
            else:
                raise e

        # 6
        # we set the path from where python should import dartwrf modules
        # every python command then imports DART-WRF from self.cluster.archivedir+'/DART-WRF/dartwrf/'
        self.cluster.python = 'export PYTHONPATH=' + \
            self.cluster.scripts_rundir+'/../; '+self.cluster.python
        print('>>> DART-WRF experiment initialized. ')
        print('------------------------------------------------------')

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
        cmd = 'python '+self.cluster.scripts_rundir + \
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

        cmd = self.cluster.python+' '+self.cluster.scripts_rundir + \
            '/obs/create_obsseq_out.py '+times_str

        id = self.cluster.run_job(cmd, "obsgen-"+self.exp.expname,
                                  cfg_update={"ntasks": "20", "time": "30", "mem": "200G", "ntasks-per-node": "20"}, depends_on=[depends_on])
        return id

    def run_ideal(self, depends_on=None):
        """Run WRF's ideal.exe for every ensemble member

        Args:
            depends_on (str, optional): job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        cmd = self.cluster.wrf_modules+"""
    export SLURM_STEP_GRES=none
    # run ideal.exe in parallel
    for ((n=1; n<="""+str(self.exp.n_ens)+"""; n++))
    do
        rundir="""+self.cluster.wrf_rundir_base+'/'+self.exp.expname+"""/$n
        echo $rundir
        cd $rundir
        mpirun -np 1 ./ideal.exe &
    done
    wait

    # move log file to sim_archive
    for ((n=1; n<="""+str(self.exp.n_ens)+"""; n++))
    do
        rundir="""+self.cluster.wrf_rundir_base+'/'+self.exp.expname+"""/$n
        touch -a $rundir/rsl.out.0000  # create log file if it doesnt exist, to avoid error in mv if it doesnt exist
        mv $rundir/rsl.out.0000 $rundir/rsl.out.input
    done
    """
        id = self.cluster.run_job(cmd, "ideal-"+self.exp.expname, 
                cfg_update={"ntasks": "40",  "ntasks-per-node": "40",
                            "time": "30", "mem": "200G"}, depends_on=[depends_on])
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
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir + \
            '/create_wbubble_wrfinput.py'+pstr

        id = self.cluster.run_job(
            cmd, "ins_wbub-"+self.exp.expname, cfg_update={"time": "5"}, depends_on=[depends_on])
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

        def prepare_WRF_inputfiles(begin, end, hist_interval_s=300, radt=1,
                                   output_restart_interval=False, depends_on=None):

            args = [self.cluster.python, self.cluster.scripts_rundir+'/prepare_namelist.py',
                    begin.strftime(
                        '%Y-%m-%d_%H:%M:%S'), end.strftime('%Y-%m-%d_%H:%M:%S'),
                    str(hist_interval_s), '--radt='+str(radt), '--restart='+restart_flag,]

            if output_restart_interval != False:
                args.append('--restart_interval=' +
                            str(int(float(output_restart_interval))))

            return self.cluster.run_job(' '.join(args), "preWRF",
                                        cfg_update=dict(time="2"), depends_on=[depends_on])

        id = depends_on
        restart_flag = '.false.' if not input_is_restart else '.true.'
        wrf_cmd = script_to_str(self.cluster.run_WRF
                                ).replace('<exp.expname>', self.exp.expname
                                          ).replace('<cluster.wrf_rundir_base>', self.cluster.wrf_rundir_base
                                                    ).replace('<cluster.wrf_modules>', self.cluster.wrf_modules,
                                                              ).replace('<exp.np_WRF>', str(self.cluster.np_WRF))

        if first_second:
            id = prepare_WRF_inputfiles(begin, begin+dt.timedelta(seconds=1),
                                        hist_interval_s=1,  # to get an output every 1 s
                                        radt=0,  # to get a cloud fraction CFRAC after 1 s
                                        output_restart_interval=output_restart_interval,
                                        depends_on=id)

            id = self.cluster.run_job(wrf_cmd, "WRF-"+self.exp.expname,
                                      cfg_update={"array": "1-"+str(self.cluster.size_WRF_jobarray),
                                                  "nodes": "1", "ntasks": str(self.cluster.np_WRF), "ntasks-per-core": "1",
                                                  "time": "5", "mem": "100G"},
                                      depends_on=[id])

        # forecast for the whole forecast duration
        id = prepare_WRF_inputfiles(begin, end,
                                    hist_interval_s=hist_interval_s,
                                    output_restart_interval=output_restart_interval,
                                    depends_on=id)

        time_in_simulation_hours = (end-begin).total_seconds()/3600
        runtime_wallclock_mins_expected = int(
            time_in_simulation_hours*30 + 10)  # usually <15 min/hour
        cfg_update = {"array": "1-"+str(self.cluster.size_WRF_jobarray),
                      "nodes": "1", "ntasks": str(self.cluster.np_WRF), "ntasks-per-core": "1",
                      "time": str(runtime_wallclock_mins_expected), "mem": "90G", }

        if runtime_wallclock_mins_expected > 25:
            cfg_update.update({"partition": "amd"})
        #     #cfg_update.update({"exclude": "jet03"})

        id = self.cluster.run_job(
            wrf_cmd, "WRF-"+self.exp.expname, cfg_update=cfg_update, depends_on=[id])
        return id

    def assimilate(self, assim_time, prior_init_time, prior_valid_time, prior_path_exp,
                   depends_on=None):
        """Creates observations from a nature run and assimilates them.

        Args:
            assim_time (dt.datetime):       timestamp of prior wrfout files
            prior_init_time (dt.datetime):  timestamp to find the directory where the prior wrfout files are
            prior_path_exp (str):           use this directory to get prior state (i.e. self.cluster.archivedir)

        Returns:
            str: job ID of the submitted job
        """
        if not os.path.exists(prior_path_exp):
            raise IOError('prior_path_exp does not exist: '+prior_path_exp)

        cmd = (self.cluster.python+' '+self.cluster.scripts_rundir+'/assimilate.py '
               + assim_time.strftime('%Y-%m-%d_%H:%M ')
               + prior_init_time.strftime('%Y-%m-%d_%H:%M ')
               + prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
               + prior_path_exp)

        id = self.cluster.run_job(cmd, "Assim-"+self.exp.expname,
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

        cmd = (self.cluster.python+' '+self.cluster.scripts_rundir+'/prep_IC_prior.py '
               + prior_path_exp
               + prior_init_time.strftime(' %Y-%m-%d_%H:%M')
               + prior_valid_time.strftime(' %Y-%m-%d_%H:%M')
               + tnew)
        id = self.cluster.run_job(
            cmd, "IC-prior-"+self.exp.expname, cfg_update=dict(time="18"), depends_on=[depends_on])
        return id

    def update_IC_from_DA(self, assim_time, depends_on=None):
        """Update existing initial conditions with the output from the assimilation

        Args:
            assim_time (dt.datetime):       Timestamp of the assimilation
            depends_on (str, optional):     job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir + \
            '/update_IC.py '+assim_time.strftime('%Y-%m-%d_%H:%M')
        id = self.cluster.run_job(cmd, "IC-update-"+self.exp.expname,
                                  cfg_update=dict(time="18"), depends_on=[depends_on])
        return id

    def create_satimages(self, init_time, depends_on=None):
        """Run a job array, one job per ensemble member, to create satellite images"""
        cmd = 'module purge; module load rttov/v13.2-gcc-8.5.0; ' \
            + 'python ~/RTTOV-WRF/run_init.py '+self.cluster.archivedir+init_time.strftime('/%Y-%m-%d_%H:%M/ ') \
            + '$SLURM_ARRAY_TASK_ID'
        id = self.cluster.run_job(cmd, "RTTOV-"+self.exp.expname,
                                  cfg_update={"ntasks": "1", "time": "60", "mem": "10G", "array": "1-"+str(self.exp.n_ens)}, depends_on=[depends_on])
        return id

    def gen_obsseq(self, depends_on=None):
        """(not included in DART-WRF)"""
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/obsseq_to_netcdf.py'
        id = self.cluster.run_job("obsseq_netcdf", cfg_update={"time": "10", "mail-type": "FAIL,END"},
                                  depends_on=[depends_on])
        return id

    def evaluate_obs_posterior_after_analysis(self, init, valid, depends_on=None):

        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/evaluate_obs_space.py ' + \
            init.strftime('%Y-%m-%d_%H:%M,') + \
            valid.strftime('%Y-%m-%d_%H:%M:%S')
        id = self.cluster.run_job(cmd, 'eval+1'+self.exp.expname, cfg_update={"ntasks": "16", "mem": "80G", "ntasks-per-node": "16", "ntasks-per-core": "2",
                                                                              "time": "9", "mail-type": "FAIL"},
                                  depends_on=[depends_on])

        # cmd = self.cluster.python+' '+self.cluster.scripts_rundir + \
        #     '/calc_linear_posterior.py '+init.strftime('%Y-%m-%d_%H:%M')
        # id = self.cluster.run_job(cmd, 'linpost'+self.exp.expname, cfg_update={"ntasks": "16", "mem": "80G", "ntasks-per-node": "16", "ntasks-per-core": "2",
        #                                                                        "time": "15", "mail-type": "FAIL"},
        #                           depends_on=[id])
        return id

    def verify_sat(self, depends_on=None):
        """(not included in DART-WRF)"""
        cmd = self.cluster.python+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py ' + \
            self.exp.expname+' '+self.exp.nature_exp + ' sat has_node np=2 mem=110G'

        self.cluster.run_job(cmd, "verif-SAT-"+self.exp.expname,
                             cfg_update={"time": "60", "mail-type": "FAIL,END", "ntasks": "2",
                                         "ntasks-per-node": "1", "ntasks-per-core": "2", "mem": "110G", }, depends_on=[depends_on])

    def verify_wrf(self, depends_on=None):
        """(not included in DART-WRF)"""
        cmd = self.cluster.python+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py ' + \
            self.exp.expname+' '+self.exp.nature_exp + ' wrf has_node np=10 mem=250G'

        self.cluster.run_job(cmd, "verif-WRF-"+self.exp.expname,
                             cfg_update={"time": "210", "mail-type": "FAIL,END", "ntasks": "10",
                                         "ntasks-per-node": "10", "ntasks-per-core": "1", "mem": "250G"}, depends_on=[depends_on])
