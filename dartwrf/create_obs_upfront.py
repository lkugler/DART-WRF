from multiprocessing.sharedctypes import Value
import os, sys, shutil, warnings
import time as time_module
import datetime as dt
import numpy as np

from exp_config import exp
from server_config import cluster
from dartwrf.utils import copy, print
import dartwrf.create_obsseq as osq
from dartwrf import obsseq

from dartwrf import assim_synth_obs as aso

tformat = '%Y-%m-%d_%H:%M'


if __name__ == "__main__":
    """Create observations for multiple times upfront
    """

    args = sys.argv[1:]
    times = []
    for tstr in args:
        times.append(dt.datetime.strptime(tstr, tformat))

    # strange path?
    # dir_for_obsseqout = exp.nature_wrfout + '/../../../obs_seq_out/'+exp.use_existing_obsseq  
    raise NotImplementedError('where to save obsseq to?')  
    dir_for_obsseqout = ''  # TODO: solve this when necessary
    print('will save obsseq to', dir_for_obsseqout)
    os.makedirs(dir_for_obsseqout, exist_ok=True) 

    os.chdir(cluster.dart_rundir)

    # link DART binaries to run_DART
    os.system(cluster.python + " " + cluster.scripts_rundir + "/link_dart_rttov.py")  

    # remove any existing observation files
    os.system("rm -f input.nml obs_seq.in obs_seq.out obs_seq.out-orig obs_seq.final")  
    aso.set_DART_nml()

    for time in times:
        print('obsseq for time', time)

        aso.prepare_nature_dart(time)  # link WRF files to DART directory

        osq.create_obsseqin_alltypes(time, exp.observations)  # obs_seq.in

        aso.run_perfect_model_obs(nproc=6)  # create observations (obs_seq.out)

        oso = obsseq.ObsSeq(cluster.dart_rundir + "/obs_seq.out")

        if True:  # set reflectance < surface albedo to surface albedo
            print(" 2.2) removing obs below surface albedo ")
            if_vis_obs = oso.df['kind'].values == 262
            if_obs_below_surface_albedo = oso.df['observations'].values < 0.2928

            oso.df.loc[if_vis_obs & if_obs_below_surface_albedo, ('observations')] = 0.2928
            oso.to_dart(f=cluster.dart_rundir + "/obs_seq.out")

        if getattr(exp, "superob_km", False):
            print(" 2.3) superobbing to", exp.superob_km, "km")
            oso.df = oso.df.superob(window_km=exp.superob_km)
            copy(cluster.dart_rundir + "/obs_seq.out", cluster.dart_rundir + "/obs_seq.out-orig")
            oso.to_dart(f=cluster.dart_rundir + "/obs_seq.out")

        aso.archive_osq_out(time, dir_obsseq=dir_for_obsseqout)

