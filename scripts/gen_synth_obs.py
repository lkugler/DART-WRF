import os, sys, shutil
import datetime as dt
import numpy as np
from scipy.interpolate import interp1d
from config.cfg import exp, cluster
from utils import symlink, copy, sed_inplace, append_file
import create_obsseq as osq

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

def edit_obserr_in_obsseq(fpath_obsseqin, OEs):
    """
    overwrite observation errors in a obs_seq.out file
    according to the values in OEs
    """
    # write to txt (write whole obs_seq.out again)
    obsseq = open(fpath_obsseqin, 'r').readlines()
    obsseq_new = obsseq.copy()
    i_obs = 0
    for i, line in enumerate(obsseq):
        if 'kind\n' in line:
            i_line_oe = i+9  # 9 for satellite obs
            obsseq_new[i_line_oe] = ' '+str(OEs[i_obs])+'   \n'
            i_obs += 1

    os.rename(fpath_obsseqin, fpath_obsseqin+'-bak')  # backup
    # write cloud dependent errors (actually whole file)
    with open(fpath_obsseqin, 'w') as f:
        for line in obsseq_new:
            f.write(line)


def set_input_nml(sat_channel=False, just_prior_values=False,
                  cov_loc_radius_km=32, cov_loc_vert_km=False):
    """descr"""
    cov_loc_radian = cov_loc_radius_km/earth_radius_km
    
    if just_prior_values:
        template = cluster.scriptsdir+'/../templates/input.prioronly.nml'
    else:
        template = cluster.scriptsdir+'/../templates/input.nml'
    copy(template, cluster.dartrundir+'/input.nml')

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
        if sat_channel in [1, 2, 3, 12]:
            rttov_nml = cluster.scriptsdir+'/../templates/obs_def_rttov.VIS.nml'
        else:
            rttov_nml = cluster.scriptsdir+'/../templates/obs_def_rttov.IR.nml'
        append_file(cluster.dartrundir+'/input.nml', rttov_nml)


if __name__ == "__main__":

    time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    fpath_obs_coords = cluster.archivedir()+time.strftime('/%Y-%m-%d_%H:%M/obs_coords.pkl')

    # remove any existing observation files
    os.chdir(cluster.dartrundir); os.system('rm -f obs_seq_*.out obs_seq.in obs_seq.final')

    # loop over observation types
    for i_obs, obscfg in enumerate(exp.observations):

        n_obs = obscfg['n_obs']
        error_var = (obscfg['err_std'])**2
        sat_channel = obscfg.get('channel', False)
        cov_loc = obscfg['cov_loc_radius_km']
        dist_obs = obscfg.get('distance_between_obs_km', False)
        cov_loc_vert_km = obscfg.get('cov_loc_vert_km', False)

        # generate obs_seq.in
        obs_coords = osq.calc_obs_locations(n_obs, coords_from_domaincenter=False, 
                                            distance_between_obs_km=dist_obs, 
                                            fpath_obs_locations=fpath_obs_coords)

        if obscfg['sat']:
            osq.sat(time, sat_channel, obs_coords, error_var,
                    output_path=cluster.dartrundir)
        else:
            osq.generic_obs(obscfg['kind'], time, obs_coords, error_var,
                            output_path=cluster.dartrundir)

        if not os.path.exists(cluster.dartrundir+'/obs_seq.in'):
            raise RuntimeError('obs_seq.in does not exist in '+cluster.dartrundir)

        # generate observations (obs_seq.out)
        set_input_nml(sat_channel=sat_channel,
                      cov_loc_radius_km=cov_loc,
                      cov_loc_vert_km=cov_loc_vert_km)
        os.chdir(cluster.dartrundir)
        t = dt.datetime.now()
        os.system('mpirun -np 12 ./perfect_model_obs')
        print('1st perfect_model_obs', (dt.datetime.now()-t).total_seconds())

        # cloud dependent observation error
        if obscfg['sat']:
            if sat_channel == 6:
                # run ./filter to have prior observation estimates from model state
                set_input_nml(sat_channel=sat_channel,
                              just_prior_values=True)
                t = dt.datetime.now()
                os.system('mv obs_seq.out obs_seq_all.out; mpirun -np 20 ./filter')
                print('1st filter', (dt.datetime.now()-t).total_seconds())

                # find the observation error for a pair of (H(x_nature), H(x_background))
                f_obs_prior = cluster.dartrundir+'/obs_seq.final'
                OBSs = read_prior_obs(f_obs_prior)

                # compute the observation error necessary
                # to achieve a certain operational FGD distribution
                OEs = []
                for obs in OBSs:
                    bt_y = obs['truth']
                    bt_x_ens = obs['prior_ens']
                    CIs = [cloudimpact_73(bt_x, bt_y) for bt_x in bt_x_ens]

                    oe_nature = oe_73(np.mean(CIs))
                    OEs.append(oe_nature)

                # write obs_seq.out
                fpath_obsseqout = cluster.dartrundir+'/obs_seq.in'
                edit_obserr_in_obsseq(fpath_obsseqout, OEs)

                # generate actual observations (with correct error)
                os.chdir(cluster.dartrundir)
                t = dt.datetime.now()
                os.system('mpirun -np 12 ./perfect_model_obs')
                print('real obs gen', (dt.datetime.now()-t).total_seconds())

                # correct input.nml for actual assimilation later on
                set_input_nml(sat_channel=sat_channel,
                              cov_loc_radius_km=cov_loc,
                              cov_loc_vert_km=cov_loc_vert_km)

        # rename according to i_obs
        os.rename(cluster.dartrundir+'/obs_seq.out', 
                  cluster.dartrundir+'/obs_seq_'+str(i_obs)+'.out')

    # concatenate the created obs_seq_*.out files
    os.chdir(cluster.dartrundir)
    os.system('cat obs_seq_*.out >> obs_seq_all.out')

    print(dt.datetime.now())
