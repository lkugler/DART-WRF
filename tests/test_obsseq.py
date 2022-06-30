import os, filecmp, shutil
import numpy as np

from config.cfg import exp, cluster
from dartwrf import obsseq


def test_oso():

    input = cluster.scriptsdir + "/../tests/obs_seq.orig.out"
    output = cluster.scriptsdir + "/../tests/obs_seq.test.out"
    output_true = cluster.scriptsdir + "/../tests/obs_seq.superob.out"

    obs = obsseq.ObsSeq(input)

    # select a subset
    obs.df = obs.df.superob(window_km=50)

    #obs.plot(f_out="/home/fs71386/lkugler/data/analysis/map_obs_superobs_obs10-50.png")

    # write to obs_seq.out in DART format
    obs.to_dart(f=output)

    #assert filecmp.cmp(output, output_true)

def test_plot():
    input = cluster.scriptsdir + "/../tests/obs_seq.out_obs2"
    obs = obsseq.ObsSeq(input)
    # select a subset
    obs.df = obs.df.superob(window_km=10)

    obs.plot(f_out="/home/fs71386/lkugler/data/analysis/map_obs_superobs_obs2-10.png")


def test_osf():
    input = cluster.scriptsdir + "/../tests/obs_seq.final"
    obs = obsseq.ObsSeq(input)
    prior_Hx = obs.df.get_prior_Hx()

    # TODO: compare with given truth

def test_superob():
    input = cluster.scriptsdir + "/../tests/obs_seq.out_obs2"
    output = cluster.scriptsdir + "/../tests/obs_seq.test.out"
    obs = obsseq.ObsSeq(input)

    obs.df = obs.df.superob(window_km=10)

    obs.to_dart(f=output)

    obs = obsseq.ObsSeq(output)

    from IPython import embed; embed()

if __name__ == '__main__':
    test_superob()
    pass
