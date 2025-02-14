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
from pprint import pprint
import datetime as dt
import re
import tempfile
import pickle
import importlib.util
import random
import string
import pickle

userhome = os.path.expanduser('~')

def import_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec) # type: ignore
    sys.modules[module_name] = module
    spec.loader.exec_module(module) # type: ignore
    return module

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

        # Important directory paths
        dir_archive: e.g. '/jetfs/home/lkugler/data/sim_archive/<exp>/'
        dir_wrf_run: e.g. '/jetfs/home/lkugler/data/run_WRF/<exp>/<ens>/'
        dir_dart_run: e.g. '/jetfs/home/lkugler/data/run_DART/<exp>/'

    """

    def __init__(self, 
                 name: str, 
                 model_dx: int, 
                 ensemble_size: int, 

                 # cluster config
                 max_nproc: int = 20, 
                 max_nproc_for_each_ensemble_member: int = 9,
                 dir_archive: str = './sim_archive/<exp>/',
                 dir_wrf_run: str = './run_WRF/<exp>/<ens>/',
                 dir_dart_run: str = './run_DART/<exp>/',
                 use_slurm: bool = False,
                 pattern_obs_seq_out: str = './diagnostics/%Y-%m-%d_%H:%M_obs_seq.out',
                 pattern_obs_seq_final: str = './diagnostics/%Y-%m-%d_%H:%M_obs_seq.final',
                 
                 # optional
                 update_vars: list=[], 
                 dart_nml: dict={}, 
                 use_existing_obsseq: bool | str = False,
                 nature_wrfout_pattern: bool | str = False,
                 
                 # others
                 **kwargs):
        
        # defining the compulsory variables
        self.name = name
        self.model_dx = model_dx
        self.ensemble_size = int(ensemble_size)
        self.update_vars = update_vars
        self.dart_nml = dart_nml
        
        # cluster config
        self.max_nproc = max_nproc
        self.max_nproc_for_each_ensemble_member = max_nproc_for_each_ensemble_member
        self.dir_archive = dir_archive.replace('<exp>', self.name)
        self.dir_wrf_run = dir_wrf_run.replace('<exp>', self.name)
        self.dir_dart_run = dir_dart_run.replace('<exp>', self.name)
        
        # defaults
        # these are overwritten with choices in **kwargs
        self.debug = False
        self.dart_modules = ''
        self.wrf_modules = ''
        self.size_jobarray = '1'
        self.use_slurm = use_slurm
        self.slurm_cfg = {}
        self.python = 'python'
        self.pattern_obs_seq_out = pattern_obs_seq_out.replace('<archivedir>', self.dir_archive)
        self.pattern_obs_seq_final = pattern_obs_seq_final.replace('<archivedir>', self.dir_archive)
        
        # optional
        self.use_existing_obsseq = use_existing_obsseq
        self.nature_wrfout_pattern = nature_wrfout_pattern

        # user defined
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        # warnings to the user
        if not update_vars:
            warnings.warn('No `update_vars` defined, not updating any variables after assimilation!')
            
        if not dart_nml:
            warnings.warn('No `dart_nml` defined, using default DART namelist!')
            
        if not isinstance(use_existing_obsseq, str):
            if use_existing_obsseq != False:
                raise ValueError('`use_existing_obsseq` must be a string or False, but is', use_existing_obsseq)
        
        if isinstance(use_existing_obsseq, str):
            print('Using existing observation sequence', use_existing_obsseq)

        # required attributes, derived from others
        self.dir_archive = self.dir_archive.replace('<exp>', self.name)
        self.dir_dartwrf_run = self.dir_archive+'/DART-WRF/dartwrf/'
        self.dir_slurm = self.dir_archive+'/slurm-scripts/'
        self.dir_log = self.dir_archive+'/logs/'

        # save config
        self.f_cfg_base = self.dir_archive + '/configs/'
        
        # write config to file
        self.f_cfg_current = self.generate_name()
        self.to_file(self.f_cfg_current)
        
    def __contains__(self, key):
        return hasattr(self, key)
    
    def __getattribute__(self, name: str):
        """Ask user if the attribute was defined in the first place"""
        try:
            return super().__getattribute__(name)
        except AttributeError:
            raise AttributeError(f'Attribute `{name}` not found in Config object. Did you set it?')

    def generate_name(self):
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return self.f_cfg_base+'/cfg_'+random_str+'.pkl'

    def update(self, **kwargs):
        """Update the configuration with new values
        """
        # d = read_Config_as_dict(self.f_cfg_current)
        if 'name' in kwargs:
            raise ValueError('You can not change the name of the experiment!')
        
        # set attributes in existing object
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        # write to file
        self.f_cfg_current = self.generate_name()
        self.to_file(self.f_cfg_current)
    
    @staticmethod
    def from_file(fname: str) -> 'Config':
        """Read a configuration from a file"""
        d = read_Config_as_dict(fname)
        return Config(**d)

    def to_file(self, filename: str):
        """Write itself to a python file"""
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        d = self.__dict__
        
        with open(filename, 'wb') as handle:
            pickle.dump(d, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
        if self.debug:
            print('Wrote config to', filename)


def read_Config_as_dict(filename: str) -> dict:
    """Read a dictionary from a python file,
    return as Config object
    """
    with open(filename, 'rb') as handle:
        d = pickle.load(handle)
    print('read config', filename)
    return d

def display_config(filename: str) -> None:
    d = read_Config_as_dict(filename)
    pprint(d)

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

def obskind_read(dart_srcdir: str) -> dict:
    """Read dictionary of observation types + ID numbers ("kind") 
    from DART f90 script and return it as python dictionary
    """
    definitionfile = dart_srcdir + \
        '/../../../assimilation_code/modules/observations/obs_kind_mod.f90'
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