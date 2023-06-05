import os, filecmp, shutil
import numpy as np

from dartwrf.server_config import cluster
from dartwrf.obs import obsseq


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

def test_concat_obsseq():
    """Test the concatenation of two obs_seq.out files"""



    f1 = './obs_seq.T2m.out'
    f2 = './obs_seq.WV73.out'
    f_output = './obs_seq.combi.out'
    f_expected = './obs_seq.combi-expected.out'

    oso1 = obsseq.ObsSeq(f1)
    oso2 = obsseq.ObsSeq(f2)

    # #oso3 = oso1
    # combi_df = pd.concat([oso1.df, oso2.df],
    #                     ignore_index=True  # we use a new observation index now
    #                     )

    # n_obstypes = combi_df.kind.nunique()
    # list_kinds = combi_df.kind.unique()

    # obstypes = []
    # for kind in list_kinds:
    #     obstypes.append((kind, inverted_obs_kind_nrs[kind]))

    # oso3 = oso1
    # oso3.df = combi_df #setattr(oso3, 'df', combi_df)
    # oso3.obstypes = obstypes #setattr(oso3, 'obstypes', obstypes)

    oso3 = oso1.append_obsseq([oso2, ])
    oso3.to_dart(f_output)

    import filecmp
    assert filecmp.cmp(f_output, f_expected)

    os.remove(f_output)


if __name__ == '__main__':
    test_concat_obsseq()