import os, sys, shutil
import datetime as dt
import numpy as np
from scipy.interpolate import interp1d

from config.cfg import exp, cluster
from utils import symlink, copy, mkdir, sed_inplace, append_file, print
import create_obsseq as osq
import assim_synth_obs as aso
from assim_synth_obs import read_prior_obs, set_DART_nml, generate_observations, assimilate
import pre_assim

def run_operator(obscfg, time):
    """
    time_for_dart (dt.datetime) : needs to be consistent with wrfout files!
    """

    # get observation file (obs not important, but their locations)
    # this should correspond to configuration to have same locations as in real assim
    os.chdir(cluster.dartrundir)

    n_obs = obscfg['n_obs']
    error_var = (obscfg['err_std'])**2
    sat_channel = obscfg.get('sat_channel', False)
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

    print('running perfect model obs')
    os.system('mpirun -np 12 ./perfect_model_obs')

    # set namelist for filter (calc only forward op)
    aso.set_DART_nml(sat_channel=sat_channel,
                  just_prior_values=True)

    # run filter
    assert os.path.exists(cluster.dartrundir+'/obs_seq.out')
    print('running filter')
    os.system('mpirun -np 40 ./filter')

    # copy output to archive
    savedir = cluster.archivedir()+'/obs_seq_final_1min/'
    mkdir(savedir)
    obsname = obscfg['kind']
    
    copy(cluster.dartrundir+'/obs_seq.final', savedir+fout)
    print('output of observation operator saved to', fout)


if __name__ == '__main__':
    prev_forecast_init = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
    exppath_firstguess = cluster.archivedir()
    print(prev_forecast_init, time)

    # link ensemble states to run_DART directory
    pre_assim.run(time, prev_forecast_init, exppath_firstguess)

    savedir = cluster.archivedir()+'/obs_seq_final_1min/'
    mkdir(savedir)

    n_stages = len(exp.observations)
    for istage, obscfg in enumerate(exp.observations):

        kind = obscfg['kind']
        n_obs = obscfg['n_obs']
        sat_channel = obscfg.get('sat_channel', False)
        obscfg['folder_obs_coords'] = False

        aso.set_DART_nml(sat_channel=sat_channel, 
                     cov_loc_radius_km=obscfg['cov_loc_radius_km'],
                     cov_loc_vert_km=obscfg.get('cov_loc_vert_km', False), 
                     just_prior_values=True)

        osq.create_obsseq_in(time, obscfg)
        aso.generate_observations()
        aso.assimilate()

        archive_stage = savedir+kind
        aso.archive_diagnostics(archive_stage, time.strftime('/%Y-%m-%d_%H:%M_obs_seq.final'))

