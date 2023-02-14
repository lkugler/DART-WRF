import os, sys, shutil, glob, warnings
import builtins as __builtin__
import subprocess
import datetime as dt

class ExperimentConfiguration(object):
    """Collection of variables to use in code later on"""
    def __init__(self):
        pass

class Shellslurm():
    """Like Slurmpy class, but runs locally"""
    def __init__(self, *args, **kwargs):
        pass
    def run(self, *args, **kwargs):
        print(args[0])
        os.system(args[0])

class ClusterConfig(object):
    """Collection of variables to use in code later on"""
    def __init__(self, exp):
        self.exp = exp
        self.set_up = False

    def setup(self):
        # Set paths and backup scripts
        self.log_dir = self.archivedir+'/logs/'
        self.slurm_scripts_dir = self.archivedir+'/slurm-scripts/'
        print('logging to', self.log_dir)
        print('scripts, which are submitted to SLURM:', self.slurm_scripts_dir)

        self.backup_scripts()
        self.set_up = True

    @property
    def archivedir(self):
        return self.archive_base+'/'+self.exp.expname

    @property
    def scripts_rundir(self):
        return self.archivedir+'/DART-WRF/'

    @property
    def dartrundir(self):
        return self.dart_rundir_base+'/'+self.exp.expname+'/'

    def wrf_rundir(self, iens):
        return self.wrf_rundir_base+'/'+self.exp.expname+'/'+str(iens)

    def create_job(self, *args, cfg_update=dict(), **kwargs):
        """Shortcut to slurmpy's class; keep certain default kwargs
        and only update some with kwarg `cfg_update`
        see https://github.com/brentp/slurmpy

        depending on cluster config : run either locally or via SLURM 
        """
        if not self.set_up:
            self.setup()

        if self.use_slurm:
            from slurmpy import Slurm
            return Slurm(*args, slurm_kwargs=dict(self.slurm_cfg, **cfg_update), 
                        log_dir=self.log_dir, 
                        scripts_dir=self.slurm_scripts_dir, 
                        **kwargs)
        else:
            return Shellslurm(*args)

    def backup_scripts(self):
        """Copies scripts and configuration to archive dir output folder"""
        os.makedirs(self.archivedir, exist_ok=True)
    
        try:
            shutil.copytree(self.scriptsdir, self.scripts_rundir)
        except FileExistsError:
            pass
        except:
            raise
        # try:
        #     copy(os.path.basename(__file__), self.scripts_rundir+'/')
        # except Exception as e:
        #     warnings.warn(str(e))
        print('scripts have been copied to', self.archivedir)

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
    import re, tempfile
    '''
    Perform the pure-Python equivalent of in-place `sed` substitution: e.g.,
    `sed -i -e 's/'${pattern}'/'${repl}' "${filename}"`.
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