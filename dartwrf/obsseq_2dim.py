"""Create obs_seq.out files with collapsed vertical dimension
Specifically, one observation per column which is the maximum of the column
"""

from copy import copy
import os, sys, shutil, warnings
import time as time_module
import datetime as dt
import numpy as np

from config.cfg import exp, cluster
from dartwrf import assim_synth_obs as aso
from dartwrf import obsseq


if __name__ == "__main__":

     assim_time = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d_%H:%M")

    # prepare an obsseq without rejected observations
     if exp.use_existing_obsseq:  # from another exp
          oso_input = assim_time.strftime(exp.use_existing_obsseq)

     # only assured to work with single obstype
     if len(exp.observations) > 1:
          raise NotImplementedError()
     n_obs = exp.observations[0]['n_obs']

     # existing obsseq with multi levels
     oso = obsseq.ObsSeq(oso_input)

     nlev = len(oso.df)/n_obs
     if nlev - int(nlev) != 0:
          raise RuntimeError()
     nlev = int(nlev)  # levels per obs
     
     # copy will be modified
     output = copy(oso)
     output.df = output.df.iloc[0::nlev]  #  every nth level = first level

     #print(output.df, oso.df)

     # iterate through, set value to max
     for i_obs in range(0, n_obs):  # go through n_obs (all columns)

          i_obs_subset = i_obs*nlev  # jumps by nlev (from one to next column)
          column = oso.df.loc[0 + i_obs_subset:nlev + i_obs_subset, :]  # select column

          output.df.loc[i_obs_subset, ('observations')] = float(column['observations'].max())
          output.df.loc[i_obs_subset, ('truth')] = float(column['truth'].max())

     print(output.df) #, 'observations'], output.df.loc[i_obs, 'observations'])

     fout = cluster.archivedir + assim_time.strftime("/obs_seq_out/%Y-%m-%d_%H:%M_obs_seq.out")
     os.makedirs(cluster.archivedir+'/obs_seq_out', exist_ok=True)
     output.to_dart(fout)
