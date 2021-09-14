import os, sys, shutil, warnings
import time as time_module
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

def read_truth_obs_obsseq(f):
    """Reads observed and true values from obs_seq.out/final files."""
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

def replace_errors_obsseqout(f, new_errors):
    """Replaces existing observation errors in obs_seq.final files
    
    new_errors (np.array) : standard deviation,
                            shape must match the number of observations
    """
    debug = True
    obsseq = open(f, 'r').readlines()

    # find number of lines between two ' OBS   ' lines:
    first_obs = None
    for i, line in enumerate(obsseq):
        if ' OBS ' in line:
            if first_obs is None:
                first_obs = i
            else:
                second_obs = i
                break
    lines_between = second_obs - first_obs
    lines_obserr_after_obsnr = lines_between - 1  # obserr line is one before ' OBS   ' line

    # replace values in list obsseq
    i_obs = 0
    for i, line in enumerate(obsseq):
        if ' OBS ' in line:
            line_error_obs_i = i+lines_obserr_after_obsnr

            previous_err_var = obsseq[line_error_obs_i]
            new_err_obs_i = new_errors[i_obs]**2  # variance in obs_seq.out
            if debug: print('previous err var ', previous_err_var, 'new error', new_err_obs_i)
            obsseq[line_error_obs_i] = ' '+str(new_err_obs_i)+' \n'

            i_obs += 1  # next iteration

    with open(f, 'w') as file:
        for line in obsseq:
            file.write(line)
    print('replaced obs errors in', f)


def set_DART_nml_singleobstype(sat_channel=False, cov_loc_radius_km=32, cov_loc_vert_km=False,
                 just_prior_values=False):
    cov_loc_radian = cov_loc_radius_km/earth_radius_km
    
    if just_prior_values:
        template = cluster.scriptsdir+'/../templates/input.eval.nml'
    else:
        template = cluster.scriptsdir+'/../templates/input.nml'
    copy(template, cluster.dartrundir+'/input.nml')

    # options are overwritten with settings
    options = {'<n_ens>': str(int(exp.n_ens)),
               '<cov_loc_radian>': str(cov_loc_radian)}

    if cov_loc_vert_km:
        vert_norm_rad = earth_radius_km*cov_loc_vert_km/cov_loc_radius_km*1000
        options['<horiz_dist_only>'] = '.false.'
        options['<vert_norm_hgt>'] = str(vert_norm_rad)
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

def set_DART_nml(cov_loc_radius_km=32, cov_loc_vert_km=False, just_prior_values=False):
    cov_loc_radian = cov_loc_radius_km/earth_radius_km
    
    if just_prior_values:
        template = cluster.scriptsdir+'/../templates/input.eval.nml'
    else:
        template = cluster.scriptsdir+'/../templates/input.nml'
    copy(template, cluster.dartrundir+'/input.nml')

    # options keys are replaced in input.nml with values
    options = {'<n_ens>': str(int(exp.n_ens)),
               '<cov_loc_radian>': str(cov_loc_radian)}

    if cov_loc_vert_km:
        vert_norm_rad = earth_radius_km*cov_loc_vert_km/cov_loc_radius_km*1000
        options['<horiz_dist_only>'] = '.false.'
        options['<vert_norm_hgt>'] = str(vert_norm_rad)
    else:
        options['<horiz_dist_only>'] = '.true.'
        options['<vert_norm_hgt>'] = '50000.0'  # dummy value

    for key, value in options.items():
        sed_inplace(cluster.dartrundir+'/input.nml', key, value)

    # input.nml for RTTOV
    rttov_nml = cluster.scriptsdir+'/../templates/obs_def_rttov.VIS.nml'
    append_file(cluster.dartrundir+'/input.nml', rttov_nml)


def obs_operator_ensemble(istage):
    # assumes that prior ensemble is already linked to advance_temp<i>/wrfout_d01
    print('running obs operator on ensemble forecast')
    os.chdir(cluster.dartrundir)

    list_ensemble_truths = []
    t = time_module.time()

    for iens in range(1, exp.n_ens+1):
        print('observation operator for ens #'+str(iens))
        # ens members are already linked to advance_temp<i>/wrfout_d01
        copy(cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01',
                cluster.dartrundir+'/wrfout_d01')
        # DART may need a wrfinput file as well, which serves as a template for dimension sizes
        symlink(cluster.dartrundir+'/wrfout_d01', cluster.dartrundir+'/wrfinput_d01')
        
        # I dont think this is necessary, we do this already in pre_assim.py
        # add geodata, if istage>0, wrfout is DART output (has coords)
        #if istage == 0:
        #    wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', cluster.dartrundir+'/wrfout_d01')

        # run perfect_model obs (forward operator)
        os.system('mpirun -np 12 ./perfect_model_obs > /dev/null')

        # truth values in obs_seq.out are H(x) values
        true, _ = read_truth_obs_obsseq(cluster.dartrundir+'/obs_seq.out')
        list_ensemble_truths.append(true)
    
    print('obs operator ensemble took', int(time_module.time()-t), 'seconds')
    n_obs = len(list_ensemble_truths[0])
    np_array = np.full((exp.n_ens, n_obs), np.nan)
    for i in range(exp.n_ens):
        np_array[i, :] = list_ensemble_truths[i]
    return np_array

