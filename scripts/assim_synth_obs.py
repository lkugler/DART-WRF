import os, sys, shutil
import warnings
import datetime as dt
import numpy as np
from scipy.interpolate import interp1d

from config.cfg import exp, cluster
from utils import symlink, copy, sed_inplace, append_file, mkdir, try_remove, print
import create_obsseq as osq
import wrfout_add_geo

earth_radius_km = 6370

# fit of Fig 7, Harnisch 2016
x_ci = [0,   5, 10.5, 13, 16]
y_oe = [1, 4.5,   10, 12, 13]  # Kelvin
oe_73_linear = interp1d(x_ci, y_oe, assume_sorted=True)

def oe_73(ci):
    if ci < 13:
        return oe_73_linear(ci)
    else:
        return 16.

def cloudimpact_73(bt_mod, bt_obs):
    """
    follows Harnisch 2016
    """
    biascor_obs = 0
    bt_lim = 255  # Kelvin for 7.3 micron WV channel

    ci_obs = max(0, bt_lim-(bt_obs - biascor_obs))
    ci_mod = max(0, bt_lim-bt_mod)
    ci = (ci_obs+ci_mod)/2
    return ci

def read_prior_obs(f_obs_prior):
    """
    docstring
    """
    obsseq = open(f_obs_prior, 'r').readlines()
    OBSs = []
    # read observations from obs_seq.final
    for i, line in enumerate(obsseq):
        if ' OBS ' in line:
            observed = float(obsseq[i+1].strip())
            truth = float(obsseq[i+2].strip())
            prior_ensmean = float(obsseq[i+3].strip())
            prior_enssd = float(obsseq[i+4].strip())
            prior_ens = []
            for j in range(5, 5+exp.n_ens):
                prior_ens.append(float(obsseq[i+j].strip()))

            OBSs.append(dict(observed=observed, truth=truth, prior_ens=np.array(prior_ens)))
    return OBSs

def read_obsseqout(f):
    obsseq = open(f, 'r').readlines()
    true = []
    obs = []
    # read observations from obs_seq.out
    for i, line in enumerate(obsseq):
        if ' OBS ' in line:
            observed = float(obsseq[i+1].strip())
            truth = float(obsseq[i+2].strip())
            true.append(truth)
            obs.append(observed)
    return true, obs

# def edit_obserr_in_obsseq(fpath_obsseqin, OEs):
#     """
#     overwrite observation errors in a obs_seq.out file
#     according to the values in OEs
#     """
#     # write to txt (write whole obs_seq.out again)
#     obsseq = open(fpath_obsseqin, 'r').readlines()
#     obsseq_new = obsseq.copy()
#     i_obs = 0
#     for i, line in enumerate(obsseq):
#         if 'kind\n' in line:
#             i_line_oe = i+9  # 9 for satellite obs
#             obsseq_new[i_line_oe] = ' '+str(OEs[i_obs])+'   \n'
#             i_obs += 1

#     os.rename(fpath_obsseqin, fpath_obsseqin+'-bak')  # backup
#     # write cloud dependent errors (actually whole file)
#     with open(fpath_obsseqin, 'w') as f:
#         for line in obsseq_new:
#             f.write(line)


def set_DART_nml(sat_channel=False, cov_loc_radius_km=32, cov_loc_vert_km=False,
                 just_prior_values=False):
    """descr"""
    cov_loc_radian = cov_loc_radius_km/earth_radius_km
    
    if just_prior_values:
        template = cluster.scriptsdir+'/../templates/input.prioronly.nml'
    else:
        template = cluster.scriptsdir+'/../templates/input.nml'
    copy(template, cluster.dartrundir+'/input.nml')

    # options are overwritten with settings
    options = {'<n_ens>': str(int(exp.n_ens)),
               '<cov_loc_radian>': str(cov_loc_radian)}

    if cov_loc_vert_km:
        cov_loc_vert_rad = cov_loc_vert_km*1000/cov_loc_radian
        options['<horiz_dist_only>'] = '.false.'
        options['<vert_norm_hgt>'] = str(cov_loc_vert_rad)
    else:
        options['<horiz_dist_only>'] = '.true.'
        options['<vert_norm_hgt>'] = '50000.0'  # dummy value

    for key, value in options.items():
        sed_inplace(cluster.dartrundir+'/input.nml', key, value)

    # input.nml for RTTOV
    if sat_channel > 0:
        if sat_channel in [1, 2, 3, 12]:  # VIS channels
            rttov_nml = cluster.scriptsdir+'/../templates/obs_def_rttov.VIS.nml'
        else:  # IR channels
            rttov_nml = cluster.scriptsdir+'/../templates/obs_def_rttov.IR.nml'
        append_file(cluster.dartrundir+'/input.nml', rttov_nml)
    else:
        # append any rttov segment, needs to exist anyway
        rttov_nml = cluster.scriptsdir+'/../templates/obs_def_rttov.IR.nml'
        append_file(cluster.dartrundir+'/input.nml', rttov_nml)

