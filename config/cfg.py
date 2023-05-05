from dartwrf import utils

exp = utils.Experiment()
exp.expname = "test_newcode"
exp.model_dx = 2000
exp.n_ens = 40
exp.superob_km = False  # False or int (spatial averaging of observations)

exp.use_existing_obsseq = False  # False or pathname (use precomputed obs_seq.out files)
#exp.use_existing_obsseq = '/users/students/lehre/advDA_s2023/dartwrf_tutorial/very_cold_observation.out'

# path to the nature run, where we take observations from
exp.nature_wrfout = '/mnt/jetfs/scratch/lkugler/data/sim_archive/exp_v1.18_P1_nature/2008-07-30_06:00/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'

exp.input_profile = '/mnt/jetfs/home/lkugler/data/initial_profiles/wrf/ens/2022-03-31/raso.fc.<iens>.wrfprof'


exp.dart_nml = {'&assim_tools_nml':
                    dict(assim_tools_nml='.false.',
                            filter_kind='1',
                            sampling_error_correction='.true.',
                            # obs_impact_filename='/jetfs/home/lkugler/DART-WRF/templates/impactfactor_T.txt',
                            ),
                '&filter_nml':
                    dict(ens_size=str(exp.n_ens),
                            num_output_state_members=str(exp.n_ens),
                            num_output_obs_members=str(exp.n_ens),
                            inf_flavor=['2', '0'],
                        ),
                '&location_nml':
                    dict(horiz_dist_only='.true.',
                        ),
                }


# n_obs can be 22500: 2km, 5776: 4km, 121: 30km, 256:16x16 (20km); 961: 10km resoltn 
# if radar: then n_obs is for each observation height level

vis = dict(var_name='VIS 0.6µm', unit='[1]',
           kind='MSG_4_SEVIRI_BDRF', sat_channel=1, 
           n_obs=961, obs_locations='square_array_evenly_on_grid',
           # n_obs=1, obs_locations=[(44.141, -0.99)],
           error_generate=0.03, error_assimilate=0.03,
           loc_horiz_km=20)

wv62 = dict(var_name='Brightness temperature WV 6.2µm', unit='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=5, 
            n_obs=961,  obs_locations='square_array_evenly_on_grid',
            error_generate=1., error_assimilate=2., 
            loc_horiz_km=20)

wv73 = dict(var_name='Brightness temperature WV 7.3µm', unit='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=6, 
            n_obs=961, obs_locations='square_array_evenly_on_grid',
            error_generate=1., error_assimilate=3., 
            loc_horiz_km=20)

ir108 = dict(var_name='Brightness temperature IR 10.8µm', unit='[K]',
             kind='MSG_4_SEVIRI_TB', sat_channel=9, 
             n_obs=1, obs_locations='square_array_evenly_on_grid',
             error_generate=5., error_assimilate=10.,
             loc_horiz_km=32)

radar = dict(var_name='Radar reflectivity', unit='[dBz]',
             kind='RADAR_REFLECTIVITY', 
             n_obs=5776, obs_locations='square_array_evenly_on_grid',
             error_generate=2.5, error_assimilate=2.5,
             heights=range(2000, 14001, 2000),
             loc_horiz_km=20, loc_vert_km=2.5)

t = dict(var_name='Temperature', unit='[K]',
         kind='RADIOSONDE_TEMPERATURE', 
         #n_obs=22500, obs_locations='square_array_evenly_on_grid',
         n_obs=1, obs_locations=[(45., 0.)],
         error_generate=0.2, error_assimilate=0.2,
         heights=[1000,], #range(1000, 17001, 2000),
         loc_horiz_km=50, loc_vert_km=2.5)

q = dict(var_name='Specific humidity', unit='[kg/kg]',
         kind='RADIOSONDE_SPECIFIC_HUMIDITY', n_obs=1,
         error_generate=0., error_assimilate=5*1e-5,
         heights=[1000], #range(1000, 17001, 2000),
         loc_horiz_km=0.1, loc_vert_km=2.5)

t2m = dict(var_name='SYNOP Temperature', unit='[K]',
           kind='SYNOP_TEMPERATURE', n_obs=1, 
           error_generate=0.1, error_assimilate=0.1,
           loc_horiz_km=40, loc_vert_km=2.5)

psfc = dict(var_name='SYNOP Pressure', unit='[Pa]',
            kind='SYNOP_SURFACE_PRESSURE', n_obs=1, 
            error_generate=50., error_assimilate=100.,
            loc_horiz_km=32, loc_vert_km=5)

exp.observations = [vis]
exp.update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'PSFC']


