
from . import clusters
cluster = clusters.vsc  # change cluster configuration here

class ExperimentConfiguration(object):
    def __init__(self):
        pass

exp = ExperimentConfiguration()
exp.expname = "exp_v1.12_LMU_WV73_cde"
exp.model_dx = 2000
exp.timestep = 10
exp.n_ens = 20
exp.n_nodes = 5
exp.n_obs = 100  # radar: n_obs for each observation height level

exp.sat_channels = [6,]
exp.sat_err = 0.03
exp.radar_err = 5.
exp.distance_between_obs_meters = 10000

# directory paths depend on the name of the experiment
cluster.expname = exp.expname