def obs_operator_ensemble():
    print('running obs operator on ensemble forecast')
    os.chdir(cluster.dartrundir)

    if sat_channel:
        list_ensemble_truths = []

        for iens in range(1, exp.n_ens+1):
            print('observation operator for ens #'+str(iens))
            # ens members are already linked to advance_temp<i>/wrfout_d01
            copy(cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01',
                 cluster.dartrundir+'/wrfout_d01')
            
            wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', cluster.dartrundir+'/wrfout_d01')

            # DART may need a wrfinput file as well, which serves as a template for dimension sizes
            symlink(cluster.dartrundir+'/wrfout_d01', cluster.dartrundir+'/wrfinput_d01')

            # run perfect_model obs (forward operator)
            os.system('mpirun -np 12 ./perfect_model_obs > /dev/null')

            # truth values in obs_seq.out are H(x) values
            true, _ = read_obsseqout(cluster.dartrundir+'/obs_seq.out')
            list_ensemble_truths.append(true)
        
        n_obs = len(list_ensemble_truths[0])
        np_array = np.full((exp.n_ens, n_obs), np.nan)
        for i in range(exp.n_ens):
            np_array[i, :] = list_ensemble_truths[i]
        return np_array
    else:
        raise NotImplementedError()

def obs_operator_nature():
    print('running obs operator on nature run')
    prepare_nature_dart()

    os.chdir(cluster.dartrundir)
    os.remove(cluster.dartrundir+'/obs_seq.out')
    os.system('mpirun -np 12 ./perfect_model_obs')
    true, _ = read_obsseqout(cluster.dartrundir+'/obs_seq.out')
    return true

def prepare_nature_dart():
    # get wrfout_d01 from nature run
    shutil.copy(time.strftime(cluster.nature_wrfout),
                cluster.dartrundir+'/wrfout_d01')

    wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', cluster.dartrundir+'/wrfout_d01')

    # DART may need a wrfinput file as well, which serves as a template for dimension sizes
    symlink(cluster.dartrundir+'/wrfout_d01', cluster.dartrundir+'/wrfinput_d01')

def calc_obserr_WV73(Hx_nature, Hx_prior):

    n_obs = len(Hx_nature)
    OEs = np.ones(n_obs)
    for iobs in range(n_obs):

        bt_y = Hx_nature[iobs]
        bt_x_ens = Hx_prior[:, iobs]
        CIs = [cloudimpact_73(bt_x, bt_y) for bt_x in bt_x_ens]
        mean_CI = np.mean(CIs)

        oe_nature = oe_73(mean_CI)
        print('oe_nature:', oe_nature, ', bt_y:', bt_y, ', mean_CI:', mean_CI)
        OEs[iobs] = oe_nature
    return OEs

def generate_observations():
    print('generate actual observations')
    os.chdir(cluster.dartrundir)
    try_remove(cluster.dartrundir+'/obs_seq.out')
    if not os.path.exists(cluster.dartrundir+'/obs_seq.in'):
        raise RuntimeError('obs_seq.in does not exist in '+cluster.dartrundir)
    os.system('mpirun -np 12 ./perfect_model_obs')

def assimilate():
    print('running filter')
    os.chdir(cluster.dartrundir)
    try_remove(cluster.dartrundir+'/obs_seq.final')
    if not os.path.exists(cluster.dartrundir+'/obs_seq.out'):
        raise RuntimeError('obs_seq.out does not exist in '+cluster.dartrundir)
    os.system('mpirun -np 48 ./filter')

