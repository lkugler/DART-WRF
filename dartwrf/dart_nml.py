import warnings
from dartwrf.utils import append_file
from dartwrf.exp_config import exp
from dartwrf.server_config import cluster

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
            
            if line == '/':
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

            # # ensure that we have list of strings
            # if isinstance(val, list) and len(val) == 1:
            #     val = [val]


            # try:
            #     # convert to float/int
            #     val = [float(v) for v in val]

            #     # convert to int when they are equal
            #     val = [int(v) for v in val if int(v)==v]
            # except:
            # it is not a numeric value => string
            val = [v.strip() for v in val]


            param_data.append(val)

            # print('this iteration var, val ...', {param: param_data})

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
                # print(parameters, [len(p) for p in parameters])
                max_width_of_parameter_name = max([len(p) for p in parameters])
                width = max_width_of_parameter_name + 1
            except:
                width = None
            
            for parameter in parameters:
                lines = d[section][parameter]

                # lines (list(list(str))): 
                # outer list: one element per line in the text file
                # inner list: one element per value in that line


                # we should have a list here
                # if we instead have a single value, then make a list
                # because we assume that lines consists of multiple lines
                assert isinstance(lines, list)

                for i, line in enumerate(lines):

                    assert isinstance(line, list)
                    if line == []:
                        line = ['',]
                    

                    first_entry = line[0]
                    if isinstance(first_entry, str) and not first_entry.startswith('.'):
                        try:
                            float(first_entry)
                            line = ', '.join(str(v) for v in line)
                        except:
                            # contains strings
                            line = [entry.strip("'").strip('"') for entry in line]  # remove pre-existing quotes
                            line = ', '.join('"'+v+'"' for v in line)
                    else:
                        # numerical values
                        line = ', '.join(str(v) for v in line)


                    if i == 0:
                        f.write('   '+parameter.ljust(width)+' = '+line+',\n')
                    else:
                        f.write('   '+' '*width+'   '+line+',\n')
            f.write('   /\n\n')


def _get_horiz_localization():
    """Compile the list of localizations for the DART namelist variables

    Args:
        exp (Experiment): Experiment object
    
    Returns:
        l_obstypes (list of str): entries for `special_vert_normalization_obs_types`
        l_loc_horiz_rad (list of str): entries for `special_localization_cutoffs`
    """
    def to_radian_horizontal(cov_loc_horiz_km):
        cov_loc_radian = cov_loc_horiz_km / earth_radius_km
        return cov_loc_radian

    l_obstypes_all = []  # list of all observation types
    l_loc_horiz_rad = []  # list of respective horizontal localization values

    for obscfg in exp.observations:
        l_obstypes_all.append(obscfg["kind"])

        # compute horizontal localization value
        loc_horiz_km = obscfg["loc_horiz_km"]
        if not loc_horiz_km >= 0:
            raise ValueError('Invalid value for `loc_horiz_km`, set loc_horiz_km >= 0 !')
        loc_horiz_rad = to_radian_horizontal(loc_horiz_km)
        l_loc_horiz_rad.append(loc_horiz_rad)

    return l_obstypes_all, l_loc_horiz_rad


def _get_vertical_localization():
    """Compile the list of vertical localizations for the DART namelist variables
    
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
        l_obstypes_vert (list of str): entries for `special_vert_normalization_obs_types`
        vert_norm_heights (list of str): entries for `special_vert_normalization_heights`
        vert_norm_scale_heights (list of str): entries for `special_vert_normalization_scale_heights`
        same for vert_norm_levels and vert_norm_pressures
    """

    def to_vertical_normalization(cov_loc_vert_km, cov_loc_horiz_km):
        vert_norm_rad = earth_radius_km * cov_loc_vert_km / cov_loc_horiz_km * 1000
        return vert_norm_rad
    
    l_obstypes_vert = []  # list of observation types that have vertical localization
    vert_norm_heights = []  # list of respective vertical localization values
    vert_norm_scale_heights = []  # list of respective vertical localization values (alternative to vert_norm_heights)
    vert_norm_levels = []
    vert_norm_pressures = []

    for obscfg in exp.observations:

        # if both loc_vert_km and loc_vert_scaleheight are False or not defined, then continue without localization
        if obscfg.get("loc_vert_km", False) == False and obscfg.get("loc_vert_scaleheight", False) == False:
            continue  # no vertical localization for this observation type, in all other cases we need it

        l_obstypes_vert.append(obscfg["kind"])
        
        try:  # do we localize by height?
            loc_vert_km = obscfg["loc_vert_km"]  
            loc_horiz_km = obscfg["loc_horiz_km"]

            vert_norm_hgt = to_vertical_normalization(loc_vert_km, loc_horiz_km)
            vert_norm_heights.append(vert_norm_hgt)

            # set the other (unused) list to a dummy value
            vert_norm_scale_heights.append(-1)
            vert_norm_levels.append(-1)
            vert_norm_pressures.append(-1)

        except KeyError:  # do we localize by scale height?
            try:
                loc_vert_scaleheight = obscfg["loc_vert_scaleheight"]

                # no conversion necessary, take the values as defined in obscfg
                vert_norm_scale_heights.append(loc_vert_scaleheight)

                # set the other (unused) list to a dummy value
                vert_norm_heights.append(-1)
                vert_norm_levels.append(-1)
                vert_norm_pressures.append(-1)

            except KeyError:  # if neither is defined

                # do we have vertical localization at all?
                # check parameter horiz_dist_only == true
                if exp.dart_nml['&location_nml']['horiz_dist_only'] == '.true.':
                    # no vertical localization => set all to dummy values
                    vert_norm_heights.append(-1)
                    vert_norm_scale_heights.append(-1)
                    vert_norm_levels.append(-1)
                    vert_norm_pressures.append(-1)
                else:
                    raise ValueError('DART namelist requires vertical localization, but neither `loc_vert_km` nor `loc_vert_scaleheight` are defined in obscfg.')
                
    return l_obstypes_vert, vert_norm_heights, vert_norm_scale_heights, vert_norm_levels, vert_norm_pressures



