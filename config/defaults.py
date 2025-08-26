
# Configuration of DART. For details see the DART or DART-WRF documentation.

dart_nml = {'&assim_tools_nml':
            dict(filter_kind='1',
                    sampling_error_correction='.true.',
                    ),
            '&filter_nml':
            dict(num_output_state_members="40",
                    num_output_obs_members="40",
                    inf_flavor=['3', '4'],
                    inf_initial=[1.05, 0.5],
                    inf_lower_bound=[.9, .9],
                    inf_upper_bound=[2., 2.],
                    inf_sd_initial=[0.3, 0.3],
                    inf_sd_lower_bound=[.6, .6],
                    inf_sd_max_change=[1.05, 1.05],
                    inf_damping=[0.9, 0.9],
                    inf_deterministic=['.true.', '.true.'],
                    inf_initial_from_restart='.false.',
                    output_members='.true.',
                    output_mean='.true.',
                    output_sd='.true.',
                    stages_to_write=['preassim', 'output',],
                    ),
            '&quality_control_nml':
                dict(outlier_threshold='5.0',
                        ),
            '&obs_def_radar_mod_nml':
                dict(apply_ref_limit_to_obs='.true.',
                        reflectivity_limit_obs=5.0,
                        lowest_reflectivity_obs=5.0,
                        apply_ref_limit_to_fwd_op='.true.',
                        reflectivity_limit_fwd_op=5.0,
                        lowest_reflectivity_fwd_op=5.0,
                        microphysics_type='5',
                        ),
            '&location_nml':
                dict(horiz_dist_only='.true.',
                        ),
            '&model_nml':
                dict(wrf_state_variables=[
                ['U',     'QTY_U_WIND_COMPONENT',  'TYPE_U',    'UPDATE', '999',],
                ['V',     'QTY_V_WIND_COMPONENT',  'TYPE_V',    'UPDATE', '999',],
                ['W',     'QTY_VERTICAL_VELOCITY', 'TYPE_W',    'UPDATE', '999',],
                ['PH',    'QTY_GEOPOTENTIAL_HEIGHT', 'TYPE_GZ',  'UPDATE', '999',],
                ['THM',   'QTY_POTENTIAL_TEMPERATURE', 'TYPE_T', 'UPDATE', '999',],
                ['MU',    'QTY_PRESSURE', 'TYPE_MU',  'UPDATE', '999',],

                ['QVAPOR', 'QTY_VAPOR_MIXING_RATIO','TYPE_QV',   'UPDATE', '999',],
                ['QCLOUD', 'QTY_CLOUDWATER_MIXING_RATIO','TYPE_QC', 'UPDATE', '999',],
                ['QICE',  'QTY_ICE_MIXING_RATIO','TYPE_QI',   'UPDATE', '999',],
                ['QSNOW', 'QTY_SNOW_MIXING_RATIO','TYPE_QS',   'UPDATE', '999',],
                #  ['QRAIN','QTY_RAINWATER_MIXING_RATIO','TYPE_QR', 'UPDATE','999',],
                #  ['QGRAUP','QTY_GRAUPEL_MIXING_RATIO','TYPE_QG', 'UPDATE','999',],

                ['CLDFRA', 'QTY_CLOUD_FRACTION',
                'TYPE_CFRAC', 'UPDATE', '999',],
                ['PSFC',  'QTY_SURFACE_PRESSURE',
                'TYPE_PSFC', 'UPDATE', '999',],
                ['T2',    'QTY_2M_TEMPERATURE',
                'TYPE_T',    'UPDATE', '999',],
                ['TSK',   'QTY_SKIN_TEMPERATURE',
                'TYPE_T',    'UPDATE', '999',],
                # ['REFL_10CM', 'QTY_RADAR_REFLECTIVITY', 'TYPE_REFL', 'UPDATE', '999',]
                ],

                wrf_state_bounds=[['QVAPOR', '0.0', 'NULL', 'CLAMP'],
                                ['QCLOUD', '0.0', 'NULL', 'CLAMP'],
                                ['QICE', '0.0', 'NULL', 'CLAMP'],
                                ['CLDFRA', '0.0', '1.0', 'CLAMP'],
                                ['QRAIN', '0.0', 'NULL', 'CLAMP'],
                                ['QSNOW', '0.0', 'NULL', 'CLAMP'],
                                ['QGRAUP', '0.0', 'NULL', 'CLAMP'], ],
                        ),
            '&ensemble_manager_nml':
            dict(layout=1,
                    tasks_per_node=20,
                    communication_configuration=1,
                    ),
            }

