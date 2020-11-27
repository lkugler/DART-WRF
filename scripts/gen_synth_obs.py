import os, sys, shutil
import datetime as dt
import numpy as np
from scipy.interpolate import interp1d

from config.cfg import exp, cluster
from utils import symlink, copy, sed_inplace, append_file
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


def obs_operator_ensemble():
    os.chdir(cluster.dartrundir)

    if sat_channel:
        list_ensemble_truths = []

        for iens in range(1, exp.n_ens+1):
            print('observation operator for ens #'+str(iens))
            # ens members are already linked to advance_temp<i>/wrfout_d01
            copy(cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01',
                 cluster.dartrundir+'/wrfout_d01')
            
            t = dt.datetime.now()
            wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', cluster.dartrundir+'/wrfout_d01')
            print((dt.datetime.now()-t).total_seconds(), 'secs for adding geodata')

            # DART may need a wrfinput file as well, which serves as a template for dimension sizes
            symlink(cluster.dartrundir+'/wrfout_d01', cluster.dartrundir+'/wrfinput_d01')

            # run perfect_model obs (forward operator)
            os.system('mpirun -np 12 ./perfect_model_obs > /dev/null')

            # truth values in obs_seq.out are H(x) values
            vals, _ = read_obsseqout(cluster.dartrundir+'/obs_seq.out')
            list_ensemble_truths.append(vals)
        
        n_obs = len(list_ensemble_truths[0])
        np_array = np.full((exp.n_ens, n_obs), np.nan)
        for i in range(exp.n_ens):
            np_array[i, :] = list_ensemble_truths[i]
        return np_array
    else:
        raise NotImplementedError()


if __name__ == "__main__":

    time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    fpath_obs_coords = cluster.archivedir()+time.strftime('/%Y-%m-%d_%H:%M/obs_coords.pkl')

    # remove any existing observation files
    os.chdir(cluster.dartrundir); os.system('rm -f obs_seq_*.out obs_seq.in obs_seq.final')

    def prepare_nature_dart():
        # get wrfout_d01 from nature run
        shutil.copy(time.strftime(cluster.nature_wrfout),
                    cluster.dartrundir+'/wrfout_d01')

        wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', cluster.dartrundir+'/wrfout_d01')

        # DART may need a wrfinput file as well, which serves as a template for dimension sizes
        symlink(cluster.dartrundir+'/wrfout_d01', cluster.dartrundir+'/wrfinput_d01')

    prepare_nature_dart()

    # loop over observation types
    for i_obs, obscfg in enumerate(exp.observations):

        n_obs = obscfg['n_obs']
        error_var = (obscfg['err_std'])**2
        sat_channel = obscfg.get('sat_channel', False)
        cov_loc = obscfg['cov_loc_radius_km']
        dist_obs = obscfg.get('distance_between_obs_km', False)
        cov_loc_vert_km = obscfg.get('cov_loc_vert_km', False)
        heights = obscfg.get('heights', False)

        # generate obs_seq.in
        obs_coords = osq.calc_obs_locations(n_obs, coords_from_domaincenter=False, 
                                            distance_between_obs_km=dist_obs, 
                                            fpath_obs_locations=fpath_obs_coords)

        if sat_channel:
            osq.sat(time, sat_channel, obs_coords, error_var,
                    output_path=cluster.dartrundir)
        else:
            osq.generic_obs(obscfg['kind'], time, obs_coords, error_var,
                            heights=heights, 
                            output_path=cluster.dartrundir)

        if not os.path.exists(cluster.dartrundir+'/obs_seq.in'):
            raise RuntimeError('obs_seq.in does not exist in '+cluster.dartrundir)

        os.chdir(cluster.dartrundir)
        if sat_channel == 6:
            """cloud dependent observation error

            # methodologically:
            1) gen H(x_nature)
            2) gen H(x_prior)
            3) find the observation error for a pair of (H(x_nature), H(x_background))
            4) generate actual observation 
                with the observation error as function of H(x_nature) and H(x_background)

            # technically:
            4) the file 'obs_seq.in' needs to be edited to show corrected observation errors
            """
            # 1) gen H(x_nature)
            set_input_nml(sat_channel=sat_channel,
                            cov_loc_radius_km=cov_loc,
                            cov_loc_vert_km=cov_loc_vert_km)
            os.system('mpirun -np 12 ./perfect_model_obs')
            Hx_nature, _ = read_obsseqout(cluster.dartrundir+'/obs_seq.out')

            # 2) gen H(x_prior) for the whole ensemble 
            Hx_prior = obs_operator_ensemble()  # files are already linked to DART directory

            # 3) find the observation error for a pair of (H(x_nature), H(x_background))
            # necessary to achieve a certain FGD distribution which is near to operational
            n_obs = len(Hx_nature)
            OEs = []
            for iobs in range(n_obs):

                bt_y = Hx_nature[iobs]
                bt_x_ens = Hx_prior[:,iobs]
                CIs = [cloudimpact_73(bt_x, bt_y) for bt_x in bt_x_ens]
                mean_CI = np.mean(CIs)

                oe_nature = oe_73(mean_CI)
                print('oe_nature=', oe_nature, ' K')
                OEs.append(oe_nature)

            # correct obs_err in obs_seq.in (to produce actual observations later on)
            fpath_obsseqout = cluster.dartrundir+'/obs_seq.in'
            edit_obserr_in_obsseq(fpath_obsseqout, OEs)

            # ensure correct nature file linked 
            # nature should be the real nature again (was changed in the meantime)
            prepare_nature_dart()   
                
        # correct input.nml for actual assimilation later on
        set_input_nml(sat_channel=sat_channel,
                        cov_loc_radius_km=cov_loc,
                        cov_loc_vert_km=cov_loc_vert_km)

        # 4) generate actual observations (with correct error)
        os.chdir(cluster.dartrundir)
        os.system('mpirun -np 12 ./perfect_model_obs')

        # rename according to i_obs
        os.rename(cluster.dartrundir+'/obs_seq.out', 
                  cluster.dartrundir+'/obs_seq_'+str(i_obs)+'.out')

    # concatenate the created obs_seq_*.out files
    os.chdir(cluster.dartrundir)
    os.system('cat obs_seq_*.out >> obs_seq_all.out')

    print(dt.datetime.now())
