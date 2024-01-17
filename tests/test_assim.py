import os, shutil

def test_dartwrf_cycled_da():
    import datetime as dt
    
    from dartwrf.workflows import WorkFlows
    w = WorkFlows(exp_config='exp_template.py', server_config='jet.py')

    timedelta_integrate = dt.timedelta(minutes=15)
    timedelta_btw_assim = dt.timedelta(minutes=15)

    id = None

    if True:  # random
        # need some ensemble data to test
        prior_path_exp = '/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P2_noDA+1'

        init_time = dt.datetime(2008, 7, 30, 12, 30)
        time = dt.datetime(2008, 7, 30, 13)
        last_assim_time = dt.datetime(2008, 7, 30, 13)
        forecast_until = dt.datetime(2008, 7, 30, 13,10)

        w.prepare_WRFrundir(init_time)
        # id = w.run_ideal(depends_on=id)

    prior_init_time = init_time

    while time <= last_assim_time:

        # usually we take the prior from the current time
        # but one could use a prior from a different time from another run
        # i.e. 13z as a prior to assimilate 12z observations
        prior_valid_time = time

        id = w.assimilate(time, prior_init_time, prior_valid_time, prior_path_exp, depends_on=id)
        
        # 1) Set posterior = prior
        id = w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time, depends_on=id)

        # 2) Update posterior += updates from assimilation
        id = w.update_IC_from_DA(time, depends_on=id)

        # How long shall we integrate?
        timedelta_integrate = timedelta_btw_assim
        output_restart_interval = timedelta_btw_assim.total_seconds()/60
        if time == last_assim_time:  # this_forecast_init.minute in [0,]:  # longer forecast every full hour
            timedelta_integrate = forecast_until - last_assim_time  # dt.timedelta(hours=4)
            output_restart_interval = 9999  # no restart file after last assim

        # 3) Run WRF ensemble
        id = w.run_ENS(begin=time,  # start integration from here
                    end=time + timedelta_integrate,  # integrate until here
                    output_restart_interval=output_restart_interval,
                    first_minutes=False,
                    depends_on=id)
        
        # as we have WRF output, we can use own exp path as prior
        prior_path_exp = w.cluster.archivedir

        time += timedelta_btw_assim
        prior_init_time = time - timedelta_btw_assim
    

def test_overwrite_OE_assim():
    import datetime as dt
    from dartwrf import assimilate as aso
    from dartwrf.obs import obsseq
    from dartwrf.server_config import cluster

    # checks if modified entries are correctly written to DART files
    input_template = "./obs_seq.orig.out"
    input_temporary = "./obs_seq.out"
    # TODO: MISSING FILE
    # input_osf = "./obs_seq.final"
    output = "./obs_seq.test.out"
    shutil.copy(input_template, input_temporary)

    oso = obsseq.ObsSeq(input_temporary)
    #osf = obsseq.ObsSeq(input_osf)

    aso.set_obserr_assimilate_in_obsseqout(oso, outfile=output)

    var_orig = oso.df['variance']

    oso_test = obsseq.ObsSeq(output)  # read in again
    assert oso_test.df['variance'].iloc[0] == var_orig
    os.remove(output)
    os.remove(input_temporary)

if __name__ == '__main__':
    # test_dartwrf_cycled_da()
    # test_overwrite_OE_assim()
    pass
