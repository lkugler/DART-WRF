
from . import clusters
cluster = clusters.vsc  # change cluster configuration here

class ExperimentConfiguration(object):
    def __init__(self):
        pass

exp = ExperimentConfiguration()
exp.expname = "exp_v1.10_LMU+shear_filter"
exp.model_dx = 2000
exp.timestep = 10
exp.n_ens = 20
exp.n_nodes = 5
exp.n_obs = 100
exp.error_variance = 0.001


# directory paths depend on the name of the experiment
cluster.expname = exp.expname
