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

class WorkFlows(object):
    def __init__(self, exp_config='cfg.py', server_config='server.py'):
        """Set up the experiment folder in `archivedir`.

        1. Copy the DART-WRF scripts to `archivedir`
        2. Copy the config files to `archivedir/dartwrf`
        3. Set log paths
        4. Write obskind.py file (dictionary of observation types)
        
        we load the config from load the config from cluster.scripts_rundir/config/cfg.py

        Args:
            exp_config (str): Path to exp config file
            server_config (str): Path to the cluster config file

        Attributes:
            cluster (obj): cluster configuration as defined in server_config file
            exp (obj): experiment configuration as defined in exp_config file
        """

        def copy_dartwrf_to_archive():
            # Copy scripts to self.cluster.archivedir folder
            try:
                shutil.copytree(self.cluster.dartwrf_dir, self.cluster.archivedir+'/DART-WRF/')
                print('DART-WRF has been copied to', self.cluster.archivedir)
            except FileExistsError as e:
                warnings.warn(str(e))
                if input('The experiment name already exists! Scripts will not be overwritten. Continue? (Y/n) ') in ['Y', 'y']:
                    pass
                else:
                    raise e
            except:
                raise

        # def copy_config_to_archive():
        #     os.makedirs(self.cluster.scripts_rundir+'/config/', exist_ok=True)

        #     # later, we can load the exp cfg with `from config.cfg import exp`
        #     shutil.copyfile('config/'+exp_config, self.cluster.scripts_rundir+'/config/cfg.py')

        #     # later, we can load the cluster cfg with `from config.cluster import cluster`
        #     shutil.copyfile('config/'+server_config, self.cluster.scripts_rundir+'/config/cluster.py')  # whatever server, the config name is always the same!

        print('------ start exp from ', exp_config, ' and ', server_config, ' ------')

        # experiment starts, we dont know where the code shall run
        # => read the configuration file

        # copy the config files to this folder
        this_dir = '/'.join(__file__.split('/')[:-1])
        try:
            shutil.copyfile('config/'+server_config, this_dir+'/server_config.py')
        except shutil.SameFileError:
            pass
        try:
            shutil.copyfile('config/'+exp_config, this_dir+'/exp_config.py')
        except shutil.SameFileError:
            pass

        sys.path.append(this_dir)
        from server_config import cluster
        self.cluster = cluster
        from exp_config import exp
        self.exp = exp

        copy_dartwrf_to_archive()  # includes config files

        # we set the path from where python should import dartwrf modules
        self.cluster.python = 'export PYTHONPATH='+self.cluster.scripts_rundir+'; '+self.cluster.python

        # Set paths and backup scripts
        self.cluster.log_dir = self.cluster.archivedir+'/logs/'
        print('logging to', self.cluster.log_dir)

        if self.cluster.use_slurm:
            self.cluster.slurm_scripts_dir = self.cluster.archivedir+'/slurm-scripts/'
            print('SLURM scripts will be in', self.cluster.slurm_scripts_dir)

        # copy obs kind def to config, we will read a table from there
        # file needs to exist within package so sphinx can read it
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

        _dict_to_py(_obskind_read(), self.cluster.scripts_rundir+'/obskind.py')
        
        # probably not needed
        # shutil.copy('config/'+server_config, 'config/cluster.py')  # whatever server, the config name is always the same!
        print('------ dartwrf experiment initialized ------')
        print('--------------------------------------------')
        
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
    for ((n=1; n<="""+str(self.exp.n_ens)+"""; n++))
    do
        rundir="""+self.cluster.wrf_rundir_base+'/'+self.exp.expname+"""/$n
        mv $rundir/rsl.out.0000 $rundir/rsl.out.input
    done
    """
        id = self.cluster.run_job(cmd, "ideal-"+self.exp.expname, cfg_update={"ntasks": str(self.exp.n_ens),
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

        id = self.cluster.run_job(cmd, "ins_wbub-"+self.exp.expname, cfg_update={"time": "5"}, depends_on=[depends_on])
        return id

    def run_ENS(self, begin, end, depends_on=None, first_minute=False, 
                input_is_restart=True, output_restart_interval=720):
        """Run the forecast ensemble

        Args:
            begin (datetime): start time of the forecast
            end (datetime): end time of the forecast
            depends_on (str, optional): job ID of a previous job after which to run this job
            first_minute (bool, optional): if True, run the first minute of the forecast
            input_is_restart (bool, optional): if True, start WRF from WRFrst file (restart mode)
            output_restart_interval (int, optional): interval in minutes between output of WRFrst files

        Returns:
            str: job ID of the submitted job
        """

        def prepare_WRF_inputfiles(begin, end, hist_interval=5, radt=5, output_restart_interval=False, depends_on=None):
            
            args = [self.cluster.python, self.cluster.scripts_rundir+'/prepare_namelist.py',
                    begin.strftime('%Y-%m-%d_%H:%M'), end.strftime('%Y-%m-%d_%H:%M'),
                    str(hist_interval), '--radt='+str(radt), '--restart='+restart_flag,]
            if output_restart_interval:
                args.append('--restart_interval='+str(int(float(output_restart_interval))))

            return self.cluster.run_job(' '.join(args), "preWRF", cfg_update=dict(time="2"), depends_on=[depends_on])
        

        id = depends_on
        restart_flag = '.false.' if not input_is_restart else '.true.'
        wrf_cmd = script_to_str(self.cluster.run_WRF
                ).replace('<exp.expname>', self.exp.expname
                ).replace('<cluster.wrf_rundir_base>', self.cluster.wrf_rundir_base
                ).replace('<cluster.wrf_modules>', self.cluster.wrf_modules)


        # first minute forecast (needed for validating a radiance assimilation)
        if first_minute:
            id = prepare_WRF_inputfiles(begin, begin+dt.timedelta(minutes=1), 
                    hist_interval=1,  # to get an output after 1 minute
                    radt=1,  # to get a cloud fraction CFRAC after 1 minute
                    output_restart_interval=output_restart_interval, depends_on=id)

            id = self.cluster.run_job(wrf_cmd, "WRF-"+self.exp.expname, 
                                      cfg_update={"array": "1-"+str(self.cluster.size_jobarray), "ntasks": "10", "nodes": "1",
                                                  "time": "10", "mem": "40G"}, 
                                      depends_on=[id])

        # forecast for the whole forecast duration       
        id = prepare_WRF_inputfiles(begin, end, output_restart_interval=output_restart_interval, depends_on=id)
        time_in_simulation_hours = (end-begin).total_seconds()/3600
        runtime_wallclock_mins_expected = int(8+time_in_simulation_hours*9)  # usually below 9 min/hour
        id = self.cluster.run_job(wrf_cmd, "WRF-"+self.exp.expname, 
                            cfg_update={"array": "1-"+str(self.cluster.size_jobarray), "ntasks": "10", "nodes": "1",
                                        "time": str(runtime_wallclock_mins_expected), "mem": "40G"}, 
                            depends_on=[id])
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

        cmd = (self.cluster.python+' '+self.cluster.scripts_rundir+'/assim_synth_obs.py '
                +assim_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_init_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_valid_time.strftime('%Y-%m-%d_%H:%M ')
                +prior_path_exp)

        id = self.cluster.run_job(cmd, "Assim-"+self.exp.expname, cfg_update={"ntasks": "12", "time": "60",
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
        id = self.cluster.run_job(cmd, "IC-prior-"+self.exp.expname, cfg_update=dict(time="8"), depends_on=[depends_on])
        return id


    def update_IC_from_DA(self, assim_time, depends_on=None):
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/update_IC.py '+assim_time.strftime('%Y-%m-%d_%H:%M')
        id = self.cluster.run_job(cmd, "IC-update-"+self.exp.expname, cfg_update=dict(time="8"), depends_on=[depends_on])
        return id


    def create_satimages(self, init_time, depends_on=None):
        cmd = 'module purge; module load netcdf-fortran/4.5.3-gcc-8.5.0-qsqbozc; python ~/RTTOV-WRF/run_init.py '+self.cluster.archivedir+init_time.strftime('/%Y-%m-%d_%H:%M/')
        id = self.cluster.run_job(cmd, "RTTOV-"+self.exp.expname, cfg_update={"ntasks": "12", "time": "120", "mem": "200G"}, depends_on=[depends_on])
        return id


    def gen_obsseq(self, depends_on=None):
        cmd = self.cluster.python+' '+self.cluster.scripts_rundir+'/obsseq_to_netcdf.py'
        id = self.cluster.run_job("obsseq_netcdf", cfg_update={"time": "10", "mail-type": "FAIL,END"}, 
                depends_on=[depends_on])
        return id


    def verify_sat(self, depends_on=None):
        cmd = self.cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py '+self.exp.expname+' has_node sat verif1d FSS BS'

        self.cluster.run_job(cmd, "verif-SAT-"+self.exp.expname, 
                        cfg_update={"time": "60", "mail-type": "FAIL,END", "ntasks": "15", 
                                    "ntasks-per-node": "15", "ntasks-per-core": "1", "mem": "100G",}, depends_on=[depends_on])

    def verify_wrf(self, depends_on=None):
        cmd = self.cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_from_raw/analyze_fc.py '+self.exp.expname+' has_node wrf verif1d FSS BS'
        
        self.cluster.run_job(cmd, "verif-WRF-"+self.exp.expname, 
                        cfg_update={"time": "120", "mail-type": "FAIL,END", "ntasks": "15", 
                                    "ntasks-per-node": "15", "ntasks-per-core": "1", "mem": "180G"}, depends_on=[depends_on])

    def verify_fast(self, depends_on=None):
        cmd = self.cluster.python_verif+' /jetfs/home/lkugler/osse_analysis/plot_fast/plot_single_exp.py '+self.exp.expname

        self.cluster.run_job(cmd, "verif-fast-"+self.exp.expname, 
                        cfg_update={"time": "10", "mail-type": "FAIL", "ntasks": "1",
                                    "ntasks-per-node": "1", "ntasks-per-core": "1"}, depends_on=[depends_on])
