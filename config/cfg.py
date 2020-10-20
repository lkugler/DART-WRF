
from . import clusters
cluster = clusters.vsc  # change cluster configuration here


class ExperimentConfiguration(object):
    def __init__(self):
        pass


exp = ExperimentConfiguration()
exp.expname = "exp_v1.12_LMU_radar_vertloc1km"
exp.model_dx = 2000
exp.timestep = 10
exp.n_ens = 40
exp.n_nodes = 10

n_obs = 64  # radar: n_obs for each observation height level

vis = dict(sat=True, channel=1, n_obs=n_obs, err_std=0.03,
           cov_loc_radius_km=10)
wv = dict(sat=True, channel=6, n_obs=n_obs, err_std=5.,
           cov_loc_radius_km=10)

radar = dict(sat=False, kind='RADAR', n_obs=n_obs, err_std=5.,
             cov_loc_radius_km=10, cov_loc_vert_km=1)
psfc = dict(sat=False, kind='PSFC', n_obs=n_obs, err_std=50.,
             cov_loc_radius_km=10)

exp.observations = [radar, ]

# directory paths depend on the name of the experiment
cluster.expname = exp.expname
