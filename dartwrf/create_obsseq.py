"""The functions in here create obs_seq.in files.
These are the template files defining obs locations and metadata
according to which observations are generated and subsequently assimilated.
"""
import os, sys, warnings
import numpy as np
import datetime as dt
from pysolar.solar import get_altitude, get_azimuth

from config.cfg import exp, cluster
from dartwrf.obs import calculate_obs_locations as col

def obskind_read():
    """Read dictionary of observation types + ID numbers ("kind") 
    from DART f90 script
    """

    definitionfile = cluster.dart_srcdir+'/../../../assimilation_code/modules/observations/obs_kind_mod.f90'
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


#####################
# Global variables
obs_kind_nrs = obskind_read()  # DART internal indices

# position on earth for RTTOV ray geometry
lat0 = 45.
lon0 = 0.
sat_az = "180.0"
sat_zen = "45.0"


def degr_to_rad(degr):
    """Convert to DART convention (radians)
    2*pi = 360 degrees
    
    Args:
        degr (float) : degrees east of Greenwich
        
    Returns 
        float
    """
    if degr < 0:
        degr += 360
    return degr/360*2*np.pi


def round_to_day(dtobj):
    """Overwrite hours, minutes, seconds to 0
    Args:
        dtobj (dt.datetime)
    """
    return dtobj.replace(second=0, minute=0, hour=0)


def add_timezone_UTC(t):
    return dt.datetime(t.year, t.month, t.day, t.hour, t.minute, tzinfo=dt.timezone.utc)


def get_dart_date(time_dt):
    """Convert datetime.datetime into DART time format
    
    Assumes that input is UTC!
    
    Returns
        str, str
    """
    days_since_010120 = 145731
    ref_day = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    dart_date_day = str((time_dt - ref_day).days + days_since_010120)
    secs_thatday = str(int((time_dt - round_to_day(time_dt)).total_seconds()))
    return dart_date_day, secs_thatday


def write_tuple_to_pickle(fpath_out, tuple):
    import pickle
    os.makedirs(os.path.dirname(fpath_out), exist_ok=True)
    with open(fpath_out, 'wb') as f:
        pickle.dump(tuple, f)
    print(fpath_out, 'saved.')

def write_file(msg, output_path='./'):
    try:
        os.remove(output_path)
    except OSError:
        pass

    with open(output_path, 'w') as f:
        f.write(msg)
        print(output_path, 'saved.')


def append_hgt_to_coords(coords, heights):
    coords2 = []
    for i in range(len(coords)):
        for hgt_m in heights:
            coords2.append(coords[i] + (hgt_m,))

    n_obs = len(coords2)
    print('effective number of observations (with vertical levels):', n_obs,
          ' on each level:', len(coords))
    return coords2


def preamble(n_obs_3d_total, list_kinds):
    """Writes the header of an obs_seq.out file
    """
    lines_obstypedef = ''
    for kind in list_kinds:
        lines_obstypedef += '\n         '+str(obs_kind_nrs[kind])+' '+kind

    n_obs_str = str(n_obs_3d_total)
    num_obstypes = str(len(list_kinds))
    return """ obs_sequence
obs_kind_definitions
           """+num_obstypes+' '+lines_obstypedef+"""
  num_copies:            0  num_qc:            0
  num_obs:            """+n_obs_str+"  max_num_obs:            "+n_obs_str+"""
  first:            1  last:            """+n_obs_str


def determine_vert_coords(sat_channel, kind, obscfg):
    if not sat_channel:
        if 'SYNOP' in kind:
            vert_coord_sys = "-1"  # meters AGL
            vert_coords = [2, ]
        else:
            vert_coord_sys = "3"  # meters AMSL
            vert_coords = obscfg['heights']
    else:
        vert_coord_sys = "-2"  # undefined height
        vert_coords = ["-888888.0000000000", ]
    return vert_coord_sys, vert_coords


