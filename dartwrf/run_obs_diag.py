import os, sys, shutil, glob

from config.cfg import exp, cluster
from utils import symlink, copy, sed_inplace, append_file, shell

rundir_program = '/home/fs71386/lkugler/data/run_DART/'

def prepare(obserr_iszero='.true.'):
    copy(cluster.scriptsdir+'/../templates/input.eval.nml',
            rundir_program+'/input.nml')
    sed_inplace(rundir_program+'/input.nml', '<n_ens>', str(int(exp.n_ens)))
    sed_inplace(rundir_program+'/input.nml', '<zero_error_obs>', obserr_iszero)
    sed_inplace(rundir_program+'/input.nml', '<horiz_dist_only>', '.false.')  # dummy
    sed_inplace(rundir_program+'/input.nml', '<vert_norm_hgt>', '5000.0')  # dummy
    
    append_file(rundir_program+'/input.nml', cluster.scriptsdir+'/../templates/obs_def_rttov.VIS.nml')


def write_input_filelist(filepaths):
    fpath = rundir_program+'/obsdiag_inputlist.txt'
    print('writing', fpath)
    if os.path.exists(fpath):
        os.remove(fpath)

    with open(fpath, 'w') as f:
        for fin in filepaths:
            f.write(fin)
            f.write('\n')


def run_obsdiag(filepaths, f_out='./obsdiag.nc'):
    write_input_filelist(filepaths)

    for obserr_iszero in ['.true.', '.false.']:
        prepare(obserr_iszero=obserr_iszero)

        # run_allinoneplace obs_diag
        print('------ running obs_diag program')
        os.chdir(rundir_program)
        symlink(cluster.dart_srcdir+'/obs_diag', rundir_program+'/obs_diag')
        shell(cluster.container, './obs_diag >& obs_diag.log')  # caution, this overwrites obs_seq_to_netcdf

        # move output to archive
        #outdir = os.path.dirname(f_out)  #'/'.join(folder_obs_seq_final.split('/')[:-1])
        if obserr_iszero == '.true.':
            fout = f_out[:-3]+'_wrt_truth.nc'   
        elif obserr_iszero == '.false.':
            fout = f_out[:-3]+'_wrt_obs.nc' 
        shutil.move(rundir_program+'/obs_diag_output.nc', fout)
        print(fout, 'saved.')


def run_obs_seq_to_netcdf(filepaths, f_out='./obs_epoch.nc'):

    write_input_filelist(filepaths)
    print('------ running obs_seq_to_netcdf program')
    #shutil.copy(cluster.dart_srcdir+'/obs_seq_to_netcdf-bak', rundir_program+'/obs_seq_to_netcdf')
    os.chdir(rundir_program)
    shell(cluster.container, './obs_seq_to_netcdf  >& obs_seq_to_netcdf.log')  # caution, overwrites its own binary?!
    shutil.move(rundir_program+'/obs_epoch_001.nc', f_out)
    print(f_out, 'saved.')


if __name__ == '__main__':
    #folder_obs_seq_final = '/home/fs71386/lkugler/data/DART-WRF/rundir/test' 
    print('python run_obs_diag.py ')
    folder_obs_seq_final = str(sys.argv[1])
    files = sorted(glob.glob(folder_obs_seq_final+'/*.final'))  # input for obs_diag program
    
    run_obsdiag(files, f_out='./test.nc')  # input must be files with posterior data!!
    run_obs_seq_to_netcdf(files, outdir=folder_obs_seq_final)  # input can be files without posterior data
