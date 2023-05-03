from dartwrf.utils import append_file

from config.cfg import exp
from config.cluster import cluster

earth_radius_km = 6370

def read_namelist(filepath):
    """Read the DART namelist file into a dictionary.
    
    Args:
        filepath (str): Path to namelist file
    
    Returns:
        dict: keys are namelist sections, values are dictionaries of namelist variables
    """
    
    d = dict()
    # read file into a list of strings
    with open(filepath, 'r') as f:
        lines = f.readlines()

    for line in lines:
        # skip whitespace
        line = line.strip()

        # skip comments
        if not line.startswith('#'):

            # skip empty lines
            if len(line) > 0:

                # namelist section
                if line.startswith('&'):
                    section = line
                    d[section] = dict()
                    continue
                
                if '/' in line:
                    continue  # skip end of namelist section

                try:
                    # split line into variable name and value
                    var, val = line.split('=')
                    val = val.strip().strip(',').strip()

                except ValueError:
                    # If the above split failed, we are still, we are still in the previous variable
                    nextline_values = line.strip().split(',').strip()
                    val = val + nextline_values

                # add variable to dictionary
                d[section][var] = val
    return d


def write_namelist_from_dict(d, filepath):
    """Write a DART namelist dictionary to a file.
    
    Args:
        d (dict): keys are namelist sections, values are dictionaries of namelist variables
        filepath (str): Path to namelist file
    """
    with open(filepath, 'w') as f:
        for section in d:
            f.write(section+'\n')
            for var in d[section]:
                val = d[section][var]
                if isinstance(val, list):
                    val = ', '.join(val)
                f.write('\t '+var+' = '+str(val)+'\n')
            f.write('\t /\n\n')


def _get_list_of_localizations():
    """Compile the list of localizations for the DART namelist variables

    Vertical localization can be defined in section &location_nml of 'input.nml'
    using following namelist variables:
        special_vert_normalization_obs_types     (list of str)
        special_vert_normalization_pressures     (list of float)
        special_vert_normalization_heights       (list of float)
        special_vert_normalization_levels        (list of float)
        special_vert_normalization_scale_heights (list of float)

    To use scale height normalization, set obsdict['loc_vert_scaleheight'] = 0.5
    To use height normalization, set obsdict['loc_vert_km'] = 3.0

    Args:
        exp (Experiment): Experiment object
    
    Returns:
        l_obstypes (list of str): entries for `special_vert_normalization_obs_types`
        l_loc_horiz_rad (list of str): entries for `special_localization_cutoffs`
        l_loc_vert_km (list of str): entries for `special_vert_normalization_heights`
        l_loc_vert_scaleheight (list of str): entries for `special_vert_normalization_scale_heights`
    """
    def to_radian_horizontal(cov_loc_horiz_km):
        cov_loc_radian = cov_loc_horiz_km / earth_radius_km
        return cov_loc_radian

    def to_vertical_normalization(cov_loc_vert_km, cov_loc_horiz_km):
        vert_norm_rad = earth_radius_km * cov_loc_vert_km / cov_loc_horiz_km * 1000
        return vert_norm_rad

    l_obstypes = []
    l_loc_horiz_rad = []
    l_loc_vert_km = []
    l_loc_vert_scaleheight = []

    for obscfg in exp.observations:

        l_obstypes.append(obscfg["kind"])
        loc_horiz_km = obscfg["loc_horiz_km"]

        # compute horizontal localization
        loc_horiz_rad = str(to_radian_horizontal(loc_horiz_km))
        l_loc_horiz_rad.append(loc_horiz_rad)

        # compute vertical localization

        # choose either localization by height or by scale height
        if hasattr(obscfg, "loc_vert_km") and hasattr(obscfg, "loc_vert_scaleheight"):
            raise ValueError("Observation config contains both loc_vert_km and loc_vert_scaleheight. Please choose one.")
        
        elif hasattr(obscfg, "loc_vert_km"):  # localization by height
            loc_vert_km = str(obscfg["loc_vert_km"])

            vert_norm_hgt = to_vertical_normalization(loc_vert_km, loc_horiz_km)
            l_loc_vert_km.append(vert_norm_hgt)

        elif hasattr(obscfg, "loc_vert_scaleheight"):  # localization by scale height
            loc_vert_scaleheight = str(obscfg["loc_vert_scaleheight"])

            # no conversion necessary, take the values as defined in obscfg
            l_loc_vert_scaleheight.append(loc_vert_scaleheight)


    # fail when both localization by height and scale height are requested
    if len(l_loc_vert_km) > 0 and len(l_loc_vert_scaleheight) > 0:
        raise ValueError("List of observation configurations contain both height and scale-height localization. Please choose one.")
    
    # set the other (unused) list to a dummy value
    if len(l_loc_vert_km) > 0:
        l_loc_vert_scaleheight = [-1,]
    else:
        l_loc_vert_km = [-1,]
    
    return l_obstypes, l_loc_horiz_rad, l_loc_vert_km, l_loc_vert_scaleheight


