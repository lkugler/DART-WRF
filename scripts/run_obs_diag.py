import os, sys, shutil, glob
from config.cfg import exp, cluster
from utils import symlink, copy, sed_inplace, append_file

def run(folder_obs_seq_final):
    rundir_program = '/home/fs71386/lkugler/data/DART-WRF/rundir/'

    files = sorted(glob.glob(folder_obs_seq_final+'/*.final'))  # input for obs_diag program
    fpath = rundir_program+'/obsdiag_inputlist.txt'
    print('writing', fpath)

    if os.path.exists(fpath):
        os.remove(fpath)

    with open(fpath, 'w') as f:
        for fin in files:
            f.write(fin)
            f.write('\n')


    print('ensure correct input.nml')
    copy(cluster.scriptsdir+'/../templates/input.nml',
         rundir_program+'/input.nml') #cluster.dartrundir+'/input.nml')
    sed_inplace(rundir_program+'/input.nml', '<n_ens>', str(int(exp.n_ens)))
    append_file(rundir_program+'/input.nml', cluster.scriptsdir+'/../templates/obs_def_rttov.VIS.nml')

    # run obs_diag
    print('running obs_diag program')
    os.chdir(rundir_program)
    symlink(cluster.dart_srcdir+'/obs_diag', rundir_program+'/obs_diag')
    os.system('./obs_diag >& obs_diag.log')

    outdir = '/'.join(folder_obs_seq_final.split('/')[:-1])
    print('moving output to', outdir+'/obs_diag_output.nc')
    copy(rundir_program+'/obs_diag_output.nc', outdir+'/obs_diag_output.nc')

    print('running obs_seq_to_netcdf program')
    symlink(cluster.dart_srcdir+'/obs_seq_to_netcdf', rundir_program+'/obs_seq_to_netcdf')
    os.system('./obs_seq_to_netcdf  >& obs_seq_to_netcdf.log')
    print('moving output to', outdir+'/obs_seq_output.nc')
    copy(rundir_program+'/obs_diag_output.nc', outdir+'/obs_seq_output.nc')


if __name__ == '__main__':
    folder_obs_seq_final = '/home/fs71386/lkugler/data/sim_archive/exp_v1.11_LMU_filter_domainobs/obs_seq_final/'
    run(folder_obs_seq_final)