def write_namelist(just_prior_values=False):
    """Write a DART namelist file ('input.nml')
    
    1. Uses the default namelist (from the DART source code)
    2. Calculates localization parameters from the experiment configuration
    3. Overwrites other parameters as defined in the experiment configuration
    4. Writes the namelist to the DART run directory

    Note:
        Vertical localization in pressure or levels is not implemented.

    Args:
        just_prior_values (bool, optional): If True, only compute prior values, not posterior. Defaults to False.

    Raises:
        ValueError: If both height and scale-height localization are requested

    Returns:
        None
   """
    list_obstypes_all, list_loc_horiz_rad = _get_horiz_localization()
    
    vert_norm_obs_types, vert_norm_heights, vert_norm_scale_heights, vert_norm_levels, vert_norm_pressures = _get_vertical_localization() 

    nml = read_namelist(cluster.dart_srcdir + "/input.nml")

    n_obstypes = len(list_obstypes_all)
    if n_obstypes > 0:
        # make sure that observations defined in `exp.observations` are assimilated
        nml['&obs_kind_nml']['assimilate_these_obs_types'] = [list_obstypes_all]
        nml['&obs_kind_nml']['evaluate_these_obs_types'] = [[]]

        # write localization variables
        nml['&assim_tools_nml']['special_localization_obs_types'] = [list_obstypes_all]
        nml['&assim_tools_nml']['special_localization_cutoffs'] = [list_loc_horiz_rad]

        nml['&location_nml']['special_vert_normalization_obs_types'] = [vert_norm_obs_types]
        nml['&location_nml']['special_vert_normalization_heights'] = [vert_norm_heights]
        nml['&location_nml']['special_vert_normalization_scale_heights'] = [vert_norm_scale_heights]
        nml['&location_nml']['special_vert_normalization_levels'] = [vert_norm_levels]
        nml['&location_nml']['special_vert_normalization_pressures'] = [vert_norm_pressures]


    # overwrite namelist parameters as defined in the experiment configuration
    for section, sdata in exp.dart_nml.items():

        # if section is not in namelist, add it
        if section not in nml:
            nml[section] = {}

        for parameter, value in sdata.items():

            if isinstance(value, list) and len(value) > 1:  # it is a list

                if isinstance(value[0], list):
                    pass  # nothing to do, value is list(list())
                else:
                    value = [value]  # value was a list of parameter values, but just one line
            else:
                value = [[value]]  # value was a single entry

            # overwrite entry in each dictionary
            nml[section][parameter] = value  # every entry in this list is one line

    # necessary options if we dont compute posterior but only evaluate prior
    if just_prior_values:  
        nml['&obs_kind_nml']['assimilate_these_obs_types'] = [[]]
        nml['&obs_kind_nml']['evaluate_these_obs_types'] = [list_obstypes_all]

        nml['&filter_nml']['compute_posterior'] = [['.false.']]
        
        # inf_flavor posterior must be 0 if posterior is not computed
        # inf_flavor keyword exists, so we can just overwrite it
        # prior inf must be 0, because we only want to evaluate the prior, not assimilate anything
        nml['&filter_nml']['inf_flavor'] = [['0', '0']]

        nml['&filter_nml']['output_members'] = [['.false.']]
        nml['&filter_nml']['output_mean'] = [['.false.']]
        nml['&filter_nml']['output_sd'] = [['.false.']]

    # fail if horiz_dist_only == false but observations contain a satellite channel
    if nml['&location_nml']['horiz_dist_only'][0] == '.false.':
        for obscfg in exp.observations:
            if 'sat_channel' in obscfg:
                warnings.warn("Selected vertical localization, but observations contain satellite obs -> Bug in DART.")

    # write to file
    write_namelist_from_dict(nml, cluster.dart_rundir + "/input.nml")

    # append section for RTTOV
    rttov_nml = cluster.dartwrf_dir + "/templates/obs_def_rttov.VIS.nml"
    append_file(cluster.dart_rundir + "/input.nml", rttov_nml)
    # alternatively, we could do this in cfg.py or the template input.nml in DART's model/wrf/work folder

    return nml  # in case we want to access namelist settings in python
