import os, sys, shutil, glob, warnings
import builtins as __builtin__
import subprocess
import datetime as dt
import re, tempfile

# class Stage(object):
#     """Collection of variables describing the assimilation stage"""
#     def __init__(self, **kwargs):
#         self.superob_km = False  # False or int (spatial averaging of observations)
#         self.use_existing_obsseq = False  # False or pathname (use precomputed obs_seq.out files)
#         self.__dict__.update(kwargs)

#         # raise ValueError if attributes are not set
#         needed_attributes = ['observations', 'dart_nml',]
#         for attr in needed_attributes:
#             if not hasattr(self, attr):
#                 raise ValueError('Stage.'+attr+' is not set')

class Experiment(object):
    """Collection of variables which define the experiment
    
    Attributes:
        expname (str): Name of the experiment
        model_dx (int): WRF grid spacing in meters
        n_ens (int): Ensemble size
        do_quality_control (bool): If True, activate "quality control" function in assim_synth_obs.py
        
        nature_wrfout_pattern (str): Path to the nature run, where we take observations from; 
            the path can contain wildcards (*,?), e.g. '/jetfs/exp1/*/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'
        input_profile (str): Path to WRF idealized input profiles; 
            e.g. '/data/initial_profiles/wrf/ens/raso.fc.<iens>.wrfprof';
            <iens> is replaced by 001-040 for a 40-member ensemble
        
        update_vars (list of str): Variables which will be updated after assimilation (update_IC.py)
            e.g. ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR',]
            
        observations (list of dict): Dictionaries which define an observation;
            keys: 
            `error_generate`: measurement error standard-deviation;
            `error_assimilate`: assigned observation error std-dev;
            `heights`: list of integers at which observations are taken;
            `loc_horiz_km`: float of horizontal localization half-width in km;
            `loc_vert_km`: float of vertical localization half-width in km;
        
        use_existing_obsseq (str, False): Path to existing obs_seq.out file (False: generate new one);
            time string is replaced by actual time: /path/%Y-%m-%d_%H:%M_obs_seq.out
        
        dart_nml (dict): updates to the default input.nml of DART (in dart_srcdir)
            keys are namelist section headers (e.g. &filter_nml)
            values are dictionaries of parameters and values (e.g. dict(ens_size=exp.n_ens,))

    """
    def __init__(self):
        pass

class ClusterConfig(object):
    """Collection of variables regarding the cluster configuration
    
    Configuration name docs

    When coding, use configuration settings like this:
    $ from exp_config import exp
    $ from cluster_config import cluster
    $ path = cluster.archivedir

    Attributes:
        name (str): Name of the cluster
        max_nproc (int): Maximum number of processors that can be used
        np_WRF (int): Number of cores for WRF (mpirun -np xx ./wrf.exe)
        use_slurm (bool): If True, use SLURM to submit jobs
        size_WRF_jobarray (int): Size of SLURM job array for running the WRF ensemble

        python (str): Path to python executable
        python_verif (str): Path to python executable for verification
        ncks (str): Path to ncks executable
        ideal (str): Path to ideal.exe
        wrfexe (str): Path to wrf.exe

        dart_modules (str): Command to load modules before running DART 
        wrf_modules (str): Command to load modules before running WRF

        wrf_rundir_base (str): Path to temporary files for WRF
        dart_rundir_base (str): Path to temporary files for DART
        archive_base (str): Path to long-time output storage

        srcdir (str): Path to where WRF has been compiled, including the 'run' folder of WRF, e.g. /home/WRF-4.3/run
        dart_srcdir (str): Path to DART compile directory, e.g. /home/DART-9.11.9/models/wrf/work
        rttov_srcdir (str): Path to RTTOV compile directory, e.g. /home/RTTOV13/rtcoef_rttov13/
        dartwrf_dir (str): Path where DART-WRF scripts reside, e.g. /home/DART-WRF/

        geo_em_for_WRF_ideal (str, False): Path to the geo_em.d01.nc file for idealized nature runs
        obs_impact_filename
        namelist (str): Path to a WRF namelist template; 
                        strings like <hist_interval>, will be overwritten in scripts/prepare_namelist.py
        run_WRF (str): Path to script which runs WRF on a node of the cluster

        slurm_cfg (dict):   Dictionary containing the default configuration of SLURM
                            as defined in SLURM docs (https://slurm.schedmd.com/sbatch.html).
                            This configuration can be customized for any job (e.g. in workflows.py)

    """
    def __init__(self, exp):
        self.exp = exp  # makes derived properties available

        # defaults
        self.dart_modules = ''
        self.wrf_modules = '' 
        self.size_jobarray = '1'

    @property
    def archivedir(self):
        """Path to the directory where data for the experiment is stored
        
        Example:
            `/users/abcd/data/sim_archive/experiment1/`
        """
        return self.archive_base+'/'+self.exp.expname+'/'

    @property
    def scripts_rundir(self):
        """Path to the directory where the DART-WRF scripts are executed

        Note:
            If you want to execute scripts from the folder where you develop code, use `self.dartwrf_dir` (not sure if this works)
            If you want to execute the code from a different place ('research'), then use `self.archivedir+'/DART-WRF/'`
        
        Example:
            `/user/data/sim_archive/DART-WRF/dartwrf/`
        """
        return self.archivedir+'/DART-WRF/dartwrf/'

    @property
    def dart_rundir(self):
        """Path to the directory where DART programs will run
        Includes the experiment name
        """
        return self.dart_rundir_base+'/'+self.exp.expname+'/'

    def wrf_rundir(self, iens):
        """Path to the directory where an ensemble member will run WRF
        Includes the experiment name and the ensemble member index
        """
        return self.wrf_rundir_base+'/'+self.exp.expname+'/'+str(iens)+'/'

    def run_job(self, cmd, jobname='', cfg_update=dict(), depends_on=None):
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
            return Slurm(jobname, slurm_kwargs=dict(self.slurm_cfg, **cfg_update), 
                  log_dir=self.log_dir, 
                  scripts_dir=self.slurm_scripts_dir,
                  ).run(cmd, depends_on=depends_on)
        else:
            print(cmd)
            returncode = os.system(cmd)
            if returncode != 0:
                raise Exception('Error running command >>> '+cmd)

