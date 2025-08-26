import datetime as dt
from dartwrf.workflows import WorkFlows
from dartwrf.utils import Config

from config.jet import cluster_defaults
cluster_defaults.update(use_slurm=True)
from config.defaults import dart_nml, t2m

cfg = Config(name='exp1',
    ensemble_size = 10,
    dart_nml = dart_nml,

    assimilate_these_observations = [t2m,],
    assimilate_existing_obsseq = False,
    nature_wrfout_pattern = '/jetfs/scratch/username/raw_data/nature/*/1/wrfout_d01_%Y-%m-%d_%H_%M_%S',
    
    geo_em_nature = '/jetfs/scratch/username/geo_em.d01.nc',
    geo_em_forecast = '/jetfs/scratch/username/geo_em.d01.nc',
    
    time = dt.datetime(2008, 7, 30, 11),
    update_vars = ['THM', 'PH', 'MU', 'QVAPOR',],
    **cluster_defaults)

w = WorkFlows(cfg)
w.prepare_WRFrundir(cfg)
id = w.assimilate(cfg, depends_on=id)