"""Create obs_seq.out files with collapsed vertical dimension
Specifically, one observation per column which is the maximum of the column

Use this script before running the OSSE workflow, to prepare obs_seq.out files.

path_3d_obsseq = '/path/exp_obs10_loc20/obs_seq_out/2008-07-30_%H:%M_obs_seq.out'  
"""

from copy import copy
import os, sys, shutil, warnings
import time as time_module
import datetime as dt
import numpy as np

from config.cluster import cluster
from dartwrf import utils
from dartwrf import assim_synth_obs as aso
from dartwrf import obsseq


if __name__ == "__main__":
     
     exp = sys.argv[1]
     assim_time = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d_%H:%M")
     
     path_3d_obsseq = cluster.archive_base+exp+'/obs_seq_out/%Y-%m-%d_%H:%M_obs_seq.out'
     oso_input = assim_time.strftime(path_3d_obsseq)
     
     # load experiment config
     sys.path.insert(0, cluster.archivedir+'/'+exp+'/DART-WRF')
     from config import cfg

     # only assured to work with single obstype
     if len(cfg.exp.observations) > 1:
          raise NotImplementedError()

     # existing obsseq with multi levels
     oso = obsseq.ObsSeq(oso_input)

     n_obs = cfg.exp.observations[0]['n_obs']
     nlev = len(oso.df)/n_obs
     if nlev - int(nlev) != 0:
          raise RuntimeError()
     nlev = int(nlev)  # levels per obs
     print('nlev', nlev)
     print('n_obs', n_obs)
     
     output = copy(oso)  # copy will be modified
     # output.df = output.df.copy()  # without this, we get a SettingWithCopyWarning
     output.df = output.df.iloc[0::nlev]  #  every nth level = first level

     #print(output.df, oso.df)

     # iterate through, set value to max
     for i_obs in range(0, n_obs):  # go through n_obs (all columns)

          i_obs_subset = i_obs*nlev  # jumps by nlev (from one to next column)
          column = oso.df.loc[0 + i_obs_subset:nlev + i_obs_subset, :]  # select column

          output.df.loc[i_obs_subset, ('observations')] = float(column['observations'].max())
          output.df.loc[i_obs_subset, ('truth')] = float(column['truth'].max())

     print(output.df)

     fout = cluster.archivedir + assim_time.strftime("/obs_seq_out/%Y-%m-%d_%H:%M_obs_seq.out")
     os.makedirs(cluster.archivedir+'/obs_seq_out', exist_ok=True)
     output.to_dart(fout)
     utils.write_txt(["created from", oso_input,], fout[:-3]+'.txt')
