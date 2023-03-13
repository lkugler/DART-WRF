import os, sys, glob, warnings

from config.cfg import exp
from config.cluster import cluster
import dartwrf.run_obs_diag as rod

def listdir_dirs(path):
    return [a for a in os.listdir(path) if os.path.isdir(os.path.join(path, a))]

if __name__ == '__main__':

    datadir = cluster.archive_base
    #expname = 'exp_v1.16_Pwbub-1_Radar_soe2' 
    expname = exp.expname
    ddir = datadir+expname+'/obs_seq_final/'

    files = sorted(glob.glob(ddir+'/*.final')) 
    rod.run_obsdiag(files, f_out=ddir+'/obsdiag.nc')
    rod.run_obs_seq_to_netcdf(files, f_out=ddir+'/obs_epoch.nc') 

    ddir = datadir+expname+'/obs_seq_final_1min/'
    files = sorted(glob.glob(ddir+'/*.final'))
    try:
        rod.run_obs_seq_to_netcdf(files, f_out=ddir+'/obs_epoch.nc') 
    except Exception as e:
        warnings.warn(str(e))
