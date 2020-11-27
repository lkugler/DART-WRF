
from . import clusters
cluster = clusters.vsc  # change cluster configuration here


class ExperimentConfiguration(object):
    def __init__(self):
        pass


exp = ExperimentConfiguration()
exp.expname = "exp_v1.12_conv1"
exp.model_dx = 2000
exp.timestep = 10
exp.n_ens = 40
exp.n_nodes = 10

n_obs = 64  # radar: n_obs for each observation height level

vis = dict(sat_channel=1, n_obs=n_obs, err_std=0.03,
           cov_loc_radius_km=10)
wv = dict(sat_channel=6, n_obs=n_obs, err_std=5.,
           cov_loc_radius_km=10)
ir108 = dict(sat_channel=9, n_obs=n_obs, err_std=5.,
             cov_loc_radius_km=10)

radar = dict(kind='RADAR', n_obs=n_obs, err_std=5.,
             heights=np.arange(1000, 15001, 1000),
             cov_loc_radius_km=10, cov_loc_vert_km=2)

t2m = dict(kind='SYNOP_TEMPERATURE', n_obs=n_obs, err_std=1.0, 
           cov_loc_radius_km=32, cov_loc_vert_km=1)
psfc = dict(kind='SYNOP_SURFACE_PRESSURE', n_obs=n_obs, err_std=50.,
           cov_loc_radius_km=32)
           

exp.observations = [t2m, psfc, ]

# directory paths depend on the name of the experiment
cluster.expname = exp.expname