def archive_diagnostics(archive_stage, fname_final):
    print('archive obs space diagnostics')
    mkdir(archive_stage)
    copy(cluster.dartrundir+'/obs_seq.final', archive_stage+'/'+fname_final)

    try:
        print('archive regression diagnostics')
        copy(cluster.dartrundir+'/reg_diagnostics', archive_stage+'/reg_diagnostics')
    except Exception as e:
        warnings.warn(str(e))

def recycle_output():
    print('move output to input')
    for iens in range(1, exp.n_ens+1):
        os.rename(cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4),
                  cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01')

def archive_output_mean(archive_stage):
    # for iens in range(1, exp.n_ens+1):
    #     savedir = archive_stage+'/'+str(iens)
    #     mkdir(savedir)
    #     filter_in = cluster.dartrundir+'/preassim_member_'+str(iens).zfill(4)+'.nc'
    #     filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)

    # copy mean and sd to archive
    for f in ['output_mean.nc', 'output_sd.nc']:
        copy(cluster.dartrundir+'/'+f, archive_stage+'/'+f)


if __name__ == "__main__":

    """Generate observations (obs_seq.out file)
    as defined in config/cfg.py
    for a certain timestamp (argument) of the nature run (defined in config/clusters.py)

    Workflow:
    for each assimilation stage (one obs_seq.in and e.g. one observation type):
    1) prepare nature run for DART
    optional: 2) calculate obs-error from parametrization
    3) create obs_seq.in with obs-errors from 2)
    4) generate actual observations (obs_seq.out) with obs_seq.in from 3)

    - calculate obs-error from parametrization
        1) create obs_seq.in with obs error=0
        2) calculate y_nat = H(x_nature) and y_ens = H(x_ensemble) 
        3) calculate obs error as function of y_nat, y_ensmean
    
    Assumptions:
    - x_ensemble is already linked for DART to advance_temp<iens>/wrfout_d01
    """

    time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    archive_time = cluster.archivedir()+time.strftime('/%Y-%m-%d_%H:%M/')

    os.chdir(cluster.dartrundir)
    os.system('rm -f obs_seq.in obs_seq.out obs_seq.final')  # remove any existing observation files

    n_stages = len(exp.observations)
    for istage, obscfg in enumerate(exp.observations):

        kind = obscfg['kind']
        archive_stage = archive_time + '/assim_stage'+str(istage)+'_'+kind
        n_obs = obscfg['n_obs']
        sat_channel = obscfg.get('sat_channel', False)
        obscfg['folder_obs_coords'] = archive_stage+'/obs_coords.pkl'

        set_DART_nml(sat_channel=sat_channel, 
                     cov_loc_radius_km=obscfg['cov_loc_radius_km'],
                     cov_loc_vert_km=obscfg.get('cov_loc_vert_km', False))

        use_error_parametrization = obscfg['err_std'] == False
        if use_error_parametrization:
            if sat_channel != 6:
                raise NotImplementedError('sat channel '+str(sat_channel))

            osq.create_obsseq_in(time, obscfg, zero_error=True)  # zero error to get truth vals

            Hx_nat = obs_operator_nature() 
            Hx_prior = obs_operator_ensemble()  # files are already linked to DART directory
            
            obscfg['err_std'] = calc_obserr_WV73(Hx_nat, Hx_prior)
        else:
            obscfg['err_std'] = np.ones(n_obs) * obscfg['err_std']

        osq.create_obsseq_in(time, obscfg)  # now with correct errors
        generate_observations()

        assimilate()
        archive_diagnostics(archive_stage, '/obs_seq.final')

        if istage < n_stages-1:
            # recirculation: filter output -> input
            recycle_output()
            copy(cluster.dartrundir+'/input.nml', archive_stage+'/input.nml')
            archive_output_mean(archive_stage)

        elif istage == n_stages-1:
            # last assimilation, continue integration now
            copy(cluster.dartrundir+'/input.nml', archive_stage+'/input.nml')
            pass  # call update wrfinput from filteroutput later

        else:
            RuntimeError('this should never occur?!')
