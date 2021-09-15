import os, sys, shutil
import datetime as dt
import numpy as np
from scipy.interpolate import interp1d

from config.cfg import exp, cluster
from utils import symlink, copy, mkdir, sed_inplace, append_file, print
import create_obsseq as osq
import assim_synth_obs as aso
import pre_assim
import wrfout_add_geo

"""Apply observation operator to some ensemble state
i.e. wrfout files in an archive directory

output: saves obs_seq.final files
these contain the Hx values
usually applied to 1 min forecasts to assess the posterior analysis quality
(analysis+1minute = 'posterior') 

"""

if __name__ == '__main__':
    prev_forecast_init = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
    time = dt.datetime.strptime(sys.argv[2], '%Y-%m-%d_%H:%M')
    exppath_firstguess = cluster.archivedir
    print(prev_forecast_init, time)

    # link ensemble states to run_DART directory
    # we want the observation operator applied to these states!
    pre_assim.run(time, prev_forecast_init, exppath_firstguess)

    savedir = cluster.archivedir+'/obs_seq_final_1min/'

    aso.set_DART_nml(just_prior_values=True)
    osq.create_obsseqin_alltypes(time, exp.observations, obs_errors=False)

    # prepare dummy nature (this Hx is irrelevant)
    os.chdir(cluster.dartrundir)
    os.system('cp ./advance_temp1/wrfout_d01 ./wrfout_d01')
    wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc',
                        cluster.dartrundir+'/wrfout_d01')
    aso.run_perfect_model_obs()
    aso.assimilate(nproc=96)

    # only the prior state values are of interest in this file
    # observation and truth is wrong in this file (dummy)
    aso.archive_osq_final(time, posterior_1min=True)
