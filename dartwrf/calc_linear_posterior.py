import os, sys, shutil, warnings, glob
import datetime as dt

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster
from dartwrf import assimilate as aso
from dartwrf import dart_nml
from dartwrf.obs import create_obsseq_out as osq_out

pattern_osf_linear = cluster.archivedir + "/diagnostics/%Y-%m-%d_%H:%M_obs_seq.final-linear"  # how an obs_seq.final file is archived

def calc_lin_posterior(assim_time):
     """Run filter to get the linear, optimal-interpolation posterior in obs-space

     Args:
          prior_init_time (datetime): initialization of prior forecast
          assim_time (datetime): assimilation time

     Returns:
          None
     """
     # what is the prior for this assim time?
     # read link_to_prior
     link_to_prior = cluster.archivedir + assim_time.strftime('/%Y-%m-%d_%H:%M/')+'link_to_prior.txt'
     with open(link_to_prior) as f:
          lines = [l.strip() for l in f.readlines()]
          prior_exp = lines[0]
          prior_init_time = dt.datetime.strptime(lines[1].strip('/'), '%Y-%m-%d_%H:%M')
     
     aso.prepare_prior_ensemble(assim_time, prior_init_time=prior_init_time, prior_valid_time=assim_time, prior_path_exp=prior_exp)
     #aso.prepare_nature_dart(assim_time) 
     
     dart_nml.write_namelist()

     # does an observation exist at this time?
     #f_oso = assim_time.strftime(aso.pattern_obs_seq_out)
     f_oso = cluster.archivedir+assim_time.strftime("/diagnostics/%Y-%m-%d_%H:%M_obs_seq.out")

     if os.path.exists(f_oso):
          # use the existing file
          shutil.copy(f_oso, cluster.dart_rundir+'/obs_seq.out')
     else:
          raise NotImplementedError(f_oso+' does not exist!')
     
     # link in the linear filter version
     from dartwrf.utils import symlink
     path_linear_filter = '/jetfs/home/lkugler/data/compile/DART/DART-10.8.3-kalmanposterior/models/wrf/work/filter'
     symlink(path_linear_filter,
             os.path.join(cluster.dart_rundir, 'filter'))

     aso.filter(nproc=12)
     aso.archive_filter_diagnostics(assim_time, pattern_osf_linear)


if __name__ == "__main__":
     """Evaluate the ensemble forecast in observation space at a given time, apart from the analysis time.

     Note: Observations are not assimilated. This is only for evaluation purposes.

     Usage: python3 evaluate_obs_space.py init1,valid1 init2,valid2 ...
     """
     args = sys.argv[1:]
     #arg_tuples = [a.split(',') for a in args]

     # we need an existing run_DART folder
     aso.prepare_run_DART_folder()

     for assim_time in args:
          #prior_init_time = dt.datetime.strptime(prior_init_time, "%Y-%m-%d_%H:%M")
          assim_time = dt.datetime.strptime(assim_time, "%Y-%m-%d_%H:%M")
          calc_lin_posterior(assim_time)
          