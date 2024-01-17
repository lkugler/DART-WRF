from dartwrf.utils import Experiment

exp = Experiment()
exp.expname = "exp_test"
exp.model_dx = 2000
exp.n_ens = 4
exp.do_quality_control = False

# path to the nature run, where we take observations from
#exp.nature_wrfout_pattern = '/jetfs/home/lkugler/data/sim_archive/exp_v1.18_P1_nature+1/*/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'
#exp.nature_wrfout_pattern = '/jetfs/home/lkugler/data/sim_archive/exp_v1.18_P1_nature/*/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'
exp.nature_wrfout_pattern = '/jetfs/home/lkugler/data/sim_archive/exp_v1.19_P3_wbub7_nat/*/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'

exp.input_profile = '/mnt/jetfs/home/lkugler/data/initial_profiles/wrf/ens/2022-03-31/raso.fc.<iens>.wrfprof'


exp.dart_nml = {'&assim_tools_nml':
                    dict(filter_kind='1',
                        sampling_error_correction='.true.',
                        # obs_impact_filename='/jetfs/home/lkugler/DART-WRF/templates/impactfactor_T.txt',
                        ),
                '&filter_nml':
                    dict(   ens_size=exp.n_ens,
                            num_output_state_members=exp.n_ens,
                            num_output_obs_members=exp.n_ens,
                            inf_flavor=['0', '4'],
                            inf_initial=[1.04, 0.5],
                            inf_initial_from_restart='.false.',
                            output_members='.true.',
                            output_mean='.true.',
                            output_sd='.true.',
                            stages_to_write='output',
                        ),
                '&quality_control_nml':
                    dict(outlier_threshold='-1',
                        ),
                '&obs_def_radar_mod_nml':
                    dict(apply_ref_limit_to_obs      =  '.true.',
                         reflectivity_limit_obs      =  5.0,
                         lowest_reflectivity_obs     =  5.0,
                         apply_ref_limit_to_fwd_op   =  '.true.',
                         reflectivity_limit_fwd_op   =  5.0,
                         lowest_reflectivity_fwd_op  =  5.0,
                         microphysics_type           =  '5',
                         ),
                '&location_nml':
                    dict(horiz_dist_only='.false.',
                        ),
                '&model_nml':
                    dict(wrf_state_variables = 
                        [['U',     'QTY_U_WIND_COMPONENT',     'TYPE_U',    'UPDATE','999',],
                         ['V',     'QTY_V_WIND_COMPONENT',     'TYPE_V',    'UPDATE','999',],
                         ['W',     'QTY_VERTICAL_VELOCITY',    'TYPE_W',    'UPDATE','999',],
                         ['PH',    'QTY_GEOPOTENTIAL_HEIGHT',  'TYPE_GZ',   'UPDATE','999',],
                         ['THM',   'QTY_POTENTIAL_TEMPERATURE','TYPE_T',    'UPDATE','999',],
                         ['MU',    'QTY_PRESSURE',             'TYPE_MU',   'UPDATE','999',],

                         ['QVAPOR','QTY_VAPOR_MIXING_RATIO',   'TYPE_QV',   'UPDATE','999',],
                         ['QCLOUD','QTY_CLOUDWATER_MIXING_RATIO','TYPE_QC', 'UPDATE','999',],
                         ['QICE',  'QTY_ICE_MIXING_RATIO',     'TYPE_QI',   'UPDATE','999',],
                        #  ['QRAIN','QTY_RAINWATER_MIXING_RATIO','TYPE_QR', 'UPDATE','999',],
                        #  ['QSNOW','QTY_SNOW_MIXING_RATIO','TYPE_QS', 'UPDATE','999',],
                        #  ['QGRAUP','QTY_GRAUPEL_MIXING_RATIO','TYPE_QG', 'UPDATE','999',],

                         ['CLDFRA','QTY_CLOUD_FRACTION',       'TYPE_CFRAC','UPDATE','999',],
                         ['PSFC',  'QTY_SURFACE_PRESSURE',     'TYPE_PSFC', 'UPDATE','999',],
                         ['T2',    'QTY_2M_TEMPERATURE',       'TYPE_T',    'UPDATE','999',],
                         ['TSK',   'QTY_SKIN_TEMPERATURE',     'TYPE_T',    'UPDATE','999',],
                         ['REFL_10CM','QTY_RADAR_REFLECTIVITY','TYPE_REFL', 'UPDATE','999',]],
                         
                        wrf_state_bounds = 
                        [['QVAPOR','0.0','NULL','CLAMP'],
                         ['QCLOUD','0.0','NULL','CLAMP'],
                         ['QICE','0.0','NULL','CLAMP'],
                         ['CLDFRA','0.0','1.0','CLAMP'],
                         
                        #  ['QRAIN','0.0','NULL','CLAMP'],
                        #  ['QSNOW','0.0','NULL','CLAMP'],
                        #  ['QGRAUP','0.0','NULL','CLAMP'],
                         ],
                        ),
                '&ensemble_manager_nml':
                   dict(layout = 1,
                        tasks_per_node = 12,
                        communication_configuration = 1,
                        ),
                }