def write_sat_angle_appendix(sat_channel, lat0, lon0, time_dt):
    """Writes metadata str for an observation inside obs_seq.out
    """
    if sat_channel:
        sun_az = str(get_azimuth(lat0, lon0, time_dt))
        sun_zen = str(90. - get_altitude(lat0, lon0, time_dt))
        print('sunzen', sun_zen, 'sunazi', sun_az)

        return """visir
    """+sat_az+"""        """+sat_zen+"""        """+sun_az+"""
    """+sun_zen+"""
            12           4          21           """+str(sat_channel)+"""
    -888888.000000000
            1"""
    else:
        return ''


def write_section(obs, last=False):
    """Returns the str of one observation inside an obs_seq.out file

    Args:
        obs (object)
        last (bool): True if this is the last observation in the obs_seq file
    """
    lon_rad = str(degr_to_rad(obs['lon']))
    lat_rad = str(degr_to_rad(obs['lat']))

    if last:
        line_link = "          "+str(obs['i']-1)+"           -1          -1"
    else:
        line_link = "        -1           "+str(obs['i']+1)+"          -1"
    
    return """
 OBS            """+str(obs['i'])+"""
"""+line_link+"""
obdef
loc3d
     """+lon_rad+"        "+lat_rad+"        "+str(obs['vert_coord'])+"     "+obs['vert_coord_sys']+"""
kind
         """+str(obs['kind_nr'])+"""
"""+obs['appendix']+"""
"""+obs['secs_thatday']+"""     """+obs['dart_date_day']+"""
"""+str(obs['obserr_var'])


def create_obs_seq_in(time_dt, list_obscfg, 
                             output_path=cluster.dartrundir+'/obs_seq.in'):
    """Create obs_seq.in with multiple obs types in one file

    Args:
        time_dt (dt.datetime): time of observation
        list_obscfg (list of dict) :    configuration for observation types
            must have keys: 
                - n_obs (int) : number of observations (must be a square of an integer: 4, 9, 1000, ...)
                - obs_locations (str or tuple) in ['square_array_from_domaincenter', 'square_array_evenly_on_grid', ] 
                                                or list of (lat, lon) coordinate tuples, in degrees north/east
                - error_generate (float)
                - error_assimilate (float or False) : False -> parameterized
                - cov_loc_radius_km (float)

        obs_errors (np.array): contains observation errors, one for each observation
    """
    print('creating obs_seq.in:')
    time_dt = add_timezone_UTC(time_dt)
    dart_date_day, secs_thatday = get_dart_date(time_dt)

    txt = ''
    i_obs_total = 0
    for i_cfg, obscfg in enumerate(list_obscfg):
        n_obs = obscfg['n_obs']

        if obscfg['obs_locations'] == 'square_array_from_domaincenter':
            coords = col.square_array_from_domaincenter(n_obs, 
                                                        obscfg['distance_between_obs_km'])  # <---- must have variable

        elif obscfg['obs_locations'] == 'square_array_evenly_on_grid':
            coords = col.evenly_on_grid(n_obs)

        else:  # obs_locations given by iterable
            coords = obscfg['obs_locations']

        assert len(coords) == n_obs, (len(coords), n_obs)  # check if functions did what they supposed to
        for lat, lon in coords:
            assert lat < 90 & lat > -90
            assert lon < 180 & lon > -180

        kind = obscfg['kind']
        print('obstype', kind)
        sat_channel = obscfg.get('sat_channel', False)

        # add observation locations in the vertical at different levels
        vert_coord_sys, vert_coords = determine_vert_coords(sat_channel, kind, obscfg)
        coords = append_hgt_to_coords(coords, vert_coords)
        n_obs_3d_thistype = len(coords)

        # user defined generation error
        obserr_std = np.zeros(n_obs_3d_thistype) + obscfg["error_generate"]

        sat_info = write_sat_angle_appendix(sat_channel, lat0, lon0, time_dt)

        for i_obs in range(n_obs_3d_thistype):
            i_obs_total += 1
            last = False

            is_last_obs_in_type = (i_obs == int(n_obs_3d_thistype)-1)
            is_last_obstype = (i_cfg == len(list_obscfg)-1)

            if is_last_obs_in_type and is_last_obstype:
                last = True

            txt += write_section(dict(i=i_obs_total,
                                    kind_nr=obs_kind_nrs[kind],
                                    dart_date_day=dart_date_day,
                                    secs_thatday=secs_thatday,
                                    lon=coords[i_obs][1],
                                    lat=coords[i_obs][0],
                                    vert_coord=coords[i_obs][2],
                                    vert_coord_sys=vert_coord_sys,
                                    obserr_var=obserr_std[i_obs]**2,
                                    appendix=sat_info),
                                last=last)
            
    n_obs_total = i_obs_total
    list_kinds = [a['kind'] for a in list_obscfg]
    pretxt = preamble(n_obs_total, list_kinds)

    alltxt = pretxt + txt
    write_file(alltxt, output_path=output_path)