def obs_operator_nature(time):
    print('getting true values in obs space from nature run')
    prepare_nature_dart(time)
    run_perfect_model_obs()
    true, _ = read_truth_obs_obsseq(cluster.dartrundir+'/obs_seq.out')
    return true


def link_nature_to_dart_truth(time):
    # get wrfout_d01 from nature run
    shutil.copy(time.strftime(cluster.nature_wrfout),
                cluster.dartrundir+'/wrfout_d01')
    # DART may need a wrfinput file as well, which serves as a template for dimension sizes
    symlink(cluster.dartrundir+'/wrfout_d01', cluster.dartrundir+'/wrfinput_d01')
    print('linked', time.strftime(cluster.nature_wrfout), 'to', cluster.dartrundir+'/wrfout_d01')


def prepare_nature_dart(time):
    print('linking nature to DART & georeferencing')
    link_nature_to_dart_truth(time)
    wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', cluster.dartrundir+'/wrfout_d01')


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

def run_perfect_model_obs():
    print('generating observations - running ./perfect_model_obs')
    os.chdir(cluster.dartrundir)
    try_remove(cluster.dartrundir+'/obs_seq.out')
    if not os.path.exists(cluster.dartrundir+'/obs_seq.in'):
        raise RuntimeError('obs_seq.in does not exist in '+cluster.dartrundir)
    os.system('mpirun -np 12 ./perfect_model_obs > log.perfect_model_obs')
    if not os.path.exists(cluster.dartrundir+'/obs_seq.out'):
        raise RuntimeError('obs_seq.out does not exist in '+cluster.dartrundir, 
                           '\n look for '+cluster.dartrundir+'/log.perfect_model_obs')

def assimilate(nproc=96):
    print('time now', dt.datetime.now())
    print('running filter')
    os.chdir(cluster.dartrundir)
    try_remove(cluster.dartrundir+'/obs_seq.final')
    t = time_module.time()
    os.system('mpirun -genv I_MPI_PIN_PROCESSOR_LIST=0-'+str(int(nproc)-1)+' -np '+str(int(nproc))+' ./filter > log.filter')
    print('./filter took', int(time_module.time()-t), 'seconds')

