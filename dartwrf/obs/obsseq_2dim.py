"""Create obs_seq.out files with collapsed vertical dimension
Specifically, one observation per column which is the maximum of the column

Use this script before running the OSSE workflow, to prepare obs_seq.out files.

Note:
     path_3d_obsseq = '/path/exp_obs10_loc20/obs_seq_out/2008-07-30_%H:%M_obs_seq.out'  

Note:
     Only works in case there is 1 observation type!

Example:
     python obsseq_2dim.py exp_v1.22_P2_rr_REFL_obs10_loc20_oe2.5 2008-07-30_13:00
"""

from copy import copy
import os, sys, warnings
import datetime as dt
import numpy as np

from dartwrf.server_config import cluster
from dartwrf import utils
from dartwrf.obs import obsseq

def _get_n_obs_per_layer(oso):     
     """Determine number of observations per layer from obsseq.ObsSeq object

     Args:
          oso (obsseq.ObsSeq): obsseq object

     Returns:
          int
     """
     height_all = np.array([a[2] for a in oso.df.loc3d])

     height_first = height_all[0]

     # count how often this height appears
     n_obs_per_layer = int(np.sum(height_all == height_first))
     return n_obs_per_layer


if __name__ == "__main__":
     exp = sys.argv[1]
     assim_time = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d_%H:%M")
     
     path_3d_obsseq = cluster.archive_base+exp+'/obs_seq_out/%Y-%m-%d_%H:%M_obs_seq.out'
     oso_input = assim_time.strftime(path_3d_obsseq)
     
     # existing obsseq with multi levels
     oso = obsseq.ObsSeq(oso_input)
     
     n_obs_3d = len(oso.df)
     n_obs_per_layer = _get_n_obs_per_layer(oso)
     nlev = int(n_obs_3d/n_obs_per_layer)
     assert np.allclose(nlev, n_obs_3d/n_obs_per_layer), 'n_obs not evenly divisible!'

     print('n_obs_per_layer', n_obs_per_layer)
     print('n_obs_3d', n_obs_3d)
     
     output = copy(oso)  # copy will be modified
     # output.df = output.df.copy()  # without this, we get a SettingWithCopyWarning
     output.df = output.df.iloc[0::nlev]  #  every nth level = first level

     # iterate through, set value to max
     for i_obs in range(0, ):  # go through n_obs (all columns)

          i_obs_subset = i_obs*nlev  # jumps by nlev (from one to next column)
          column = oso.df.loc[0 + i_obs_subset:nlev + i_obs_subset, :]  # select column

          output.df.loc[i_obs_subset, ('observations')] = float(column['observations'].max())
          output.df.loc[i_obs_subset, ('truth')] = float(column['truth'].max())

     print(output.df)

     fout = cluster.archivedir + assim_time.strftime("/obs_seq_out/%Y-%m-%d_%H:%M_obs_seq.out")
     os.makedirs(cluster.archivedir+'/obs_seq_out', exist_ok=True)
     output.to_dart(fout)
     utils.write_txt(["created from", oso_input,], fout[:-3]+'.txt')
