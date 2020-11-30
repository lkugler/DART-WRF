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
                       distance_between_obs_km=9999, folder_obs_coords=False):
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

def main_obspart(obs, last=False):
    """
    Args:
    obs (object)
    last (bool): True if this is the last observation in the obs_seq file
    """
    if last:
        line_link = "          "+str(obs.i-1)+"           -1          -1"
    else:
        line_link = "        -1           "+str(obs.i+1)+"          -1"
    
    return """
 OBS            """+str(obs.i)+"""
"""+line_link+"""
obdef
loc3d
     """+obs.lon_rad+"        "+obs.lat_rad+"        "+obs.vert+"     "+obs.vert_coord_sys+"""
kind
         """+obs.kind_nr+"""
 """+obs.secs_thatday+"""     """+obs.dart_date_day+"""
  """+obs.error_var

def write_generic_obsseq(obs_name, obs_kind_nr, error_var, coords,
                         dart_date_day, secs_thatday, output_path,
                         vert_coord_sfc=False):
    """
    Args:
        dart_date_day (str): DART internal time formatted date
        secs_thatday (str): DART internal time of day (seconds since 0 UTC)
        vert_coord_sfc (bool):
            if True, then vertical coordinate is height above ground, i.e. "surface observation"
            if False, then vertical is hgt_AMSL
    """

    vert_coord_sys = 3  # meters AMSL
    if vert_coord_sfc:
        vert_coord_sys = -1

    n_obs = len(coords)
    n_obs_str = str(n_obs)
    error_var = str(error_var)
    line_obstypedef = obs_kind_nr+' '+obs_name
    vert_coord_sys = str(vert_coord_sys)

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
        hgt_m = str(coords[i_obs-1][2])

        lon_rad = str(degr_to_rad(lon))
        lat_rad = str(degr_to_rad(lat))

        # compile text
        if i_obs < int(n_obs):
            msg += """
 OBS            """+str(i_obs)+"""
          -1           """+str(i_obs+1)+"""          -1
obdef
loc3d
     """+lon_rad+"        "+lat_rad+"        "+hgt_m+"     "+vert_coord_sys+"""
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
     """+lon_rad+"        "+lat_rad+"        "+hgt_m+"     "+vert_coord_sys+"""
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


def generic_obs(obs_kind, time_dt, coords, error_var, heights=False, output_path='./'):

    obs_kind_nrs = {'RADIOSONDE_TEMPERATURE': '5',
                    'RADAR_REFLECTIVITY': '37',
                    'SYNOP_SURFACE_PRESSURE': '94',
                    'SYNOP_SPECIFIC_HUMIDITY': '95',
                    'SYNOP_TEMPERATURE': '96',
                    }

    if 'SYNOP' in obs_kind:
        is_sfc_obs = True
        heights = [2,]
    else:
        is_sfc_obs = False

    if not heights:
        heights = [5000., ]
    coords = calc_obs_locations_3d(coords, heights)

    dart_date_day, secs_thatday = get_dart_date(add_timezone_UTC(time_dt))
    print('secs, days:', secs_thatday, dart_date_day)

    obs_kind_nr = obs_kind_nrs[obs_kind]
    write_generic_obsseq(obs_kind, obs_kind_nr, error_var, coords,
                         dart_date_day, secs_thatday, output_path,
                         vert_coord_sfc=is_sfc_obs)

def obskind_read():
    raw_obskind_dart = """
                    5 RADIOSONDE_TEMPERATURE
                    6 RADIOSONDE_SPECIFIC_HUMIDITY
                    12 AIRCRAFT_U_WIND_COMPONENT
                    13 AIRCRAFT_V_WIND_COMPONENT
                    14 AIRCRAFT_TEMPERATURE
                    16 ACARS_U_WIND_COMPONENT
                    17 ACARS_V_WIND_COMPONENT
                    18 ACARS_TEMPERATURE
                    29 LAND_SFC_PRESSURE
                    30 SAT_U_WIND_COMPONENT
                    31 SAT_V_WIND_COMPONENT
                    36 DOPPLER_RADIAL_VELOCITY
                    37 RADAR_REFLECTIVITY
                    83 GPSRO_REFRACTIVITY
                    94 SYNOP_SURFACE_PRESSURE
                    95 SYNOP_SPECIFIC_HUMIDITY
                    96 SYNOP_TEMPERATURE
                254 MSG_4_SEVIRI_RADIANCE
                255 MSG_4_SEVIRI_TB
                256 MSG_4_SEVIRI_BDRF"""

    # lookup table for kind nr
    alist = raw_obskind_dart.split()
    assert len(alist) % 2 == 0, alist
    obskind_nrs = {}
    for i in range(0, len(alist)-1, 2):
        obskind_nrs[alist[i+1]] = alist[i]
    return obskind_nrs

obskind_nrs = obskind_read()


def create_obsseq_in(obscfg, obserr_var):
    """
    Args:
    obserr_var (np.array): observation error variance
        shape (n_obs,), one value for each observation, 
    """

    self.coords = osq.calc_obs_locations(obscfg['n_obs'], 
                        coords_from_domaincenter=False, 
                        distance_between_obs_km=obscfg.get('distance_between_obs_km', False), 
                        fpath_obs_locations=folder_obs_coords+'/obs_coords_'+obscfg['kind']+'.pkl')

    #     for i_obs in obscfg['n_obs']:

    #         instruction = dict(kind_nr = obskind_nrs[obscfg['kind']],
    #                            sat_channel = obscfg.get('sat_channel', False),
    #                            heights = obscfg.get('heights', False),
                             
    # obs_kinds, time_dt, coords, error_var, heights=False, output_path='./'):

    if 'SYNOP' in obs_kind:
        is_sfc_obs = True
        heights = [2,]
    else:
        is_sfc_obs = False

    if not heights:
        heights = [5000., ]
    coords = calc_obs_locations_3d(coords, heights)

    dart_date_day, secs_thatday = get_dart_date(add_timezone_UTC(time_dt))
    print('secs, days:', secs_thatday, dart_date_day)

    obs_kind_nr = obs_kind_nrs[obs_kind]

    for obs_kind in obs_kinds:

        write_generic_obsseq2(obs_kind, obs_kind_nr, error_var, coords,
                            dart_date_day, secs_thatday, output_path,
                            vert_coord_sfc=is_sfc_obs)

if __name__ == '__main__':
    time_dt = dt.datetime(2008, 7, 30, 10, 0)
    n_obs = 64
    sat_channel = 1

    distance_between_obs_meters = 10000
    #error_var = 0.001
    obs_coords = calc_obs_locations(n_obs, coords_from_domaincenter=False, 
                                            distance_between_obs_km=distance_between_obs_meters, 
                                            fpath_obs_locations=None)
    #sat(time_dt, sat_channel, obs_coords, error_var, output_path='./')

    # error_var = (5.)**2
    # generic_obs('RADAR_REFLECTIVITY', time_dt, obs_coords, error_var, heights=[5000.,], output_path='./')

    error_var = (0.5)**2
    generic_obs('RADIOSONDE_TEMPERATURE', time_dt, obs_coords, error_var, heights=[5000.,])
