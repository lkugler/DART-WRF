
from . import clusters
cluster = clusters.vsc  # change cluster configuration here

class ExperimentConfiguration(object):
    def __init__(self):
        pass

exp = ExperimentConfiguration()
exp.expname = "exp_v1.12_LMU_so_VIS"
exp.model_dx = 2000
exp.timestep = 10
exp.n_ens = 40
exp.n_nodes = 10

n_obs = 81  # radar: n_obs for each observation height level

vis = dict(sat=True, channel=1, n_obs=n_obs, err_std=0.03, 
           distance_between_obs_km=50, 
           cov_loc_radius_km=10)
radar = dict(sat=False, kind='radar', n_obs=n_obs, err_std=5.,
             distance_between_obs_km=50, 
             cov_loc_radius_km=10)

exp.observations = [vis,]

# directory paths depend on the name of the experiment
cluster.expname = exp.expname
