import os, sys, shutil, warnings
import datetime as dt

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster
from dartwrf import assim_synth_obs as aso

def evaluate_one_time(init, valid):
     """Evaluate the ensemble forecast in observation space at a given time, apart from the analysis time.

     Args:
          init (datetime): initialization time of the forecast
          valid (datetime): valid time of the forecast

     Returns:
          None
     """

     # # prepare nature and prior ensemble
     aso.prepare_nature_dart(valid)
     aso.prepare_prior_ensemble(valid, prior_init_time=init, prior_valid_time=valid, prior_path_exp=cluster.archivedir)


     if use_other_obsseq:  # use a different obsseq file
          f_obs_seq_out = use_other_obsseq
          shutil.copy(f_obs_seq_out, cluster.dart_rundir+'/obs_seq.out')

     else:  # from same exp
          # use the last assimilation obsseq file for the observation locations (note: observed values are not valid)     
          f_obs_seq_out = cluster.archivedir+valid.strftime("/obs_seq_out/%Y-%m-%d_%H:%M_obs_seq.out")

          from dartwrf.obs import obsseq
          oso = obsseq.ObsSeq(f_obs_seq_out)
          oso.df['observations'] = -9999
          oso.to_dart(cluster.dart_rundir+'/obs_seq.out')

     aso.evaluate(valid, output_format="%Y-%m-%d_%H:%M_obs_seq.final-evaluate")


if __name__ == "__main__":
     """Evaluate the ensemble forecast in observation space at a given time, apart from the analysis time.

     Note: Observations are not assimilated. This is only for evaluation purposes.

     Usage: python3 evaluate_obs_space.py init1,valid1 init2,valid2 ...
     """
     args = sys.argv[1:]
     init_valid_tuples = [a.split(',') for a in args]

     use_other_obsseq = False

     # we need an existing run_DART folder
     aso.prepare_run_DART_folder()

     for (init, valid) in init_valid_tuples:

          init = dt.datetime.strptime(init, "%Y-%m-%d_%H:%M")
          valid = dt.datetime.strptime(valid, "%Y-%m-%d_%H:%M")
          evaluate_one_time(init, valid)