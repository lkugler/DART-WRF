import os, sys, shutil
import datetime as dt
import numpy as np
from scipy.interpolate import interp1d

from config.cfg import exp, cluster
from utils import symlink, copy, mkdir, sed_inplace, append_file
import create_obsseq as osq
from gen_synth_obs import read_prior_obs, set_input_nml
import pre_assim

def run_operator(time):
    """
    time_for_dart (dt.datetime) : needs to be consistent with wrfout files!
    """

    # assume only 1 obstype for now
    obscfg = exp.observations[0]

    # get observation file (obs not important, but their locations)
    # this should correspond to configuration to have same locations as in real assim
    obs_seq_all_out = cluster.dartrundir + '/obs_seq_all.out'
    os.chdir(cluster.dartrundir)
    n_obs = obscfg['n_obs']
    error_var = (obscfg['err_std'])**2
    sat_channel = obscfg.get('channel', False)
    cov_loc = obscfg['cov_loc_radius_km']
    dist_obs = obscfg.get('distance_between_obs_km', False)
    obs_coords = osq.calc_obs_locations(n_obs, coords_from_domaincenter=False, 
                                        distance_between_obs_km=dist_obs, 
                                        fpath_obs_locations=None)
    osq.sat(time, sat_channel, obs_coords, error_var,
            output_path=cluster.dartrundir)
    assert os.path.exists(cluster.dartrundir + '/obs_seq.in')

    # prepare dummy nature
    os.system('cp ./advance_temp1/wrfout_d01 ./wrfout_d01')
    import wrfout_add_geo
    wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', 
                        cluster.dartrundir+'/wrfout_d01')

    print('running perfect model obs', flush=True)
    os.system('mpirun -np 12 ./perfect_model_obs')

    # set namelist for filter (calc only forward op)
    set_input_nml(sat_channel=obscfg.get('channel', False),
                  just_prior_values=True)

    # run filter
    os.system('mv obs_seq.out obs_seq_all.out')
    assert os.path.exists(obs_seq_all_out)
    print('running filter', flush=True)
    os.system('mpirun -np 40 ./filter')

    # copy output to archive
    savedir = cluster.archivedir()+'/obs_seq_final_1min/'
    mkdir(savedir)
    copy(cluster.dartrundir+'/obs_seq.final', 
         savedir+time.strftime('/%Y-%m-%d_%H:%M_obs_seq.final'))


if __name__ == '__main__':
    prev_forecast_init = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    time_to_run_fw_op = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
    exppath_firstguess = cluster.archivedir()
    print(prev_forecast_init, time_to_run_fw_op)

    # link ensemble states to run_DART directory
    pre_assim.run(time_to_run_fw_op, prev_forecast_init, exppath_firstguess)

    # run fwd operator, save to archive
    run_operator(time_to_run_fw_op)
