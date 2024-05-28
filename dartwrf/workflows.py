#!/usr/bin/python3
"""
These functions call python scripts via the shell,
e.g. assimilate() calls dartwrf/assimilate.py through the shell.

This would not be necessary, but some users might want to use queueing systems (e.g. SLURM) which must call scripts.
"""
import os, sys, shutil, warnings
import datetime as dt

from dartwrf.utils import script_to_str

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

        def _copy_dartwrf_to_archive():
            # Copy scripts to self.cluster.archivedir folder
            try:
                shutil.copytree(self.cluster.dartwrf_dir, self.cluster.archivedir+'/DART-WRF/', 
                        ignore=shutil.ignore_patterns('*.git',))  # don't copy the git repo
                print('>>> DART-WRF scripts:          "'+self.cluster.archivedir+'/DART-WRF/"')
            except FileExistsError as e:
                warnings.warn(str(e))
                if input('The experiment name already exists! Scripts will not be overwritten. Continue? (Y/n) ') in ['Y', 'y']:
                    pass
                else:
                    raise e
            except:
                raise

        def _obskind_read():
            """Read dictionary of observation types + ID numbers ("kind") 
            from DART f90 script and return it as python dictionary
            """
            definitionfile = self.cluster.dart_srcdir+'/../../../assimilation_code/modules/observations/obs_kind_mod.f90'
            with open(definitionfile, 'r') as f:
                kind_def_f = f.readlines()

            obskind_nrs = {}
            for i, line in enumerate(kind_def_f):
                if 'Integer definitions for DART OBS TYPES' in line:
                    # data starts below this line
                    i_start = i
                    break
            for line in kind_def_f[i_start+1:]:
                if 'MAX_DEFINED_TYPES_OF_OBS' in line:
                    # end of data
                    break
                if '::' in line:
                    # a line looks like this
                    # integer, parameter, public ::       MSG_4_SEVIRI_TB =   261
                    data = line.split('::')[-1].split('=')
                    kind_str = data[0].strip()
                    kind_nr = int(data[1].strip())
                    obskind_nrs[kind_str] = kind_nr
            return obskind_nrs
        
        def _dict_to_py(d, outfile):
            """Write a python dictionary to a .py file

            Args:
                d (dict): dictionary to write
                outfile (str): path to output file

            Returns:
                None
            """
            with open(outfile, 'w') as f:
                txt = '# this file is autogenerated \nobs_kind_nrs = {'
                for k,v in d.items():
                    txt += '"'+k+'": '+str(v)+', \n'
                txt += '}'
                f.write(txt)

        print('------------------------------------------------------')
        print('>>> Starting experiment ... ')
        print('>>> Experiment configuration:  "./config/'+exp_config+'" ')
        print('>>> Server configuration:      "./config/'+server_config+'"')

        #### 1
        # copy the selected config files (arguments to Workflows(...)) to the scripts directory
        # ./DART-WRF/dartwrf/server_config.py and ./DART-WRF/dartwrf/exp_config.py
        # these config files will be used later, and no others!
        original_scripts_dir = '/'.join(__file__.split('/')[:-1])  # usually /home/DART-WRF/dartwrf/
        try:
            shutil.copyfile('config/'+server_config, original_scripts_dir+'/server_config.py')
        except shutil.SameFileError:
            pass
        try:
            shutil.copyfile('config/'+exp_config, original_scripts_dir+'/exp_config.py')
        except shutil.SameFileError:
            pass

        #### 2
        # import the configuration files from where we copied them just before
        sys.path.append(original_scripts_dir)
        from server_config import cluster
        self.cluster = cluster
        from exp_config import exp
        self.exp = exp

        print('>>> Main data folder:          "'+self.cluster.archivedir+'"')
        print('>>> Temporary DART run folder: "'+self.cluster.dart_rundir+'"')
        print('>>> Temporary WRF run folder:  "'+self.cluster.wrf_rundir_base+'"')

        #### 3
        # Set paths and backup scripts
        self.cluster.log_dir = self.cluster.archivedir+'/logs/'
        print('>>> In case of error, check logs at:"'+self.cluster.log_dir+'"')
        if self.cluster.use_slurm:
            self.cluster.slurm_scripts_dir = self.cluster.archivedir+'/slurm-scripts/'
            print('>>> SLURM scripts stored in:    "', self.cluster.slurm_scripts_dir+'"')

        #### 4
        # to be able to generate obs_seq.in files, we need a dictionary to convert obs kinds to numbers
        # a) we read the obs kind definitions (obs_kind_mod.f90 from DART code) 
        # b) we generate a python file with this dictionary
        # Note: to include it in the documentary, the file needs to exist also in the repository 
        # (so the documentation generator SPHINX can read it)
        _dict_to_py(_obskind_read(), original_scripts_dir+'/obs/obskind.py')

        #### 5
        # Copy scripts and config files to `self.cluster.archivedir` folder
        _copy_dartwrf_to_archive() 

        #### 6
        # we set the path from where python should import dartwrf modules
        # every python command then imports DART-WRF from self.cluster.archivedir+'/DART-WRF/dartwrf/'
        self.cluster.python = 'export PYTHONPATH='+self.cluster.scripts_rundir+'/../; '+self.cluster.python
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
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/prepare_wrfrundir.py '+init_time.strftime('%Y-%m-%d_%H:%M')
        print(cmd)
        os.system(cmd)

    def generate_obsseq_out(self, times, depends_on=None):
        """Creates observations from a nature run for a list of times

        Args:
            times (list): list of datetime objects

        Returns:
            str: job ID of the submitted job
        """
        times_str = ','.join([t.strftime('%Y-%m-%d_%H:%M') for t in times])

        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/obs/create_obsseq_out.py '+times_str

        id = self.cluster.run_job(cmd, "obsgen-"+self.exp.expname, cfg_update={"ntasks": "12", "time": "30",
                                "mem": "50G", "ntasks-per-node": "12", "ntasks-per-core": "2"}, depends_on=[depends_on])
        return id

    def run_ideal(self, depends_on=None):
        """Run WRF's ideal.exe for every ensemble member
        
        Args:
            depends_on (str, optional): job ID of a previous job after which to run this job
        
        Returns:
            str: job ID of the submitted job
        """
        cmd = """# run ideal.exe in parallel
    export SLURM_STEP_GRES=none
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
        id = self.cluster.run_job(cmd, "ideal-"+self.exp.expname, cfg_update={"ntasks": str(self.exp.n_ens),
                            "time": "10", "mem": "100G"}, depends_on=[depends_on])
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
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/create_wbubble_wrfinput.py'+pstr

        id = self.cluster.run_job(cmd, "ins_wbub-"+self.exp.expname, cfg_update={"time": "5"}, depends_on=[depends_on])
        return id

    def run_ENS(self, begin, end, depends_on=None, first_minutes=False, 
                input_is_restart=True, output_restart_interval=720, hist_interval=5, radt=5):
        """Run the forecast ensemble

        Args:
            begin (datetime): start time of the forecast
            end (datetime): end time of the forecast
            depends_on (str, optional): job ID of a previous job after which to run this job
            first_minutes (bool, optional): if True, get wrfout of first 2 minutes
            input_is_restart (bool, optional): if True, start WRF from WRFrst file (restart mode)
            output_restart_interval (int, optional): interval in minutes between output of WRFrst files
            hist_interval (float, optional): interval in minutes between output of WRF history files
            radt (int, optional): time step of radiation scheme

        Returns:
            str: job ID of the submitted job
        """

        def prepare_WRF_inputfiles(begin, end, hist_interval_s=300, radt=5, output_restart_interval=False, depends_on=None):
            
            args = [self.cluster.python, self.cluster.scripts_rundir+'/prepare_namelist.py',
                    begin.strftime('%Y-%m-%d_%H:%M:%S'), end.strftime('%Y-%m-%d_%H:%M:%S'),
                    str(hist_interval_s), '--radt='+str(radt), '--restart='+restart_flag,]

            if output_restart_interval:
                args.append('--restart_interval='+str(int(float(output_restart_interval))))

            return self.cluster.run_job(' '.join(args), "preWRF", 
                        cfg_update=dict(time="2"), depends_on=[depends_on])
        
        id = depends_on
        restart_flag = '.false.' if not input_is_restart else '.true.'
        wrf_cmd = script_to_str(self.cluster.run_WRF
                ).replace('<exp.expname>', self.exp.expname
                ).replace('<cluster.wrf_rundir_base>', self.cluster.wrf_rundir_base
                ).replace('<cluster.wrf_modules>', self.cluster.wrf_modules,
                ).replace('<exp.np_WRF>', str(self.cluster.np_WRF))

        # every minute output within first 2 minutes (needed for validating a radiance assimilation)
        if first_minutes:
            id = prepare_WRF_inputfiles(begin, begin+dt.timedelta(minutes=2), 
                    hist_interval_s=30,  # to get an output every 30 seconds
                    radt = 1,  # to get a cloud fraction CFRAC after 1 minute
                    output_restart_interval=output_restart_interval, 
                    depends_on=id)

            id = self.cluster.run_job(wrf_cmd, "WRF-"+self.exp.expname, 
                                      cfg_update={"array": "1-"+str(self.cluster.size_WRF_jobarray), "ntasks": "10", "nodes": "1",
                                                  "time": "10", "mem": "40G"}, 
                                      depends_on=[id])

        # forecast for the whole forecast duration       
        id = prepare_WRF_inputfiles(begin, end, 
                                    hist_interval_s=hist_interval*60, 
                                    radt=radt,
                                    output_restart_interval=output_restart_interval,
                                    depends_on=id)

        time_in_simulation_hours = (end-begin).total_seconds()/3600
        runtime_wallclock_mins_expected = int(8+time_in_simulation_hours*9)  # usually below 9 min/hour
        cfg_update = {"array": "1-"+str(self.cluster.size_WRF_jobarray), "ntasks": "10", "nodes": "1",
                      "time": str(runtime_wallclock_mins_expected), "mem": "40G", }
        # if runtime_wallclock_mins_expected > 10:
        #     cfg_update.update({"nodelist": "jet05"})
        id = self.cluster.run_job(wrf_cmd, "WRF-"+self.exp.expname, cfg_update=cfg_update, depends_on=[id])
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
                +assim_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_init_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_path_exp)

        id = self.cluster.run_job(cmd, "Assim-"+self.exp.expname, cfg_update={"ntasks": "12", "time": "60",
                                "mem": "60G", "ntasks-per-node": "12", "ntasks-per-core": "2"}, depends_on=[depends_on])
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
                    +prior_path_exp 
                    +prior_init_time.strftime(' %Y-%m-%d_%H:%M')
                    +prior_valid_time.strftime(' %Y-%m-%d_%H:%M')
                    +tnew)
        id = self.cluster.run_job(cmd, "IC-prior-"+self.exp.expname, cfg_update=dict(time="18"), depends_on=[depends_on])
        return id


    def update_IC_from_DA(self, assim_time, depends_on=None):
        """Update existing initial conditions with the output from the assimilation

        Args:
            assim_time (dt.datetime):       Timestamp of the assimilation
            depends_on (str, optional):     job ID of a previous job after which to run this job

        Returns:
            str: job ID of the submitted job
        """
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/update_IC.py '+assim_time.strftime('%Y-%m-%d_%H:%M')
        id = self.cluster.run_job(cmd, "IC-update-"+self.exp.expname, cfg_update=dict(time="18"), depends_on=[depends_on])
        return id


    def create_satimages(self, init_time, depends_on=None):
        """Run a job array, one job per ensemble member, to create satellite images"""
        cmd = 'module purge; module load rttov; ' \
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
 
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/evaluate_obs_space.py '+init.strftime('%Y-%m-%d_%H:%M,') + valid.strftime('%Y-%m-%d_%H:%M:%S')
        id = self.cluster.run_job(cmd, 'eval+1'+self.exp.expname, cfg_update={"ntasks": "12", "mem": "50G", "ntasks-per-node": "12", "ntasks-per-core": "2", 
                                                                              "time": "15", "mail-type": "FAIL"}, 
                depends_on=[depends_on])
        
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/calc_linear_posterior.py '+init.strftime('%Y-%m-%d_%H:%M')
        id = self.cluster.run_job(cmd, 'linpost'+self.exp.expname, cfg_update={"ntasks": "12", "mem": "50G", "ntasks-per-node": "12", "ntasks-per-core": "2", 
                                                                              "time": "15", "mail-type": "FAIL"}, 
                depends_on=[id])
        return id

    def verify_sat(self, depends_on=None):
        """(not included in DART-WRF)"""
        cmd = '/jetfs/home/lkugler/miniforge3/envs/verif/bin/python /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py '+self.exp.expname+' has_node sat verif1d FSS BS'

        self.cluster.run_job(cmd, "verif-SAT-"+self.exp.expname, 
                        cfg_update={"time": "60", "mail-type": "FAIL,END", "ntasks": "15", 
                                    "ntasks-per-node": "15", "ntasks-per-core": "1", "mem": "100G",}, depends_on=[depends_on])

    def verify_wrf(self, depends_on=None):
        """(not included in DART-WRF)"""
        cmd = '/jetfs/home/lkugler/miniforge3/envs/verif/bin/python /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py '+self.exp.expname+' has_node wrf verif1d FSS BS'
        
        self.cluster.run_job(cmd, "verif-WRF-"+self.exp.expname, 
                        cfg_update={"time": "180", "mail-type": "FAIL,END", "ntasks": "21", 
                                    "ntasks-per-node": "21", "ntasks-per-core": "1", "mem": "230G"}, depends_on=[depends_on])
