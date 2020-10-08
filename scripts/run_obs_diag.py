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
    try:
        os.remove(rundir_program+'/obs_seq_to_netcdf')
    except:
        pass
    os.system('./obs_diag >& obs_diag.log')  # caution, this overwrites obs_seq_to_netcdf

    outdir = '/'.join(folder_obs_seq_final.split('/')[:-1])
    print('moving output to', outdir+'/obs_diag_output.nc')
    copy(rundir_program+'/obs_diag_output.nc', outdir+'/obs_diag_output.nc')

    print('running obs_seq_to_netcdf program')
    shutil.copy(cluster.dart_srcdir+'/obs_seq_to_netcdf-bak', cluster.dart_srcdir+'/obs_seq_to_netcdf')
    symlink(cluster.dart_srcdir+'/obs_seq_to_netcdf', rundir_program+'/obs_seq_to_netcdf')
    os.system('./obs_seq_to_netcdf  >& obs_seq_to_netcdf.log')  # caution, overwrites its own binary?!
    print('moving output to', outdir+'/obs_seq...')
    os.system('mv '+rundir_program+'/obs_epoch_*.nc '+outdir+'/')


if __name__ == '__main__':
    #folder_obs_seq_final = '/home/fs71386/lkugler/data/sim_archive/exp_v1.11_LMU_filter2/obs_seq_final/'
    folder_obs_seq_final = str(sys.argv[1])
    run(folder_obs_seq_final)
