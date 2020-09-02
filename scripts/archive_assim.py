import os, sys, warnings, glob
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy_scp_srvx8, copy, mkdir, mkdir_srvx8, clean_wrfdir

# if cluster.name != 'srvx8':
#     copy = copy_scp_srvx8
#     mkdir = mkdir_srvx8

time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')

print('archive obs space diagnostics')
savedir = cluster.archivedir()+'/obs_seq_final/'
mkdir(savedir)
copy(cluster.dartrundir+'/obs_seq.final', savedir+time.strftime('/%Y-%m-%d_%H:%M_obs_seq.final'))

print('archive model state')
try:
    mkdir(cluster.archivedir())

    # copy mean and sd to archive
    for f in ['preassim_mean.nc', 'preassim_sd.nc',
              'output_mean.nc', 'output_sd.nc']:
        copy(cluster.dartrundir+'/'+f,
             cluster.archivedir()+'/'+f[:-3]+time.strftime('_%Y-%m-%d_%H:%M:%S'))

    print('copy members to archive')
    for iens in range(1, exp.n_ens+1):
        savedir = cluster.archivedir()+'/'+time.strftime('/%Y-%m-%d_%H:%M/')+str(iens)
        mkdir(savedir)

        filter_in = cluster.dartrundir+'/preassim_member_'+str(iens).zfill(4)+'.nc'
        filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)

        copy(filter_in, savedir+time.strftime('/%Y-%m-%d_%H:%M_prior'))
        copy(filter_out, savedir+time.strftime('/%Y-%m-%d_%H:%M_posterior'))

except Exception as e:
    warnings.warn(str(e))
