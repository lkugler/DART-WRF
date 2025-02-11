
def obskind_read(dart_srcdir: str) -> dict:
    """Read dictionary of observation types + ID numbers ("kind") 
    from DART f90 script and return it as python dictionary
    """
    definitionfile = dart_srcdir + \
        '/../../../assimilation_code/modules/observations/obs_kind_mod.f90'
    with open(definitionfile, 'r') as f:
        kind_def_f = f.readlines()

    obskind_nrs = {}
    for i, line in enumerate(kind_def_f):
        if 'Integer definitions for DART OBS TYPES' in line:
            # data starts below this line
            i_start = i
            break
    for line in kind_def_f[i_start+1:]:
        if 'MAX_DEFINED_TYPES_OF_OBS' in line:
            # end of data
            break
        if '::' in line:
            # a line looks like this
            # integer, parameter, public ::       MSG_4_SEVIRI_TB =   261
            data = line.split('::')[-1].split('=')
            kind_str = data[0].strip()
            kind_nr = int(data[1].strip())
            obskind_nrs[kind_str] = kind_nr
    return obskind_nrs