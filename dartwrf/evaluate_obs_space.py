import os, sys, shutil, warnings, glob
import datetime as dt

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster
from dartwrf import assimilate as aso
from dartwrf import dart_nml
from dartwrf.obs import create_obsseq_out as osq_out

def evaluate_one_time(assim_time, valid_time, use_other_obsseq=False):
     """Evaluate the ensemble forecast in observation space at a given time, apart from the analysis time.

     Args:
          assim_time (datetime): initialization time of the forecast
          valid_time (datetime): valid_time of the forecast (e.g. +1 minute after assim_time)

     Returns:
          None
     """
     aso.prepare_run_DART_folder()
     aso.prepare_prior_ensemble(valid_time, prior_init_time=assim_time, prior_valid_time=valid_time, prior_path_exp=cluster.archivedir)
     dart_nml.write_namelist()

     if os.path.isfile(exp.assimilate_existing_obsseq):
          # use the existing obs_seq.out file
          shutil.copy(exp.assimilate_existing_obsseq, cluster.dart_rundir+'/obs_seq.out')
     else:
          # is there a pre-existing obs file from assimilation before?
          f_oso = valid_time.strftime(cluster.pattern_obs_seq_out)
          f_oso = cluster.archivedir+valid_time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out")

          if os.path.isfile(f_oso):
               # use the existing file
               shutil.copy(f_oso, cluster.dart_rundir+'/obs_seq.out')
          else:
               print("Obs file does not exist:", f_oso)
               try:
                    # generate the observations for the specified valid_time
                    print("Trying to generate observations from a nature file")
                    aso.prepare_nature_dart(valid_time)
                    osq_out.generate_obsseq_out(valid_time)
               except:
                    print("Failed. Trying to evaluate posterior with dummy observations")
                    # use an old obsseq file and overwrite obs/truth values with "missing value"
                    f_oso = cluster.archivedir+valid_time.strftime("/diagnostics/%Y-%m-%d_%H:%M_obs_seq.out")
                    if not os.path.isfile(f_oso):
                         raise RuntimeError(f_oso+' not found. Cannot create dummy observation.')
               
                    from dartwrf.obs import obsseq
                    oso = obsseq.ObsSeq(f_oso)

                    # overwrite obs/truth values with "missing value"
                    oso.df['observations'] = -888888.0
                    oso.df['truth'] = -888888.0
                    oso.to_dart(cluster.dart_rundir+'/obs_seq.out')
     
     aso.evaluate(valid_time, f_out_pattern=cluster.archivedir + "/diagnostics/%Y-%m-%d_%H:%M:%S_obs_seq.final-evaluate")


if __name__ == "__main__":
     """Evaluate the ensemble forecast in observation space at a given time, apart from the analysis time.

     Note: Observations are not assimilated. This is only for evaluation purposes.

     Usage: python3 evaluate_obs_space.py init1,valid1 init2,valid2 ...
     """
     args = sys.argv[1:]
     arg_tuples = [a.split(',') for a in args]

     # we need an existing run_DART folder
     aso.prepare_run_DART_folder()

     for (assim_time, valid_time) in arg_tuples:

          assim_time = dt.datetime.strptime(assim_time, "%Y-%m-%d_%H:%M")
          valid_time = dt.datetime.strptime(valid_time, "%Y-%m-%d_%H:%M:%S")
          evaluate_one_time(assim_time, valid_time)
