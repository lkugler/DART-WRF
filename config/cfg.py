from dartwrf import utils

exp = utils.Experiment()
exp.expname = "test_newcode"
exp.model_dx = 2000
exp.n_ens = 10

exp.filter_kind = 1
exp.prior_inflation = 0
exp.post_inflation = 4
exp.sec = True
exp.reject_smallFGD = False
exp.cov_loc_vert_km_horiz_km = (3, 20)
exp.superob_km = False  # False or int (spatial averaging of observations)
exp.adjust_obs_impact = False

exp.use_existing_obsseq = False  # False or pathname (use precomputed obs_seq.out files)
#exp.use_existing_obsseq = '/jetfs/home/lkugler/data/sim_archive/NoImpactFactors/obs_seq_out/2008-07-30_%H:%M_obs_seq.out'
#exp.use_existing_obsseq = '/jetfs/home/lkugler/data/sim_archive/exp_v1.21_P3_wbub7_VIS_obs10_loc20/obs_seq_out/2008-07-30_%H:%M_obs_seq.out'  
#exp.use_existing_obsseq = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.21_P3_wbub7_REFL2D_obs10_loc20_oe5/obs_seq_out/2008-07-30_%H:%M_obs_seq.out'
#exp.use_existing_obsseq = '/gpfs/data/fs71386/lkugler/sim_archive/exp_v1.21_P2_rr_VIS_obs20_loc4/obs_seq_out/2008-07-30_%H:%M_obs_seq.out'

#exp.nature = '/mnt/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P3_wbub7_nat/2008-07-30_12:00/1'
exp.nature = '/mnt/jetfs/scratch/lkugler/data/sim_archive/exp_v1.18_P1_nature/2008-07-30_06:00/1'

exp.input_profile = '/mnt/jetfs/home/lkugler/data/initial_profiles/wrf/ens/2022-03-31/raso.fc.<iens>.wrfprof'
#exp.input_profile = '/gpfs/data/fs71386/lkugler/initial_profiles/wrf/ens/2022-03-31/raso.nat.<iens>.wrfprof'
#exp.input_profile = '/gpfs/data/fs71386/lkugler/initial_profiles/wrf/ens/2022-05-18/raso.fc.<iens>.wrfprof'


# localize vertically, if it has a vertical position
# needs a horizontal scale too, to calculate the vertical normalization
# since you can not specify different vertical localizations for diff. variables

# n_obs= 22500: 2km, 5776: 4km, 121: 30km, 256:16x16 (20km); 961: 10km resoltn # radar: n_obs for each observation height level

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
         #n_obs=22500, obs_locations='square_array_evenly_on_grid',
         n_obs=1, obs_locations=[(45., 0.)],
         error_generate=0.2, error_assimilate=0.2,
         heights=[1000,], #range(1000, 17001, 2000),
         cov_loc_radius_km=50)

q = dict(plotname='Specific humidity', plotunits='[kg/kg]',
         kind='RADIOSONDE_SPECIFIC_HUMIDITY', n_obs=1,
         error_generate=0., error_assimilate=5*1e-5,
         heights=[1000], #range(1000, 17001, 2000),
         cov_loc_radius_km=0.1)

t2m = dict(plotname='SYNOP Temperature', plotunits='[K]',
           kind='SYNOP_TEMPERATURE', n_obs=1, 
           error_generate=0.1, error_assimilate=1.,
           cov_loc_radius_km=20)

psfc = dict(plotname='SYNOP Pressure', plotunits='[Pa]',
            kind='SYNOP_SURFACE_PRESSURE', n_obs=1, 
            error_generate=50., error_assimilate=100.,
            cov_loc_radius_km=32)

exp.observations = [t]
exp.update_vars = ['U', 'V', 'W', 'THM', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'PSFC']
#exp.update_vars = ['U', 'V', 'W', 'T', 'PH', 'MU', 'QVAPOR', 'PSFC']