if __name__ == '__main__':
    # for testing
    time_dt = dt.datetime(2008, 7, 30, 13, 0)


    vis = dict(plotname='VIS 0.6µm',  plotunits='[1]',
            kind='MSG_4_SEVIRI_BDRF', sat_channel=1, 
            n_obs=961, obs_locations='square_array_evenly_on_grid',
            error_generate=0.03, error_assimilate=0.06,
            cov_loc_radius_km=32)

    # wv62 = dict(plotname='Brightness temperature WV 6.2µm', plotunits='[K]',
    #             kind='MSG_4_SEVIRI_TB', sat_channel=5, 
    #             n_obs=n_obs, obs_locations='square_array_evenly_on_grid',
    #             error_generate=1., error_assimilate=False, 
    #             cov_loc_radius_km=20)

    # wv73 = dict(plotname='Brightness temperature WV 7.3µm',  plotunits='[K]',
    #             kind='MSG_4_SEVIRI_TB', sat_channel=6, 
    #             n_obs=n_obs, obs_locations='square_array_evenly_on_grid',
    #             error_generate=1., error_assimilate=False,
    #             cov_loc_radius_km=20)

    # ir108 = dict(plotname='Brightness temperature IR 10.8µm', plotunits='[K]',
    #             kind='MSG_4_SEVIRI_TB', sat_channel=9, 
    #             n_obs=n_obs, obs_locations='square_array_evenly_on_grid',
    #             error_generate=5., error_assimilate=10.,
    #             cov_loc_radius_km=32)

    radar = dict(plotname='Radar reflectivity', plotunits='[dBz]',
                kind='RADAR_REFLECTIVITY',             
                n_obs=1, obs_locations=[(45,0),],
                error_generate=2.5, error_assimilate=5.,
                heights=np.arange(1000, 15001, 1000),
                cov_loc_radius_km=20, cov_loc_vert_km=4)

    # t2m = dict(plotname='SYNOP Temperature', plotunits='[K]',
    #         kind='SYNOP_TEMPERATURE',             
    #         n_obs=n_obs, obs_locations='square_array_evenly_on_grid',
    #         error_generate=0.1, error_assimilate=1.,
    #         cov_loc_radius_km=20, cov_loc_vert_km=3)

    # psfc = dict(plotname='SYNOP Pressure', plotunits='[dBz]',
    #             kind='SYNOP_SURFACE_PRESSURE', 
    #             n_obs=n_obs, obs_locations='square_array_evenly_on_grid',
    #             error_generate=50., error_assimilate=100.,
    #             cov_loc_radius_km=32, cov_loc_vert_km=5)


    create_obs_seq_in(time_dt, [radar])

    if False:
        error_assimilate = 5.*np.ones(n_obs*len(radar['heights']))
        import assim_synth_obs as aso
        aso.replace_errors_obsseqout(cluster.dartrundir+'/obs_seq.out', error_assimilate)


