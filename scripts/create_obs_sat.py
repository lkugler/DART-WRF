"""Create obs_seq.in

"""
import os, sys
import numpy as np
import datetime as dt
from pysolar.solar import get_altitude, get_azimuth

def degr_to_rad(degr):
    if degr < 0:
        degr += 360
    return degr/360*2*np.pi

def round_to_day(dtobj):
    return dtobj.replace(second=0, minute=0, hour=0)

def add_timezone_UTC(t):
    return dt.datetime(t.year, t.month, t.day, t.hour, t.minute, tzinfo=dt.timezone.utc)


def run(time_dt, n_obs, error_variance, output_path='./'):
    """Create obs_seq.in

    implemented for
        - reflectivity of VIS 0.6
    """


    time_dt = add_timezone_UTC(time_dt)
    # time_dt = dt.datetime(2008, 7, 30, 15, 30, tzinfo=dt.timezone.utc)
    assert n_obs == int(n_obs)
    n_obs_str = str(int(n_obs))
    error_variance = str(error_variance)

    # solar angles
    lat0 = 45.
    lon0 = 0.

    sat_az = "180.0"
    sat_zen = "45.0"
    radius_earth = 6.371*1E6

    # equally spaced grid for satellite observations every 4 km
    nx, ny = int(np.sqrt(n_obs)), int(np.sqrt(n_obs))
    coords = []

    km_per_degree = 2*np.pi*radius_earth/360
    dy_4km_in_degree = 4000/km_per_degree
    #print(dy_4km_in_degree)

    for iy in range(int(-ny/2), int(ny/2+1)):
        for ix in range(int(-nx/2), int(nx/2+1)):

            lat = lat0 + iy*dy_4km_in_degree
            km_per_degree_x = 2*np.pi*radius_earth*np.sin(lat/180*np.pi)/360
            dx_4km_in_degree = 4000/km_per_degree_x
            lon = lon0 + ix*dx_4km_in_degree

            coords.append((lat, lon))

    if False:
        import pickle
        with open('obs_coords.pkl', 'wb') as f:
            pickle.dump(coords, f)

    sun_az = str(get_azimuth(lat0, lon0, time_dt))
    sun_zen = str(90. - get_altitude(lat0, lon0, time_dt))
    print('sunzen', sun_zen, 'sunazi', sun_az)

    days_since_010120 = 145731
    ref_day = dt.datetime(2000,1,1, tzinfo=dt.timezone.utc)
    dart_date_day = str((time_dt - ref_day).days + days_since_010120)
    secs_thatday = str(int((time_dt - round_to_day(time_dt)).total_seconds()))
    print('secs, days:', secs_thatday, dart_date_day)

    msg = """
 obs_sequence
obs_kind_definitions
           1
         256 MSG_4_SEVIRI_BDRF
  num_copies:            0  num_qc:            0
  num_obs:            """+n_obs_str+"  max_num_obs:            "+n_obs_str+"""
  first:            1  last:            """+n_obs_str

    for i_obs in range(1, int(n_obs)+1):
        # data

        lon = coords[i_obs][1]
        lat = coords[i_obs][0]

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
         256
 visir
   """+sat_az+"""        """+sat_zen+"""        """+sun_az+"""
   """+sun_zen+"""
          12           4          21           1
  -888888.000000000
           1
 """+secs_thatday+"""     """+dart_date_day+"""
  """+error_variance
        if i_obs == int(n_obs):  # last_observation
            # compile text
            msg += """
 OBS            """+str(i_obs)+"""
          """+str(i_obs-1)+"""           -1          -1
obdef
loc3d
     """+lon_rad+"""        """+lat_rad+"""        -888888.0000000000     -2
kind
         256
 visir
   """+sat_az+"""        """+sat_zen+"""        """+sun_az+"""
   """+sun_zen+"""
          12           4          21           1
  -888888.000000000
           1
 """+secs_thatday+"""     """+dart_date_day+"""
  """+error_variance

    #print(msg)
    os.remove(output_path+'/obs_seq.in')
    with open(output_path+'/obs_seq.in', 'w') as f:
        f.write(msg)

if __name__ == '__main__':
    time_dt = dt.datetime(2008, 7, 30, 15, 30, tzinfo=dt.timezone.utc)
    n_obs = 100
    error_variance = str(.001)
    run(time_dt, n_obs, error_variance)
