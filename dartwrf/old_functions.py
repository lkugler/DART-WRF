def recycle_output():
    """Use output of assimilation (./filter) as input for another assimilation (with ./filter)
    Specifically, this copies the state fields from filter_restart_d01.000x to the wrfout files in advance_temp folders"""
    update_vars = ['U', 'V', 'T', 'PH', 'MU', 'QVAPOR', 'QCLOUD', 'QICE', 'QRAIN', 'U10', 'V10', 'T2', 'Q2', 'TSK', 'PSFC', 'CLDFRA']
    updates = ','.join(update_vars)

    print('recycle DART output to be used as input')
    for iens in range(1, exp.n_ens+1):
        dart_output = cluster.dartrundir+'/filter_restart_d01.'+str(iens).zfill(4)
        dart_input = cluster.dartrundir+'/advance_temp'+str(iens)+'/wrfout_d01'

        #print('check for non-monotonic vertical pressure')

        # convert link to file in order to be able to update the content
        if os.path.islink(dart_input):
            l = os.readlink(dart_input)
            os.remove(dart_input)
            copy(l, dart_input)

        # print('move DART output to input: '+dart_output+' -> '+dart_input)
        # os.rename(dart_output, dart_input)  # probably doesnt work

        print('updating', updates, 'in', dart_input, 'from', dart_output)
        os.system(cluster.ncks+' -A -v '+updates+' '+dart_output+' '+dart_input)


def run_Hx(time, obscfg):
    """
    # assumes that prior ensemble is already linked to advance_temp<i>/wrfout_d01
    Creates 
        obs_seq.final (file):       observations on (non-averaged) grid
    """
    get_obsseq_out(time)
    print("running H(x) : obs operator on ensemble prior")

    # set input.nml to calculate prior Hx 
    set_DART_nml(just_prior_values=True)

    # run filter to calculate prior Hx 
    shell("mpirun -np 12 ./filter &> log.filter.preassim")

    osf = obsseq.ObsSeq(cluster.dartrundir + "/obs_seq.final")

    if getattr(exp, "superob_km", False):
        df = osf.df
        print("superobbing to", exp.superob_km, "km")
        osf.df = osf.df.superob(window_km=exp.superob_km)
        osf.to_dart(cluster.dartrundir + "/obs_seq.final")
    return osf



def replace_errors_obsseqout(f, new_errors):
    """Replaces existing observation errors in obs_seq.final files

    new_errors (np.array) : standard deviation,
                            shape must match the number of observations
    """
    debug = True
    obsseq = open(f, "r").readlines()

    # find number of lines between two ' OBS   ' lines:
    first_obs = second_obs = None
    for i, line in enumerate(obsseq):
        if " OBS " in line:
            if first_obs is None:
                first_obs = i
            else:
                second_obs = i
                break
    if not second_obs:
        raise RuntimeError('just one OBS in this file?! '+str(f))
    lines_between = second_obs - first_obs
    lines_obserr_after_obsnr = lines_between - 1  # obserr line is one before ' OBS   ' line

    # replace values in list obsseq
    i_obs = 0
    for i, line in enumerate(obsseq):
        if " OBS " in line:
            line_error_obs_i = i + lines_obserr_after_obsnr

            previous_err_var = obsseq[line_error_obs_i]
            new_err_obs_i = new_errors[i_obs] ** 2  # variance in obs_seq.out
            if debug:
                print(
                    line.strip(),
                    "previous err var ",
                    float(previous_err_var.strip()),
                    "new error",
                    new_err_obs_i,
                )
            obsseq[line_error_obs_i] = " " + str(new_err_obs_i) + " \n"

            i_obs += 1  # next iteration

    with open(f, "w") as file:
        for line in obsseq:
            file.write(line)
    print("replaced obs errors in", f)



def obs_operator_nature(time):
    print("getting true values in obs space from nature run")
    prepare_nature_dart(time)
    run_perfect_model_obs()
    true, _ = read_truth_obs_obsseq(cluster.dartrundir + "/obs_seq.out")
    return true



def read_truth_obs_obsseq(f):
    """Reads observed and true values from obs_seq.out/final files."""
    obsseq = open(f, "r").readlines()
    true = []
    obs = []
    # read observations from obs_seq.out
    for i, line in enumerate(obsseq):
        if " OBS " in line:
            observed = float(obsseq[i + 1].strip())
            truth = float(obsseq[i + 2].strip())
            true.append(truth)
            obs.append(observed)
    return true, obs


def read_prior_obs(f_obs_prior):
    """
    docstring
    """
    obsseq = open(f_obs_prior, "r").readlines()
    OBSs = []
    # read observations from obs_seq.final
    for i, line in enumerate(obsseq):
        if " OBS " in line:
            observed = float(obsseq[i + 1].strip())
            truth = float(obsseq[i + 2].strip())
            prior_ensmean = float(obsseq[i + 3].strip())
            prior_enssd = float(obsseq[i + 4].strip())
            prior_ens = []
            for j in range(5, 5 + exp.n_ens):
                prior_ens.append(float(obsseq[i + j].strip()))

            OBSs.append(dict(observed=observed, truth=truth, prior_ens=np.array(prior_ens)))
    return OBSs