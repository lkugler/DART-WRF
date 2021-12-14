import filecmp
from config.cfg import exp, cluster

from dartwrf import obsseq


def test_oso():

    input = cluster.scriptsdir + "/../tests/obs_seq.orig.out"
    output = cluster.scriptsdir + "/../tests/obs_seq.test.out"
    output_true = cluster.scriptsdir + "/../tests/obs_seq.superob.out"

    obs = obsseq.ObsSeq(input)

    # select a subset
    obs.superob(window_km=50)

    # write to obs_seq.out in DART format
    obs.to_dart(f=output)

    assert filecmp.cmp(output, output_true)


def test_osf():
    input = cluster.scriptsdir + "/../tests/obs_seq.final"
    obs = obsseq.ObsSeq(input)
    prior_Hx = obs.get_prior_Hx_matrix()

    # TODO: compare with given truth

if __name__ == '__main__':
    test_osf()
