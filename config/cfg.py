from dartwrf import utils

exp = utils.Experiment()
exp.expname = "obs-T_inflation-1.1"
exp.model_dx = 2000
exp.n_ens = 10

exp.filter_kind = 1
exp.prior_inflation = 0
exp.inf_initial = 1.1
exp.post_inflation = 4
exp.sec = True
exp.cov_loc_vert_km_horiz_km = (4, 40)
exp.superob_km = False  # False or int (spatial averaging of observations)
exp.adjust_obs_impact = False

exp.use_existing_obsseq = False  # False or pathname (use precomputed obs_seq.out files)
#exp.use_existing_obsseq = '/users/students/lehre/advDA_s2023/dartwrf_tutorial/very_cold_observation.out'

# path to the nature run, where we take observations from
exp.nature = '/users/students/lehre/advDA_s2023/data/sample_nature/'

exp.input_profile = '/mnt/jetfs/home/lkugler/data/initial_profiles/wrf/ens/2022-03-31/raso.fc.<iens>.wrfprof'

# n_obs can be 22500: 2km, 5776: 4km, 121: 30km, 256:16x16 (20km); 961: 10km resoltn 
# if radar: then n_obs is for each observation height level

vis = dict(plotname='VIS 0.6µm', plotunits='[1]',
           kind='MSG_4_SEVIRI_BDRF', sat_channel=1, 
           n_obs=961, obs_locations='square_array_evenly_on_grid',
           # n_obs=1, obs_locations=[(44.141, -0.99)],
           error_generate=0.03, error_assimilate=0.03,
           cov_loc_radius_km=20)

wv62 = dict(plotname='Brightness temperature WV 6.2µm', plotunits='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=5, 
            n_obs=961,  obs_locations='square_array_evenly_on_grid',
            error_generate=1., error_assimilate=2., 
            cov_loc_radius_km=20)

wv73 = dict(plotname='Brightness temperature WV 7.3µm', plotunits='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=6, 
            n_obs=961, obs_locations='square_array_evenly_on_grid',
            error_generate=1., error_assimilate=3., 
            cov_loc_radius_km=20)

ir108 = dict(plotname='Brightness temperature IR 10.8µm', plotunits='[K]',
             kind='MSG_4_SEVIRI_TB', sat_channel=9, 
             n_obs=1, obs_locations='square_array_evenly_on_grid',
             error_generate=5., error_assimilate=10.,
             cov_loc_radius_km=32)

radar = dict(plotname='Radar reflectivity', plotunits='[dBz]',
             kind='RADAR_REFLECTIVITY', 
             n_obs=5776, obs_locations='square_array_evenly_on_grid',
             error_generate=2.5, error_assimilate=2.5,
             heights=range(2000, 14001, 2000),
             cov_loc_radius_km=1)

t = dict(plotname='Temperature', plotunits='[K]',
         kind='RADIOSONDE_TEMPERATURE', 
         n_obs=961, obs_locations='square_array_evenly_on_grid',
         #n_obs=1, obs_locations=[(45., 0.)],
         error_generate=0.2, error_assimilate=0.2,
         heights=[1000,], #range(1000, 17001, 2000),
         cov_loc_radius_km=30)

q = dict(plotname='Specific humidity', plotunits='[kg/kg]',
         kind='RADIOSONDE_SPECIFIC_HUMIDITY', n_obs=1,
         error_generate=0., error_assimilate=5*1e-5,
         heights=[1000], #range(1000, 17001, 2000),
         cov_loc_radius_km=0.1)

t2m = dict(plotname='SYNOP Temperature', plotunits='[K]',
           kind='SYNOP_TEMPERATURE', n_obs=1, 
           error_generate=0.1, error_assimilate=0.1,
           cov_loc_radius_km=40)

psfc = dict(plotname='SYNOP Pressure', plotunits='[Pa]',
            kind='SYNOP_SURFACE_PRESSURE', n_obs=1, 
            error_generate=50., error_assimilate=100.,
            cov_loc_radius_km=32)

exp.observations = [t]
exp.update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'PSFC']

