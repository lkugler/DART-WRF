import os, sys, glob

def listdir_dirs(path):
    return [a for a in os.listdir(path) if os.path.isdir(os.path.join(path, a))]

#sys.path.append('')
from config.cfg import exp, cluster
import run_obs_diag as rod

#sys.path.append('/home/fs71386/lkugler/DART-WRF/scripts')
#from obs import read_dartobs as rdo

if __name__ == '__main__':

    datadir = cluster.archive_base
    ddir = datadir+exp.expname+'/obs_seq_final/'

    for dir_name in listdir_dirs(ddir):
        files = sorted(glob.glob(ddir+'/'+dir_name+'/*.final'))  
        #rod.run_obsdiag(files, f_out=ddir+'/obsdiag_'+dir_name+'.nc') 
        rod.run_obs_seq_to_netcdf(files, f_out=ddir+'/obs_epoch-'+dir_name+'.nc') 

    ddir = datadir+exp.expname+'/obs_seq_final_1min/'

    for dir_name in listdir_dirs(ddir):
        files = sorted(glob.glob(ddir+'/'+dir_name+'/*.final'))
        rod.run_obs_seq_to_netcdf(files, f_out=ddir+'/obs_epoch-'+dir_name+'.nc') 
