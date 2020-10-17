"""Create obs_seq.in

"""
import os, sys, warnings
import numpy as np
import datetime as dt
from pysolar.solar import get_altitude, get_azimuth

# position on earth to calculate solar angles
lat0 = 45.
lon0 = 0.

sat_az = "180.0"
sat_zen = "45.0"

def degr_to_rad(degr):
    """Convert to DART convention = radians"""
    if degr < 0:
        degr += 360
    return degr/360*2*np.pi

def round_to_day(dtobj):
    return dtobj.replace(second=0, minute=0, hour=0)

def add_timezone_UTC(t):
    return dt.datetime(t.year, t.month, t.day, t.hour, t.minute, tzinfo=dt.timezone.utc)

def get_dart_date(time_dt):
    # assumes input is UTC!
    days_since_010120 = 145731
    ref_day = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
    dart_date_day = str((time_dt - ref_day).days + days_since_010120)
    secs_thatday = str(int((time_dt - round_to_day(time_dt)).total_seconds()))
    return dart_date_day, secs_thatday

def calc_obs_locations(n_obs, coords_from_domaincenter=True,
                       distance_between_obs_km=9999, fpath_obs_locations=False):
    """Calculate coordinate pairs for locations

    Args:
        n_obs (int):
            number of observations (must be a square of an integer: 4, 9, 1000, ...)
        coords_from_domaincenter (bool):
            if False: spread observations evenly
            if True: spread from domaincenter, `distance_between_obs_km` apart
        distance_between_obs_km (int):
            only used when coords_from_domaincenter=True
        fpath_obs_locations (False or str):
            write an obs_coords.pkl, can be used to check observation locations
            if str, write to file

    Returns:
        list of (lat, lon) tuples
    """
    radius_earth_meters = 6.371*1E6

    coords = []
    if coords_from_domaincenter:
        """
        Create equally spaced grid for satellite observations every 4 km
        e.g. ny,nx = 10
        -> obs locations are from -5 to +5 times dy in south_north direction
        and from -5 to +5 times dx in west_east direction
        """
        nx, ny = int(np.sqrt(n_obs)), int(np.sqrt(n_obs))

        m_per_degree = 2*np.pi*radius_earth_meters/360
        distance_between_obs_meters = distance_between_obs_km*1000.
        dy_4km_in_degree = distance_between_obs_meters/m_per_degree

        for iy in range(int(-ny/2), int(ny/2+1)):
            for ix in range(int(-nx/2), int(nx/2+1)):

                lat = lat0 + iy*dy_4km_in_degree
                m_per_degree_x = 2*np.pi*radius_earth_meters*np.sin(lat/180*np.pi)/360
                dx_4km_in_degree = distance_between_obs_meters/m_per_degree_x
                lon = lon0 + ix*dx_4km_in_degree
                coords.append((lat, lon))
    else:
        """Observations spread evenly over domain"""
        fcoords = '/home/fs71386/lkugler/run_DART/geo_em.d01.nc'
        import xarray as xr
        ds = xr.open_dataset(fcoords)

        lons = ds.XLONG_M.isel(Time=0).values
        lats = ds.XLAT_M.isel(Time=0).values
        n_obs_x = int(np.sqrt(n_obs))
        dx = int(len(ds.south_north)/n_obs_x)
        skip = int(dx/2)

        for i in range(n_obs_x):
            for j in range(n_obs_x):
                coords.append((lats[skip+i*dx, skip+j*dx],
                               lons[skip+i*dx, skip+j*dx]))

    try:
        if fpath_obs_locations:
            import pickle
            os.makedirs(os.path.dirname(fpath_obs_locations), exist_ok=True)
            with open(fpath_obs_locations, 'wb') as f:
                pickle.dump(coords, f); print(fpath_obs_locations, 'saved.')
    except Exception as e:
        warnings.warn(str(e))
    assert len(coords) == n_obs, (len(coords), n_obs)
    return coords

def write_generic_obsseq(obs_name, obs_kind_nr, error_var, coords,
                         dart_date_day, secs_thatday, output_path):
    n_obs_str = str(int(n_obs))
    error_var = str(error_var)
    line_obstypedef = obs_kind_nr+' '+obs_name

    msg = """
 obs_sequence
obs_kind_definitions
           1
         """+line_obstypedef+"""
  num_copies:            0  num_qc:            0
  num_obs:            """+n_obs_str+"  max_num_obs:            "+n_obs_str+"""
  first:            1  last:            """+n_obs_str

    for i_obs in range(1, int(n_obs)+1):

        lon = coords[i_obs-1][1]
        lat = coords[i_obs-1][0]
        hgt_m = str(coords[i_obs-1][2])+'.000'

        lon_rad = str(degr_to_rad(lon))
        lat_rad = str(degr_to_rad(lat))

        # compile text
        if i_obs < int(n_obs):
            msg += """
 OBS            """+str(i_obs)+"""
          -1           """+str(i_obs+1)+"""          -1
obdef
loc3d
     """+lon_rad+"""        """+lat_rad+"""        """+hgt_m+"""     3
kind
         """+obs_kind_nr+"""
 """+secs_thatday+"""     """+dart_date_day+"""
  """+error_var
        if i_obs == int(n_obs):  # last_observation
            # compile text
            msg += """
 OBS            """+str(i_obs)+"""
          """+str(i_obs-1)+"""           -1          -1
obdef
loc3d
     """+lon_rad+"""        """+lat_rad+"""        """+hgt_m+"""     3
kind
         """+obs_kind_nr+"""
 """+secs_thatday+"""     """+dart_date_day+"""
  """+error_var

    fpath = output_path+'/obs_seq.in'
    try:
        os.remove(fpath)
    except OSError:
        pass

    with open(fpath, 'w') as f:
        f.write(msg)
        print(fpath, 'saved.')

