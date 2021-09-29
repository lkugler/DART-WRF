import numpy as np
from config import clusters  # from . = problem in archivedir
cluster = clusters.vsc  # change cluster configuration here


class ExperimentConfiguration(object):
    def __init__(self):
        pass


exp = ExperimentConfiguration()
exp.expname = "exp_v1.18_P1_nature"
exp.model_dx = 2000
exp.n_ens = 4
exp.n_nodes = 1

#exp.nature_wrfout = '/home/fs71386/lkugler/data/sim_archive/exp_v1.17_P1_nature/2008-07-30_06:00/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'
exp.input_profile = '/home/fs71386/lkugler/wrf_profiles/data/wrf/ens/2021-05-04/raso.nat.<iens>.wrfprof'
#exp.input_profile = '/home/fs71386/lkugler/wrf_profiles/data/wrf/ens/2021-05-04/raso.fc.<iens>.wrfprof'


# localize vertically, if it has a vertical position
# needs a horizontal scale too, to calculate the vertical normalization
# since you can not specify different vertical localizations for diff. variables
exp.cov_loc_vert_km_horiz_km = (2, 20)  

n_obs = 961  #121: 30km, 256:16x16 (20km); 961: 10km resoltn # radar: n_obs for each observation height level

vis = dict(plotname='VIS 0.6µm',  plotunits='[1]',
           kind='MSG_4_SEVIRI_BDRF', sat_channel=1, n_obs=n_obs, 
           error_generate=0.03, error_assimilate=0.06,
           cov_loc_radius_km=20)

wv73 = dict(plotname='Brightness temperature WV 7.3µm',  plotunits='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=6, n_obs=n_obs, 
            error_generate=1., error_assimilate=False, 
            cov_loc_radius_km=20)

ir108 = dict(plotname='Brightness temperature IR 10.8µm', plotunits='[K]',
             kind='MSG_4_SEVIRI_TB', sat_channel=9, n_obs=n_obs, 
             error_generate=5., error_assimilate=10.,
             cov_loc_radius_km=32)

radar = dict(plotname='Radar reflectivity', plotunits='[dBz]',
             kind='RADAR_REFLECTIVITY', n_obs=n_obs, 
             error_generate=2.5, error_assimilate=5.,
             heights=np.arange(2000, 14001, 2000),
             cov_loc_radius_km=20)

t2m = dict(plotname='SYNOP Temperature', plotunits='[K]',
           kind='SYNOP_TEMPERATURE', n_obs=n_obs, 
           error_generate=0.1, error_assimilate=1.,
           cov_loc_radius_km=20)

psfc = dict(plotname='SYNOP Pressure', plotunits='[dBz]',
            kind='SYNOP_SURFACE_PRESSURE', n_obs=n_obs, 
            error_generate=50., error_assimilate=100.,
            cov_loc_radius_km=32)


exp.observations = [] #wv73] #radar] # 108, wv73, vis]
#exp.update_vars = ['T', 'QVAPOR', 'QCLOUD', 'QICE','CLDFRA']
exp.update_vars = ['U', 'V', 'T', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'TSK', 'CLDFRA']

# directory paths depend on the name of the experiment
cluster.expname = exp.expname
