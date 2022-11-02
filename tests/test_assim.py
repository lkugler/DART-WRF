import os, shutil
import datetime as dt

from dartwrf import obsseq, assim_synth_obs
from config.cfg import cluster

class ExperimentConfiguration(object):
    def __init__(self):
        pass

exp = ExperimentConfiguration()
exp.expname = "test"

obscfg_wv73 = dict(plotname='Brightness temperature WV 7.3µm',  plotunits='[K]',
                kind='MSG_4_SEVIRI_TB', sat_channel=6, n_obs=4,
                error_generate=1., error_assimilate=False,
                cov_loc_radius_km=32)
exp.observations = [obscfg_wv73]

time = dt.datetime(2008,7,30,12)


def test_overwrite_OE_assim():
    # checks if modified entries are correctly written to DART files
    input_template = cluster.scriptsdir + "/../tests/obs_seq.orig.out"
    input_temporary = cluster.scriptsdir + "/../tests/obs_seq.out"
    # TODO: MISSING FILE
    # input_osf = cluster.scriptsdir + "/../tests/obs_seq.final"
    output = cluster.scriptsdir + "/../tests/obs_seq.test.out"
    shutil.copy(input_template, input_temporary)

    oso = obsseq.ObsSeq(input_temporary)
    osf = obsseq.ObsSeq(input_osf)

    assim_synth_obs.set_obserr_assimilate_in_obsseqout(oso, osf, outfile=output)

    var_orig = oso.df['variance']

    oso_test = obsseq.ObsSeq(output)  # read in again
    assert oso_test.df['variance'].iloc[0] == var_orig
    os.remove(output)
    os.remove(input_temporary)

if __name__ == '__main__':
    test_overwrite_OE_assim()