def recycle_output():
    """Use output of assimilation (./filter) as input for another assimilation (with ./filter)
    Specifically, this copies the state fields from filter_restart_d01.000x to the wrfout files in advance_temp folders"""
    update_vars = ['U', 'V', 'T', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QRAIN', 'U10', 'V10', 'T2', 'Q2', 'TSK', 'PSFC', 'CLDFRA']
    updates = ','.join(update_vars)

    print('recycle DART output to be used as input')
    for iens in range(1, exp.n_ens+1):
        dart_output = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
        dart_input = cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01'

        #print('check for non-monotonic vertical pressure')

        # convert link to file in order to be able to update the content
        if os.path.islink(dart_input):
            l = os.readlink(dart_input)
            os.remove(dart_input)
            copy(l, dart_input) 

        # print('move DART output to input: '+dart_output+' -> '+dart_input)
        # os.rename(dart_output, dart_input)  # probably doesnt work

        print('updating', updates, 'in', dart_input, 'from', dart_output)
        os.system(cluster.ncks+' -A -v '+updates+' '+dart_output+' '+dart_input)

############### archiving

def archive_assimilation(time)

    print('archive obs space diagnostics')
    archive_dir = cluster.archivedir+'/obs_seq_final/'
    mkdir(archive_dir)
    fout = archive_dir+time.strftime('/%Y-%m-%d_%H:%M_obs_seq.final')
    copy(cluster.dartrundir+'/obs_seq.final', fout)
    print(fout, 'saved.')

    # try:  # what are regression diagnostics?!
    #     print('archive regression diagnostics')
    #     copy(cluster.dartrundir+'/reg_diagnostics', archive_dir+'/reg_diagnostics')
    # except Exception as e:
    #     warnings.warn(str(e))

    print('archiving output')
    archive_assim = cluster.archivedir + '/assim_stage0/'
    mkdir(archive_assim)
    copy(cluster.dartrundir+'/input.nml', archive_assim+'/input.nml')

    for iens in range(1, exp.n_ens+1):  # single members
        filter_out = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
        copy(filter_out, archive_assim+'/filter_restart_d01.'+str(iens).zfill(4))

    for f in ['output_mean.nc', 'output_sd.nc']:  # copy mean and sd to archive
        copy(cluster.dartrundir+'/'+f, archive_assim+'/'+f)

def archive_obs_generation(time):

    dir_obsseq = cluster.archivedir+'/obs_seq_out/'
    os.makedirs(dir_obsseq, exist_ok=True)
    copy(cluster.dartrundir+'/obs_seq.out', dir_obsseq+time.strftime('/%Y-%m-%d_%H:%M_obs_seq.out'))


if __name__ == "__main__":

    """Assimilate observations (different obs types)
    as defined in config/cfg.py
    for a certain timestamp (argument) of the nature run (defined in config/clusters.py)

    Workflow:
    for each assimilation stage (one obs_seq.in and e.g. one observation type):
    1) create obs_seq.in with obs-errors
    2) prepare nature run for DART
    3) create obs from nature (obs_seq.out)
    4) Assimilate
      - adapt obs errors for assimilation
        - calculate assim obs error from parametrization
            1) create obs_seq.in with obs error=0 
            2) calculate y_nat = H(x_nature) and y_ens = H(x_ensemble) 
            3) calculate obs error as function of y_nat, y_ensmean 
        - or get assim obs error from config
        - edit obs error in obs_seq.out
      - assimilate
      - write state to archive

    
    Assumptions:
    - x_ensemble is already linked for DART to advance_temp<iens>/wrfout_d01

    Example call:
    python assim.py 2008-08-07_12:00
    """

    time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    archive_time = cluster.archivedir+time.strftime('/%Y-%m-%d_%H:%M/')

    os.chdir(cluster.dartrundir)
    os.system('rm -f obs_seq.in obs_seq.out obs_seq.final')  # remove any existing observation files

    print('create obs_seq.in from config')
    prepare_nature_dart(time)  # link WRF files to DART directory

    ################################################
    print(' 1) get the assimilation errors in a single vector ')
    error_assimilate = []  
    # to get the obs-error for assimilation, 
    # we need to get the true obs-space values for the parametrized variable
    # and collect the obs-error for assimilation in a single vector/list

    for i, obscfg in enumerate(exp.observations):
        n_obs = obscfg['n_obs']
        n_obs_z = len(obscfg.get('heights', [1,]))
        n_obs_3d = n_obs * n_obs_z

        parametrized = obscfg.get('sat_channel') == 6

        if not parametrized:
            err_assim = np.zeros(n_obs_3d) + obscfg['error_assimilate']

        else:  # error parametrization for WV73
            # get observations for sat 6
            osq.create_obsseqin_alltypes(time, [obscfg,], np.zeros(n_obs_3d))
            run_perfect_model_obs()
            
            # depends on obs_seq.out produced before by run_perfect_model_obs()
            Hx_nat, _ = read_truth_obs_obsseq(cluster.dartrundir+'/obs_seq.out')

            Hx_prior = obs_operator_ensemble(istage)  # files are already linked to DART directory
            err_assim = calc_obserr_WV73(Hx_nat, Hx_prior)
     
        error_assimilate.extend(err_assim)  # the obs-error we assume for assimilating observations

    ################################################
    print(' 2) generate observations ')

    # the obs-error we use for generating obs is user-defined
    error_generate = []
    for i, obscfg in enumerate(exp.observations):
        error_generate.extend(np.zeros(n_obs_3d) + obscfg['error_generate'])

    osq.create_obsseqin_alltypes(time, exp.observations, obs_errors=error_generate)

    first_obstype = exp.observations[0]  # TODO: different for each observation type
    set_DART_nml(cov_loc_radius_km=first_obstype['cov_loc_radius_km'],
                 cov_loc_vert_km=first_obstype.get('cov_loc_vert_km', False))

    run_perfect_model_obs()  # actually create observations that are used to assimilate
    archive_obs_generation(time)

    ################################################
    print(' 3) assimilate with observation-errors for assimilation')

    replace_errors_obsseqout(cluster.dartrundir+'/obs_seq.out', error_assimilate)
    t = time_module.time()
    assimilate()
    print('filter took', time_module.time()-t, 'seconds')
    
    archive_assimilation(time)
