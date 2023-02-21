import os, sys, shutil, glob, warnings
import builtins as __builtin__
import subprocess
import datetime as dt
import re, tempfile
import importlib

class Experiment(object):
    """Collection of variables regarding the experiment configuration"""
    def __init__(self):
        pass

class ClusterConfig(object):
    """Collection of variables regarding the cluster configuration"""
    def __init__(self, exp):
        self.exp = exp

    @property
    def archivedir(self):
        """Path to the directory where data for the experiment is stored
        
        Example:
            `/users/abcd/data/sim_archive/experiment1/`
        """
        return self.archive_base+'/'+self.exp.expname

    @property
    def scripts_rundir(self):
        """Path to the directory where the DART-WRF scripts are executed
        
        Example:
            `/user/data/sim_archive/DART-WRF/`
        """
        return self.archivedir+'/DART-WRF/'

    @property
    def dartrundir(self):
        """Path to the directory where DART programs will run
        Includes the experiment name
        """
        return self.dart_rundir_base+'/'+self.exp.expname+'/'

    def wrf_rundir(self, iens):
        """Path to the directory where an ensemble member will run WRF
        Includes the experiment name and the ensemble member index
        """
        return self.wrf_rundir_base+'/'+self.exp.expname+'/'+str(iens)

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
            Slurm(jobname, slurm_kwargs=dict(self.slurm_cfg, **cfg_update), 
                  log_dir=self.log_dir, 
                  scripts_dir=self.slurm_scripts_dir, 
                  **kwargs
                  ).run(cmd, depends_on=depends_on)
        else:
            print(cmd)
            os.system(cmd)

def shell(args):
    print(args)
    #subprocess.run(args.split(' ')) #, shell=True) #, stderr=subprocess.STDOUT) 
    os.system(args)

def print(*args):
    __builtin__.print(*args, flush=True)

def copy(src, dst, remove_if_exists=True):
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
    # Create a symbolic link pointing to src named dst.
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
    for f in os.listdir(src):
        symlink(src+'/'+f, dst+'/'+f)

def copy_scp_srvx8(src, dst):
    os.system('scp '+src+' a1254888@srvx8.img.univie.ac.at:'+dst)

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
    os.system('cat '+f_gets_appended+' >> '+f_main)