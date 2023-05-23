import os, sys, shutil, warnings
import time as time_module
import datetime as dt
import numpy as np

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster
from dartwrf import assim_synth_obs as aso

def get_previous_obsseq_file(time):
     oso_input = cluster.archivedir+'/obs_seq_out' + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out-beforeQC")

     if not os.path.isfile(oso_input):  # fallback
          oso_input = cluster.archivedir+'/obs_seq_out' + time.strftime("/%Y-%m-%d_%H:%M_obs_seq.out")

     return oso_input



if __name__ == "__main__":
     """Evaluate the ensemble forecast in observation space at a given time, apart from the analysis time.

     Note: Observations are not assimilated. This is only for evaluation purposes.
     """

     init = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d_%H:%M")
     time = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d_%H:%M")

     use_other_obsseq = False

     # we need an existing run_DART folder
     aso.prepare_run_DART_folder()

     # # prepare nature and prior ensemble
     aso.prepare_nature_dart(time)
     aso.prepare_prior_ensemble(time, prior_init_time=init, prior_valid_time=time, prior_path_exp=cluster.archivedir)

     # tell DART to use the prior as input
     aso.write_list_of_inputfiles_prior()

     if use_other_obsseq:  # use a different obsseq file
          oso_input = use_other_obsseq
     else:  # from same exp

          # use the last assimilation obsseq file for the observation locations (note: observed values are not valid)     
          oso_input = get_previous_obsseq_file(init)
          shutil.copy(oso_input, cluster.dart_rundir+'/obs_seq.out')

     aso.evaluate(time, output_format="%Y-%m-%d_%H:%M_obs_seq.final-evaluate")