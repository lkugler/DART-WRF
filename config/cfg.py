import numpy as np
from . import clusters
cluster = clusters.vsc  # change cluster configuration here


class ExperimentConfiguration(object):
    def __init__(self):
        pass


exp = ExperimentConfiguration()
exp.expname = "exp_v1.16_P1-1_Radar"
exp.model_dx = 2000
exp.n_ens = 40
exp.n_nodes = 10

n_obs = 1600  # 50km res: 64:8x8; 10km res: 1600:40x40  # radar: n_obs for each observation height level

vis = dict(plotname='VIS 0.6µm',  plotunits='[1]',
           kind='MSG_4_SEVIRI_BDRF', sat_channel=1, n_obs=n_obs, 
           err_std=0.03,
           error_generate=0.03, error_assimilate=0.06,
           cov_loc_radius_km=32)

wv73 = dict(plotname='Brightness temperature WV 7.3µm',  plotunits='[K]',
            kind='MSG_4_SEVIRI_TB', sat_channel=6, n_obs=n_obs, 
            err_std=False,
            error_generate=False, error_assimilate=False,
            cov_loc_radius_km=32)

ir108 = dict(plotname='Brightness temperature IR 10.8µm', plotunits='[K]',
             kind='MSG_4_SEVIRI_TB', sat_channel=9, n_obs=n_obs, 
             err_std=5.,
             error_generate=5., error_assimilate=10.,
             cov_loc_radius_km=32)

radar = dict(plotname='Radar reflectivity', plotunits='[dBz]',
             kind='RADAR_REFLECTIVITY', n_obs=n_obs, 
             error_generate=2.5, error_assimilate=5.,
             heights=np.arange(1000, 15001, 1000),
             cov_loc_radius_km=32, cov_loc_vert_km=4)

t2m = dict(plotname='SYNOP Temperature', plotunits='[K]',
           kind='SYNOP_TEMPERATURE', n_obs=n_obs, 
           error_generate=0.1, error_assimilate=1.,
           cov_loc_radius_km=20, cov_loc_vert_km=3)

psfc = dict(plotname='SYNOP Pressure', plotunits='[dBz]',
            kind='SYNOP_SURFACE_PRESSURE', n_obs=n_obs, 
            error_generate=50., error_assimilate=100.,
            cov_loc_radius_km=32, cov_loc_vert_km=5)


exp.observations = [radar, ] # 108, wv73, vis]

# directory paths depend on the name of the experiment
cluster.expname = exp.expname
