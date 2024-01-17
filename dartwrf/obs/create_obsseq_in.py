"""The functions in here create obs_seq.in files.
These are the template files defining obs locations and metadata
according to which observations are generated and subsequently assimilated.
"""
import os, sys, warnings
import numpy as np
import datetime as dt
from pysolar.solar import get_altitude, get_azimuth

from dartwrf.server_config import cluster
from dartwrf import utils
from dartwrf.obs import calculate_obs_locations as col
from dartwrf.obs.obskind import obs_kind_nrs # dictionary string => DART internal indices

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


def _add_timezone_UTC(t):
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


def _write_file(msg, output_path='./'):
    try:
        os.remove(output_path)
    except OSError:
        pass

    with open(output_path, 'w') as f:
        f.write(msg)
        print(output_path, 'saved.')


def _append_hgt_to_coords(coords, heights):
    """Adds vertical position to list of coordinates
    
    if heights is a scalar, then all obs have the same height
    if heights is a list, then you get multiple levels

    Args:
        coords (list of 2-tuples): (lat, lon) in degrees north/east
        heights (float or list of float): height in meters
    
    Returns:
        list of 3-tuples
    """
    coords2 = []
    try:
        len(heights)  # fails with scalar
    except TypeError:
        heights = [heights, ]
        
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


def _determine_vert_coords(sat_channel, kind, obscfg):
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
        
        if 'height' in obscfg:
            # hypothetical height, only used for localization
            vert_coord_sys = "3"  # meters AMSL
            vert_coords = obscfg['height']
    return vert_coord_sys, vert_coords


def write_sat_angle_appendix(sat_channel, lat0, lon0, time_dt):
    """Writes metadata str for an observation inside obs_seq.out

    Args:
        sat_channel (int or False): False if not a satellite observation
        lat0 (float): latitude of point on earth
        lon0 (float): longitude of point on earth
        time_dt (dt.datetime): time of observation

    Returns:
        str
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

    Returns:
        str
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
                      output_path=cluster.dart_rundir+'/obs_seq.in'):
    """Create obs_seq.in with multiple obs types in one file

    Args:
        time_dt (dt.datetime): time of observation
        list_obscfg (list of dict): configuration for observation types

    Note:
        `list_obscfg` must have these keys: 
            - n_obs (int) : number of observations (must be a square of an integer: 4, 9, 1000, ...)
            - obs_locations (str or tuple) in ['square_array_from_domaincenter', 'square_array_evenly_on_grid', ] 
                                            or list of (lat, lon) coordinate tuples, in degrees north/east
            - error_generate (np.array)
            - error_assimilate (np.array or False) : False -> parameterized
            - cov_loc_radius_km (float)
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print('creating obs_seq.in:')
    time_dt = _add_timezone_UTC(time_dt)
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
            assert (lat < 90) & (lat > -90)
            assert (lon < 180) & (lon > -180)

        kind = obscfg['kind']
        print('obstype', kind)
        sat_channel = obscfg.get('sat_channel', False)

        # add observation locations in the vertical at different levels
        vert_coord_sys, vert_coords = _determine_vert_coords(sat_channel, kind, obscfg)
        coords = _append_hgt_to_coords(coords, vert_coords)
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
    _write_file(alltxt, output_path=output_path)


if __name__ == '__main__':
    # for testing
    time_dt = dt.datetime(2008, 7, 30, 13, 0)

    radar = dict(var_name='Radar reflectivity', unit='[dBz]',
                kind='RADAR_REFLECTIVITY', 
                n_obs=5776, obs_locations='square_array_evenly_on_grid',
                error_generate=2.5, error_assimilate=2.5,
                heights=range(2000, 14001, 2000),
                loc_horiz_km=20, loc_vert_km=2.5)

    create_obs_seq_in(time_dt, [radar],
                      output_path=utils.userhome+'/run_DART/obs_seq.in')

    if False:
        error_assimilate = 5.*np.ones(n_obs*len(radar['heights']))
        import assim_synth_obs as aso
        aso.replace_errors_obsseqout(cluster.dart_rundir+'/obs_seq.out', error_assimilate)