# n_obs can be 22500: 2km, 5776: 4km, 121: 30km, 256:16x16 (20km); 961: 10km resoltn 
# if radar: then n_obs is for each observation height level
oeinf = 4.**.5

vis = dict(var_name='VIS 0.6µm', unit='[1]',
           kind='MSG_4_SEVIRI_BDRF', sat_channel=1, 
           n_obs=961, obs_locations='square_array_evenly_on_grid',
           # n_obs=1, obs_locations=[(44.141, -0.99)],
           error_generate=0.03, error_assimilate=0.03*oeinf,
           loc_horiz_km=20, 
           #height=4000, loc_vert_km=3
           )

wv73 = dict(var_name='Brightness temperature WV 7.3µm', unit='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=6, 
            n_obs=961, obs_locations='square_array_evenly_on_grid',
            error_generate=1, error_assimilate=1*oeinf, 
            loc_horiz_km=20, 
            #height=7000, loc_vert_km=3
            )

wv62 = dict(var_name='Brightness temperature WV 6.2µm', unit='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=5, 
            n_obs=961,  obs_locations='square_array_evenly_on_grid',
            # n_obs=1, obs_locations=[(44.141, -0.99)],
            error_generate=1, error_assimilate=1*oeinf, 
            loc_horiz_km=20, 
            #height=10000, loc_vert_km=3
            )

ir108 = dict(var_name='Brightness temperature IR 10.8µm', unit='[K]',
             kind='MSG_4_SEVIRI_TB', sat_channel=9, 
             n_obs=1, obs_locations='square_array_evenly_on_grid',
             error_generate=5., error_assimilate=10.,
             loc_horiz_km=32)

radar = dict(var_name='Radar reflectivity', unit='[dBz]',
             kind='RADAR_REFLECTIVITY', 
             n_obs=961, obs_locations='square_array_evenly_on_grid',
             # n_obs=2, obs_locations=[(45.332, 0.4735), (45.332, 0.53)],
             heights=range(2000, 14001, 2000),
             error_generate=2.5, error_assimilate=2.5*oeinf,
             loc_horiz_km=20, loc_vert_km=3)

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
         loc_horiz_km=50, loc_vert_km=2.5)

t2m = dict(var_name='SYNOP Temperature', unit='[K]',
           kind='SYNOP_TEMPERATURE', 
           n_obs=256, obs_locations='square_array_evenly_on_grid',
           error_generate=0.3, error_assimilate=0.3,
           loc_horiz_km=10, loc_vert_km=2)

psfc = dict(var_name='SYNOP Pressure', unit='[Pa]',
            kind='SYNOP_SURFACE_PRESSURE', n_obs=1, 
            error_generate=50., error_assimilate=100.,
            loc_horiz_km=32, loc_vert_km=5)

exp.observations = [t]

# the variables which will be replaced in the WRF initial conditions file
exp.update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'PSFC']
#exp.update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'PSFC']
#exp.update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QRAIN', 'QSNOW', 'QGRAUP', 'PSFC']
#exp.update_vars = ['QVAPOR', 'QCLOUD', 'QICE', 'PSFC']

exp.use_existing_obsseq = False
# exp.use_existing_obsseq='/jetfs/home/lkugler/data/sim_archive/exp_v1.22_P2_rr_WV73_obs10_loc20_oe1/obs_seq_out/%Y-%m-%d_%H:%M_obs_seq.out'




