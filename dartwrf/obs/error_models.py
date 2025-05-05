import numpy as np
from scipy.interpolate import interp1d

def calc_obserr_WV(channel, Hx_nature, Hx_prior):
    """Calculate parametrized error (for assimilation)

    Args:
        channel (str):          satellite channel
        Hx_nature (np.array):   H(x_nature) with dimension (observations)
        Hx_prior (np.array):    H(x_prior) with dimension (ensemble_members, observations)

    Returns
        np.array        Observation error std-deviation with dimension (observations)
    """
    if channel not in ['WV62', 'WV73']:
        raise NotImplementedError("channel not implemented: " + channel)
    debug = True

    n_obs = len(Hx_nature)
    OEs = np.ones(n_obs)
    for iobs in range(n_obs):
        bt_y = Hx_nature[iobs]
        bt_x_ens = Hx_prior[:, iobs]
        
        # compute Cloud impact for every pair (ensemble, truth)
        CIs = [_cloudimpact(channel, bt_x, bt_y) for bt_x in bt_x_ens]
        mean_CI = np.mean(CIs)

        if channel == 'WV62':
            oe_model = _OE_model_harnisch_WV62(mean_CI)
        elif channel == 'WV73':
            oe_model = _OE_model_new73(mean_CI)
        
        if debug:
            print("bt_y=", bt_y, "bt_x_ens=", bt_x_ens)
            print("CIs=", CIs)
            print("=> mean_CI=", mean_CI, "=> OE_assim=", oe_model)
        
        OEs[iobs] = oe_model
    return OEs


def _cloudimpact(channel, bt_mod, bt_obs):
    """
    follows Harnisch 2016, Figure 3
    """
    if channel == 'WV73':
        biascor_obs = 0
        # bt_lim = 252  # Kelvin for 7.3 micron WV channel
        bt_lim = 255.0  # new
    elif channel == 'WV62':
        biascor_obs = 0
        bt_lim = 232.5  # Kelvin for 6.2 micron WV channel

    ci_obs = max(0, bt_lim - (bt_obs - biascor_obs))
    ci_mod = max(0, bt_lim - bt_mod)
    ci = (ci_obs + ci_mod) / 2
    return ci


def _OE_model_harnisch_WV62(ci):
    if ci >= 0 and ci < 7.5:
        # Kelvin, fit of Fig 7a, Harnisch 2016
        x_ci = [0, 2.5, 4.5, 5.5, 7.5]  # average cloud impact [K]
        y_oe = [1.2, 3, 5, 6, 6.5]  # adjusted observation error [K]
        oe_linear = interp1d(x_ci, y_oe, assume_sorted=True)
        return oe_linear(ci)
    else:  # assign highest observation error
        return 6.5


def _OE_model_harnisch_WV73(ci):
    if ci >= 0 and ci < 16:
        # Kelvin, fit of Fig 7b, Harnisch 2016
        x_ci = [0, 5, 10.5, 13, 16]  # average cloud impact [K]
        y_oe = [1, 4.5, 10, 12, 13]  # adjusted observation error [K]
        oe_linear = interp1d(x_ci, y_oe, assume_sorted=True)
        return oe_linear(ci)
    else:  # assign highest observation error
        return 13.0

def _OE_model_new73(ci):
    # based on exp_nat250_WV73_obs6_loc6_oe2_inf3
    if ci >= 0 and ci < 25:
        x_ci = [0, 5, 10, 15, 25]  # average cloud impact [K]
        y_oe = [1, 2, 9, 10.5, 7]  # adjusted observation error [K]
        oe_linear = interp1d(x_ci, y_oe, assume_sorted=True)
        return oe_linear(ci)
    else:
        return 7.0

