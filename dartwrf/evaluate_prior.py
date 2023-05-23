import os, sys, shutil, warnings
import time as time_module
import datetime as dt
import numpy as np

from exp_config import exp
from server_config import cluster
from dartwrf.utils import symlink, copy, sed_inplace, append_file, mkdir, try_remove, print, shell
from dartwrf import assim_synth_obs as aso

from osselyze.utils import get_prior_config

if __name__ == "__main__":

     assim_time = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d_%H:%M")

     print("> computing posterior observations ...")
     print(">> prepare prior ensemble")
     prior_exp, prior_init = get_prior_config(cluster.archive_base, exp.expname, init=assim_time)
     prior_valid_time = assim_time
     aso.prepare_prior_ensemble(assim_time, prior_init, prior_valid_time, cluster.archive_base+'/'+prior_exp)

    # prepare an obsseq without rejected observations
     if exp.use_existing_obsseq:  # from another exp
          oso_input = assim_time.strftime(exp.use_existing_obsseq)
     else:  # from same exp
          oso_input = cluster.archivedir+'/obs_seq_out' + assim_time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out-beforeQC")
          if not os.path.isfile(oso_input):
               oso_input = cluster.archivedir+'/obs_seq_out' + assim_time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out")
          shutil.copy(oso_input, cluster.dart_rundir+'/obs_seq.out')


     aso.evaluate(assim_time, output_format="%Y-%m-%d_%H:%M_obs_seq.final-eval_prior_allobs")