def sat(time_dt, channel_id, coords, error_var, output_path='./'):
    """Create obs_seq.in

    Args:
        time_dt (dt.datetime): time of observation
        channel_id (int): SEVIRI channel number
            see https://nwp-saf.eumetsat.int/downloads/rtcoef_rttov12/ir_srf/rtcoef_msg_4_seviri_srf.html
        coords (list of 2-tuples with (lat,lon))
        error_var (float):
            gaussian error with this variance is added to the truth at observation time
        output_path (str): directory where `obs_seq.in` will be saved
    """
    # time_dt = add_timezone_UTC(time_dt)
    # time_dt = dt.datetime(2008, 7, 30, 15, 30, tzinfo=dt.timezone.utc)
    error_var = str(error_var)
    n_obs = len(coords)

    # Brightness temperature or Reflectance?
    channel_id = int(channel_id)
    if channel_id in [1, 2, 3, 12]:
        line_obstypedef = '         256 MSG_4_SEVIRI_BDRF'
        code = '256'
    else:
        line_obstypedef = '         255 MSG_4_SEVIRI_TB'
        code = '255'
    channel_id = str(channel_id)

    time_dt = add_timezone_UTC(time_dt)
    sun_az = str(get_azimuth(lat0, lon0, time_dt))
    sun_zen = str(90. - get_altitude(lat0, lon0, time_dt))
    print('sunzen', sun_zen, 'sunazi', sun_az)

    dart_date_day, secs_thatday = get_dart_date(time_dt)
    print('secs, days:', secs_thatday, dart_date_day)

    n_obs_str = str(int(n_obs))
    error_var = str(error_var)

    msg = """
 obs_sequence
obs_kind_definitions
           1
"""+line_obstypedef+"""
  num_copies:            0  num_qc:            0
  num_obs:            """+n_obs_str+"  max_num_obs:            "+n_obs_str+"""
  first:            1  last:            """+n_obs_str

    for i_obs in range(1, int(n_obs)+1):

        lon = coords[i_obs-1][1]
        lat = coords[i_obs-1][0]

        lon_rad = str(degr_to_rad(lon))
        lat_rad = str(degr_to_rad(lat))

        # compile text
        if i_obs < int(n_obs):
            msg += """
 OBS            """+str(i_obs)+"""
          -1           """+str(i_obs+1)+"""          -1
obdef
loc3d
     """+lon_rad+"""        """+lat_rad+"""        -888888.0000000000     -2
kind
         """+code+"""
 visir
   """+sat_az+"""        """+sat_zen+"""        """+sun_az+"""
   """+sun_zen+"""
          12           4          21           """+channel_id+"""
  -888888.000000000
           1
 """+secs_thatday+"""     """+dart_date_day+"""
  """+error_var
        if i_obs == int(n_obs):  # last_observation
            # compile text
            msg += """
 OBS            """+str(i_obs)+"""
          """+str(i_obs-1)+"""           -1          -1
obdef
loc3d
     """+lon_rad+"""        """+lat_rad+"""        -888888.0000000000     -2
kind
         """+code+"""
 visir
   """+sat_az+"""        """+sat_zen+"""        """+sun_az+"""
   """+sun_zen+"""
          12           4          21           """+channel_id+"""
  -888888.000000000
           1
 """+secs_thatday+"""     """+dart_date_day+"""
  """+error_var

    fpath = output_path+'/obs_seq.in'
    try:
        os.remove(fpath)
    except OSError:
        pass

    with open(fpath, 'w') as f:
        f.write(msg)
        print(fpath, 'saved.')


def calc_obs_locations_3d(coords, heights):
    # append height
    coords2 = []
    for i in range(len(coords)):
        for hgt_m in heights:
            coords2.append(coords[i] + (hgt_m,))

    n_obs = len(coords2)
    print('effective number of observations (with vertical levels):', n_obs,
          ' on each level:', len(coords))
    return coords2


def generic_obs(obs_type, time_dt, coords, error_var, output_path='./'):

    obs_codes = {'RASO_T': {'name': 'RADIOSONDE_TEMPERATURE', 'nr': '5'},
                 'RADAR': {'name': 'RADAR_REFLECTIVITY', 'nr': '37'}
                 }

    heights = np.arange(1000, 15001, 1000)
    coords = calc_obs_locations_3d(coords, heights)

    dart_date_day, secs_thatday = get_dart_date(time_dt)
    print('secs, days:', secs_thatday, dart_date_day)

    obs_name = obs_codes[obs_type]['name']
    obs_kind_nr = obs_codes[obs_type]['nr']

    write_generic_obsseq(obs_name, obs_kind_nr, error_var, coords,
                         dart_date_day, secs_thatday, output_path)


if __name__ == '__main__':
    time_dt = dt.datetime(2008, 7, 30, 15, 30)
    n_obs = 100
    channel_id = 1

    distance_between_obs_meters = 10000

    # error_var = 0.001
    # sat(time_dt, channel_id, n_obs, error_var, distance_between_obs_meters,
    #        output_path='./', fpath_obs_locations='./domain.pkl')

    error_var = (5.)**2
    generic_obs('RADAR', time_dt, n_obs, error_var, distance_between_obs_meters,
                output_path='./', fpath_obs_locations='./domain.pkl')

    # error_var = (0.5)**2
    # generic_obs('RASO_T', time_dt, n_obs, error_var, distance_between_obs_meters,
    #                 output