oeinf = 2.0

vis = dict(
        kind='MSG_4_SEVIRI_BDRF', sat_channel=1,
        km_between_obs=12, skip_border_km=8.0,
        error_generate=0.03, error_assimilate=0.06,
        loc_horiz_km=12,
        # height=6000, loc_vert_km=6,
        )

wv73 = dict(kind='MSG_4_SEVIRI_TB', sat_channel=6,
            km_between_obs=12, skip_border_km=8.0,
            error_generate=1, error_assimilate=2,
            loc_horiz_km=12,
            # height=7000, loc_vert_km=3
            )

wv62 = dict(kind='MSG_4_SEVIRI_TB', sat_channel=5,
            km_between_obs=12, skip_border_km=8.0,
            error_generate=1, error_assimilate=2,
            loc_horiz_km=20,
            # height=7000, loc_vert_km=3
            )

ir108 = dict(
             kind='MSG_4_SEVIRI_TB', sat_channel=9,
             n_obs=1,
             error_generate=5., error_assimilate=10.,
             loc_horiz_km=32)

radar = dict(
             kind='RADAR_REFLECTIVITY',
             km_between_obs=12, skip_border_km=8.0,
             heights=range(2000, 14001, 2000),
             error_generate=2.5, error_assimilate=2.5*oeinf,
             loc_horiz_km=20, loc_vert_km=3)

t = dict(
         kind='RADIOSONDE_TEMPERATURE',
         # n_obs=22500,
         n_obs=1, obs_locations=[(45., 0.)],
         error_generate=0.2, error_assimilate=0.2,
         heights=[1000,],  # range(1000, 17001, 2000),
         loc_horiz_km=5000, loc_vert_km=12.5)

q = dict(
         kind='RADIOSONDE_SPECIFIC_HUMIDITY', n_obs=1,
         error_generate=0., error_assimilate=5*1e-5,
         heights=[1000],  # range(1000, 17001, 2000),
         loc_horiz_km=50, loc_vert_km=2.5)

t2m = dict(
           kind='SYNOP_TEMPERATURE',
           km_between_obs=48, skip_border_km=8.0,
           error_generate=0.3, error_assimilate=0.6,
           loc_horiz_km=48, loc_vert_km=3)

psfc = dict(
            kind='SYNOP_SURFACE_PRESSURE', n_obs=1,
            error_generate=50., error_assimilate=100.,
            loc_horiz_km=32, loc_vert_km=5)

############################################
# for cloud fraction assimilation only

cf1 = dict(kind='CF192km', loc_horiz_km=9999,
           )
cf2 = dict(kind='CF96km', loc_horiz_km=96,
           )
cf3 = dict(kind='CF48km', loc_horiz_km=48,
           )
cf4 = dict(kind='CF24km', loc_horiz_km=24,
           )
cf5 = dict(kind='CF12km', loc_horiz_km=12,
           )
all_cloudfractions = [cf1, cf2, cf3, cf4, cf5]

CF_config = dict(var='WV73',
                scales_km=(12,),
                observed_width_km=384,
                dx_km_obs=1.0,
                dx_km_forecast=2.0,
                threshold=('value', 230), #('value', 230), #('value', 0.6), #('value', 230), #, #False, #  #, #('value', 230), ## 
                difference=False,
                first_guess_pattern='/RT_wrfout_d01_%Y-%m-%d_%H:%M:%S.nc',
                
                # f_obs_pattern='/jetfs/scratch/a11716773/master_thesis_2023/data2/sim_archive/nature_dx=2000m/RT_wrfout_d01_%Y-%m-%d_%H:%M:%S.nc',
                f_obs_pattern='/jetfs/home/lkugler/data/sim_archive/nat_250m_obs1km/*/1/RT_wrfout_d01_%Y-%m-%d_%H_%M_%S.nc',
                # f_obs_pattern='/jetfs/home/lkugler/data/sim_archive/exp_v1.18_P1_nature+1/2008-07-30_06:00/1/RT_wrfout_d01_%Y-%m-%d_%H_%M_%S.nc',
                f_grid_obs='/jetfs/home/lkugler/data/sim_archive/geo_em.d01.nc.250m-1km_400x400',

                obs_err_csv='/jetfs/home/lkugler/CloudfractionDA/data/hrNat_IR/OE-WV73_CF_230.csv',

                inflation_OE_var=2.0,
        )