userhome = os.path.expanduser('~')

def shell(args):
    print(args)
    #subprocess.run(args.split(' ')) #, shell=True) #, stderr=subprocess.STDOUT) 
    return os.system(args)

def print(*args):
    __builtin__.print(*args, flush=True)

def copy(src, dst, remove_if_exists=True):
    if src == dst:
        return  # the link already exists, nothing to do
    if remove_if_exists:
        try:
            os.remove(dst)
        except:
            pass
    shutil.copy(src, dst)

def try_remove(f):
    try:
        os.remove(f)
    except:
        pass

def mkdir(path):
    os.system('mkdir -p '+path)

def script_to_str(path):
    return open(path, 'r').read()

def copy_contents(src, dst):
    os.system('cp -rf '+src+'/* '+dst+'/')

def clean_wrfdir(dir):
    for s in ['wrfout_*', 'rsl.*', 'wrfrst_*']:
        for f in glob.glob(dir+'/'+s):
            os.remove(f)

def symlink(src, dst):
    """Create a symbolic link from src to dst
    """
    try:
        os.symlink(src, dst)
    except FileExistsError:
        # print('file exists')
        if os.path.realpath(dst) == src:
            pass  # print('link is correct')
        else:
            os.remove(dst)
            os.symlink(src, dst)
    except Exception as e:
        raise e

def link_contents(src, dst):
    """Create symbolic links for all files in src to dst
    
    Args:
        src (str): Path to source directory
        dst (str): Path to destination directory
        
    Returns:
        None
    """
    for f in os.listdir(src):
        symlink(src+'/'+f, dst+'/'+f)

def sed_inplace(filename, pattern, repl):
    '''Perform the pure-Python equivalent of in-place `sed` substitution
    Like `sed -i -e 's/'${pattern}'/'${repl}' "${filename}"`.

    Args:
        filename (str):  path to file
        pattern (str): string that will be replaced
        repl (str): what shall be written instead of pattern?

    Example:
        sed_inplace('namelist.input', '<dx>', str(int(exp.model_dx)))

    Returns:
        None
    '''
    # For efficiency, precompile the passed regular expression.
    pattern_compiled = re.compile(pattern)

    # For portability, NamedTemporaryFile() defaults to mode "w+b" (i.e., binary
    # writing with updating). This is usually a good thing. In this case,
    # however, binary writing imposes non-trivial encoding constraints trivially
    # resolved by switching to text writing. Let's do that.
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
        with open(filename) as src_file:
            for line in src_file:
                tmp_file.write(pattern_compiled.sub(repl, line))

    # Overwrite the original file with the munged temporary file in a
    # manner preserving file attributes (e.g., permissions).
    shutil.copystat(filename, tmp_file.name)
    shutil.move(tmp_file.name, filename)

def append_file(f_main, f_gets_appended):
    """Append the contents of one file to another

    Args:
        f_main (str): Path to file that will be appended
        f_gets_appended (str): Path to file that will be appended to f_main

    Returns:
        None
    """
    rc = os.system('cat '+f_gets_appended+' >> '+f_main)
    if rc != 0:
        raise RuntimeError('cat '+f_gets_appended+' >> '+f_main)

def write_txt(lines, fpath):
    """Write a list of strings to a text file
    
    Args:
        lines (list): List of strings
        fpath (str): Path to file
        
    Returns:
        None
    """
    try_remove(fpath)
    with open(fpath, "w") as file:
        for line in lines:
            file.write(line+'\n')
