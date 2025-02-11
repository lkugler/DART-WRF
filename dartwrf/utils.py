"""Utility functions for DART-WRF

Caution: You can not use the configuration files in here, 
because loading this would lead to a circular import.
"""

import os
import sys
import shutil
import glob
import warnings
import builtins as __builtin__
import subprocess
import datetime as dt
import re
import tempfile
import pickle
import importlib.util

userhome = os.path.expanduser('~')

def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec) # type: ignore
    sys.modules[module_name] = module
    spec.loader.exec_module(module) # type: ignore
    return module

class ClusterConfig(object):
    """Collection of variables regarding the cluster configuration

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

        srcdir (str): Path to where WRF has been compiled, including the 'run' folder of WRF, e.g. /home/WRF-4.3/run
        dart_srcdir (str): Path to DART compile directory, e.g. /home/DART-9.11.9/models/wrf/work
        rttov_srcdir (str): Path to RTTOV compile directory, e.g. /home/RTTOV13/rtcoef_rttov13/
        dartwrf_dir (str): Path where DART-WRF scripts reside, e.g. /home/DART-WRF/

        geo_em_nature (str, False): Path to the geo_em.d01.nc file for idealized nature runs
        geo_em_forecast (str, False): Path to the geo_em.d01.nc file for the forecast domain
        obs_impact_filename
        namelist (str): Path to a WRF namelist template; 
                        strings like <hist_interval>, will be overwritten in scripts/prepare_namelist.py
        run_WRF (str): Path to script which runs WRF on a node of the cluster

        slurm_cfg (dict):   Dictionary containing the default configuration of SLURM
                            as defined in SLURM docs (https://slurm.schedmd.com/sbatch.html).
                            This configuration can be customized for any job (e.g. in workflows.py)

    """

    def __init__(self, 
                 max_nproc: int, 
                 max_nproc_for_each_ensemble_member: int,
                 WRF_ideal_template: str, 
                 WRF_exe_template: str, 
                 archive_base: str,
                 wrf_rundir_base: str,
                 dart_rundir_base: str,
                 dartwrf_dir_dev: str,
                 WRF_namelist_template: str,
                 **kwargs):
        # defaults
        # these are overwritten with choices in **kwargs
        self.dart_modules = ''
        self.wrf_modules = ''
        self.size_jobarray = '1'
        self.use_slurm = False
        self.slurm_cfg = {}
        self.log_dir = './'
        self.slurm_scripts_dir = './'
        self.archive_base = archive_base
        self.wrf_rundir_base = wrf_rundir_base        
        self.dart_rundir_base = dart_rundir_base
        self.dartwrf_dir_dev = dartwrf_dir_dev
        self.WRF_namelist_template = WRF_namelist_template
        self.python = 'python'
        self.pattern_obs_seq_out = '<archivedir>/diagnostics/%Y-%m-%d_%H:%M_obs_seq.out'
        self.pattern_obs_seq_final = '<archivedir>/diagnostics/%Y-%m-%d_%H:%M_obs_seq.final'
        
        self.max_nproc = max_nproc
        self.max_nproc_for_each_ensemble_member = max_nproc_for_each_ensemble_member
        self.WRF_ideal_template = WRF_ideal_template
        self.WRF_exe_template = WRF_exe_template
        
        # user defined
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return f'ClusterConfig: {self.__dict__}'

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


class Config(object):
    """Collection of variables which define the experiment

    Attributes:
        expname (str): Name of the experiment
        model_dx (int): WRF grid spacing in meters
        ensemble_size (int): Ensemble size

        nature_wrfout_pattern (str): Path to the nature run WRF files, where can be generated from; 
            the path can contain wildcards (*,?), e.g. '/jetfs/exp1/*/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'
        
        input_profile (str): Path to sounding profiles as initial condition (see WRF ideal guide)
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
            values are dictionaries of parameters and values (e.g. dict(ens_size=exp.ensemble_size,))

        wrf_rundir_base (str): Path to temporary files for WRF
        dart_rundir_base (str): Path to temporary files for DART
        archive_base (str): Path to long-time output storage

    """

    def __init__(self, name: str, model_dx: int, ensemble_size: int, 
                 update_vars: list=[], dart_nml: dict={}, 
                 use_existing_obsseq: bool | str = False,
                 input_profile: bool | str = False,
                 nature_wrfout_pattern: bool | str = False,
                 **kwargs):
        
        # defining the compulsory variables
        self.name = name
        self.model_dx = model_dx
        self.ensemble_size = ensemble_size
        self.update_vars = update_vars
        self.dart_nml = dart_nml
        
        # optional
        self.use_existing_obsseq = use_existing_obsseq
        self.input_profile = input_profile
        self.nature_wrfout_pattern = nature_wrfout_pattern
        
        if not update_vars:
            warnings.warn('No `update_vars` defined, not updating any variables after assimilation!')
            
        if not dart_nml:
            warnings.warn('No `dart_nml` defined, using default DART namelist!')
            
        if not isinstance(use_existing_obsseq, str):
            if use_existing_obsseq != False:
                raise ValueError('`use_existing_obsseq` must be a string or False, but is', use_existing_obsseq)
        
        if isinstance(use_existing_obsseq, str):
            print('Using existing observation sequence', use_existing_obsseq)

        # user defined
        for key, value in kwargs.items():
            setattr(self, key, value)



def write_dict_to_pyfile(d: dict, filename: str):
    """Write a dictionary to a python file"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as f:
        for key, value in d.items():
            f.write(key+' = '+str(value)+'\n')

def read_dict_from_pyfile(filename: str) -> Config:
    """Read a dictionary from a python file,
    return as Config object
    """
    with open(filename, 'r') as f:
        d = {}
        for line in f:
            key, value = line.split('=')
            d[key.strip()] = value.strip()
    return Config(**d)


def shell(args, pythonpath=None):
    print(args)
    os.system(args)
    # if pythonpath:
    #     env = os.environ.copy()
    #     env['PYTHONPATH'] = pythonpath
    #     subprocess.check_output(args.split(' '), env=env)
    # else:
    #     subprocess.check_output(args.split(' '))


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
    Creates the folder if it does not exist
    """
    try:  # this file may not exist
        os.remove(dst)
    except OSError:
        pass

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    os.symlink(src, dst)


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


def save_dict(dictionary, fpath):
    with open(fpath, 'wb') as f:
        pickle.dump(dictionary, f)


def load_dict(fpath):
    with open(fpath, 'rb') as f:
        return pickle.load(f)
