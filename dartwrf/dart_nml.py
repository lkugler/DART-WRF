from dartwrf.utils import append_file

from config.cfg import exp
from config.cluster import cluster

earth_radius_km = 6370

def read_namelist(filepath):
    """Read the DART namelist file into a dictionary.
    
    Args:
        filepath (str): Path to namelist file
    
    Returns:
        dict: namelist[section][parameter] = [[arg1, arg2,], [arg3, arg4]]
    """
    
    d = dict()
    # read file into a list of strings
    with open(filepath, 'r') as f:
        lines = f.readlines()

    for line in lines:
        # skip whitespace
        line = line.strip()

        if line.startswith('#') or line.startswith('!'):
            continue  # skip this line

        # skip empty lines
        if len(line) > 0:

            # namelist section
            if line.startswith('&'):
                section = line
                d[section] = dict()
                continue
            
            if '/' in line:
                continue  # skip end of namelist section

            line = line.strip().strip(',')

            try:
                # split line into variable name and value
                param, val = line.split('=')
                param = param.strip()

                param_data = []

            except ValueError:
                # If the above split failed, 
                # then there is additional data for the previous variable
                val = line  # in this line, there is only param_data
                # param is still the one from previously

            val = val.strip().strip(',').split(',')

            # ensure that we have strings
            if isinstance(val, list):
                val = [str(v) for v in val]
            else:
                val = [str(val)]

            param_data.append(val)

            print('this iteration var, val ...', {param: param_data})

            # add variable to dictionary
            d[section][param] = param_data
    return d

def write_namelist_from_dict(d, filepath):
    """Write a DART namelist dictionary to a file.
    
    Args:
        d (dict): keys are namelist sections, values are dictionaries.
                    these dictionaries contain keys (=parameters) and values (list type)
                    every item in values is a line (list type)
                    every line contains possibly multiple entries
        filepath (str): Path to namelist file
    """
    with open(filepath, 'w') as f:
        for section in d:
            f.write(section+'\n')

            try:
                parameters = d[section].keys()
                print(parameters, [len(p) for p in parameters])
                max_width_of_parameter_name = max([len(p) for p in parameters])
                width = max_width_of_parameter_name + 1
            except:
                width = None
            
            for parameter in parameters:
                lines = d[section][parameter]

                if isinstance(lines, str):
                    lines = [lines,]

                for i, line in enumerate(lines):

                    try:
                        line = ', '.join(line)  # write line (is a list)
                    except:
                        pass


                    if i == 0:
                        f.write('   '+parameter.ljust(width)+' = '+line+'\n')
                    else:
                        f.write('   '+' '*width+' = '+line+'\n')
            f.write('   /\n\n')


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
        l_loc_vert_scaleheight = ["-1",]
    else:
        l_loc_vert_km = ["-1",]
    
    return l_obstypes, l_loc_horiz_rad, l_loc_vert_km, l_loc_vert_scaleheight


def _to_fortran_list(l):
    """Ensure formatting as "arg1", "arg2", """
    assert isinstance(l, list)

    if len(l) > 1:  # multiple entries
        return ', '.join(['"'+v+'"' for v in l])
    elif len(l) == 1:  # single entry
        return '"'+l[0]+'"'
    else:  # no entry
        return '' 

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
    nml['&obs_kind_nml']['assimilate_these_obs_types'] = _to_fortran_list(list_obstypes)
    
    # dont compute posterior, just evaluate prior
    if just_prior_values:  
        nml['&filter_nml']['compute_posterior'] = '.false.'
        nml['&filter_nml']['output_members'] = '.false.'
        nml['&filter_nml']['output_mean'] = '.false.'
        nml['&filter_nml']['output_sd'] = '.false.'
        nml['&obs_kind_nml']['assimilate_these_obs_types'] = []
        nml['&obs_kind_nml']['evaluate_these_obs_types'] = [_to_fortran_list(list_obstypes)]


    # write localization variables
    nml['&assim_tools_nml']['special_localization_obs_types'] = [_to_fortran_list(list_obstypes)]
    nml['&assim_tools_nml']['special_localization_cutoffs'] = [_to_fortran_list(list_loc_horiz_rad)]

    nml['&location_nml']['special_vert_normalization_obs_types'] = [_to_fortran_list(list_obstypes)]
    nml['&location_nml']['special_vert_normalization_heights'] = [_to_fortran_list(list_loc_vert_km)]
    nml['&location_nml']['special_vert_normalization_scale_heights'] = [_to_fortran_list(list_loc_vert_scaleheight)]

    print(nml['&location_nml']['special_vert_normalization_obs_types'])

    # overwrite namelist with experiment configuration
    for section, sdata in exp.dart_nml.items():

        # if section is not in namelist, add it
        if section not in nml:
            nml[section] = {}

        for parameter, value in sdata.items():

            if isinstance(value, list) and len(value) > 1:  # it is a real list
                value = [value]  # value was a list of parameter values, but just one line
            else:
                value = [[value]]  # value was a single entry

            # overwrite entry in each dictionary
            nml[section][parameter] = value  # every entry in this list is one line

    # final checks
    # fail if horiz_dist_only == false but observations contain a satellite channel
    if nml['&location_nml']['horiz_dist_only'][0] == '.false.':
        for obscfg in exp.observations:
            if hasattr(obscfg, "sat_channel"):
                raise ValueError("Selected vertical localization, but observations contain satellite obs -> Not possible.")

    # write to file
    write_namelist_from_dict(nml, cluster.dart_rundir + "/input.nml")

    # append section for RTTOV
    rttov_nml = cluster.scriptsdir + "/../templates/obs_def_rttov.VIS.nml"
    append_file(cluster.dart_rundir + "/input.nml", rttov_nml)