def write_namelist(just_prior_values=False):
    """Set DART namelist variables in 'input.nml' file.
    
    1. Takes the default namelist is the one already defined in the DART source code
    2. Calculates localization parameters from the observation configurations
    3. Overwrites other parameters as defined in the experiment configuration
    4. Writes the namelist to the DART run directory

    Args:
        just_prior_values (bool, optional): If True, only compute prior values, not posterior. Defaults to False.

    Raises:
        ValueError: If both height and scale-height localization are requested

    Returns:
        None
   """
    list_obstypes, list_loc_horiz_rad, list_loc_vert_km, list_loc_vert_scaleheight = _get_list_of_localizations()

    nml = read_namelist(cluster.dart_srcdir + "/input.nml")

    # make sure that observations defined in `exp.observations` are assimilated
    nml['&obs_kind_nml']['assimilate_these_obs_types'] = list_obstypes
    
    # dont compute posterior, just evaluate prior
    if just_prior_values:  
        nml['&filter_nml']['compute_posterior'] = '.false.'
        nml['&filter_nml']['output_members'] = '.false.'
        nml['&filter_nml']['output_mean'] = '.false.'
        nml['&filter_nml']['output_sd'] = '.false.'
        nml['&obs_kind_nml']['assimilate_these_obs_types'] = []
        nml['&obs_kind_nml']['evaluate_these_obs_types'] = list_obstypes


    # write localization variables
    nml['&assim_tools_nml']['special_localization_obs_types'] = list_obstypes
    nml['&assim_tools_nml']['special_localization_cutoffs'] = list_loc_horiz_rad

    nml['&location_nml']['special_vert_normalization_obs_types'] = list_obstypes
    nml['&location_nml']['special_vert_normalization_heights'] = list_loc_vert_km
    nml['&location_nml']['special_vert_normalization_scale_heights'] = list_loc_vert_scaleheight


    # overwrite namelist with DART-WRF/config/ configuration
    for key, value in exp.dart_nml.items():

        # if key is not in namelist, add it
        if key not in nml:
            nml[key] = {}

        # overwrite entry in each dictionary
        nml[key] = value


    # final checks
    # fail if horiz_dist_only == false but observations contain a satellite channel
    if nml['&location_nml']['horiz_dist_only'] == '.false.':
        for obscfg in exp.observations:
            if hasattr(obscfg, "sat_channel"):
                raise ValueError("Selected vertical localization, but observations contain satellite obs -> Not possible.")

    # write to file
    write_namelist_from_dict(nml, cluster.dart_rundir + "/input.nml")

    # append section for RTTOV
    rttov_nml = cluster.scriptsdir + "/../templates/obs_def_rttov.VIS.nml"
    append_file(cluster.dart_rundir + "/input.nml", rttov_nml)