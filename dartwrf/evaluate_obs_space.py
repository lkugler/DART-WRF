import os, sys, shutil, warnings
import time as time_module
import datetime as dt
import numpy as np

from config.cfg import exp
from config.cluster import cluster
from dartwrf import assim_synth_obs as aso

def get_previous_obsseq_file(time):
     oso_input = cluster.archivedir+'/obs_seq_out' + init.strftime("/%Y-%m-%d_%H:%M_obs_seq.out-beforeQC")

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

     aso.write_list_of_inputfiles_posterior(time)

     # use the last assimilation obsseq file for the observation locations (note: observed values are not valid)

     if use_other_obsseq:  # use a different obsseq file
          oso_input = use_other_obsseq
     else:  # from same exp
          
          oso_input = get_previous_obsseq_file(time)
          shutil.copy(oso_input, cluster.dart_rundir+'/obs_seq.out')

     aso.evaluate(time, output_format="%Y-%m-%d_%H:%M_obs_seq.final-evaluate")