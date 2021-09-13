"""The functions in here create obs_seq.in files.
These are the template files defining obs locations and metadata
according to which observations are generated and subsequently assimilated.
"""
import os, sys, warnings
import numpy as np
import datetime as dt
from config.cfg import exp, cluster
from pysolar.solar import get_altitude, get_azimuth


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


#####################
# Global variables

# position on earth for RTTOV ray geometry
lat0 = 45.
lon0 = 0.

# position on Earth for DART, domain center when coords_from_domaincenter=True
lat0_center = 45.
lon0_center = 0.

sat_az = "180.0"
sat_zen = "45.0"

obs_kind_nrs = obskind_read()


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
                       distance_between_obs_km=9999, cov_loc_radius_km=32, fpath_coords=False):
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

                lat = lat0_center + iy*dy_4km_in_degree
                m_per_degree_x = 2*np.pi*radius_earth_meters*np.sin(lat/180*np.pi)/360
                dx_4km_in_degree = distance_between_obs_meters/m_per_degree_x
                lon = lon0_center + ix*dx_4km_in_degree
                coords.append((lat, lon))
    else:
        """Observations spread evenly over domain
        but: leave out a distance to the border of the domain
        so that the assimilation increments are zero on the boundary
        distance to boundary = 1.5x localization-radius
        """
        fcoords = cluster.dartrundir+'/geo_em.d01.nc'
        import xarray as xr
        ds = xr.open_dataset(fcoords)

        lons = ds.XLONG_M.isel(Time=0).values
        lats = ds.XLAT_M.isel(Time=0).values
        n_obs_x = int(np.sqrt(n_obs))
        nx = len(ds.south_north)  # number of gridpoints in one direction
        model_dx_km = exp.model_dx/1000

        omit_covloc_radius_on_boundary = True
        if omit_covloc_radius_on_boundary:  #  in order to avoid an increment step on the boundary
            skip_km = 50  # cov_loc_radius_km*1.5
            skip_gridpoints = int(skip_km/model_dx_km)  # skip this many gridpoints on each side

            gridpoints_left = nx - 2*skip_gridpoints
            # now spread observations evenly across the space left
            gridpoints_between_obs = int(gridpoints_left/(n_obs_x-1))
        else:
            gridpoints_between_obs = int(nx/n_obs_x)  # number of gridpoints / number of observations in one direction
            skip_gridpoints = int(gridpoints_between_obs/2)    # to center the observations in the domain
        
        km_between_obs = gridpoints_between_obs*model_dx_km
        print('observation density: one observation every', km_between_obs, 'km /', 
        gridpoints_between_obs,'gridpoints \n', 'leaving a domain boundary on each side of', 
        skip_gridpoints, 'gridpoints or', skip_gridpoints*model_dx_km, 'km')
        # skip_gridpoints = space we have to leave out on the boundary of the domain
        # in order to have the observations centered in the domain

        for i in range(n_obs_x):
            for j in range(n_obs_x):
                coords.append((lats[skip_gridpoints+i*gridpoints_between_obs, skip_gridpoints+j*gridpoints_between_obs],
                               lons[skip_gridpoints+i*gridpoints_between_obs, skip_gridpoints+j*gridpoints_between_obs]))
    try:
        if fpath_coords:
            import pickle
            os.makedirs(os.path.dirname(fpath_coords), exist_ok=True)
            with open(fpath_coords, 'wb') as f:
                pickle.dump(coords, f)
                print(fpath_coords, 'saved.')
    except Exception as e:
        warnings.warn(str(e))
    assert len(coords) == n_obs, (len(coords), n_obs)
    return coords


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


def preamble(n_obs, line_obstypedef):
    n_obs_str = str(n_obs)
    return """ obs_sequence
obs_kind_definitions
           1
"""+line_obstypedef+"""
  num_copies:            0  num_qc:            0
  num_obs:            """+n_obs_str+"  max_num_obs:            "+n_obs_str+"""
  first:            1  last:            """+n_obs_str


def preamble_multi(n_obs_3d_total, list_kinds):
    lines_obstypedef = ''
    for kind in list_kinds:
        lines_obstypedef += '\n         '+obs_kind_nrs[kind]+' '+kind

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
    """
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
         """+obs['kind_nr']+"""
"""+obs['appendix']+"""
"""+obs['secs_thatday']+"""     """+obs['dart_date_day']+"""
"""+str(obs['obserr_var'])


def create_obsseq_in_separate_obs(time_dt, obscfg, obs_errors=False,
                     archive_obs_coords=False):
    """Create obs_seq.in of one obstype

    Args:
        time_dt (dt.datetime): time of observation
        obscfg (dict)
        obs_errors (int, np.array) : values of observation errors (standard deviations)
            e.g. 0 = use zero error
        archive_obs_coords (str, False): path to folder

    channel_id (int): SEVIRI channel number
        see https://nwp-saf.eumetsat.int/downloads/rtcoef_rttov12/ir_srf/rtcoef_msg_4_seviri_srf.html
        
    coords (list of 2-tuples with (lat,lon))
    obserr_std (np.array): shape (n_obs,), one value for each observation, 
        gaussian error with this std-dev is added to the truth at observation time
    archive_obs_coords (bool, str): False or str (filepath where `obs_seq.in` will be saved)
    """

    n_obs = obscfg['n_obs']
    coords = calc_obs_locations(n_obs, 
                coords_from_domaincenter=False, 
                distance_between_obs_km=obscfg.get('distance_between_obs_km', False), 
                fpath_coords=archive_obs_coords)

    kind = obscfg['kind']
    sat_channel = obscfg.get('sat_channel', False)

    # determine vertical coordinates
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

    coords = append_hgt_to_coords(coords, vert_coords)
    n_obs_3d = len(coords)

    # define obs error
    obserr_std = np.zeros(n_obs_3d) 
    if obs_errors:
        obserr_std += obs_errors

    # other stuff for obsseq.in
    obs_kind_nr = obs_kind_nrs[kind]
    line_obstypedef = '         '+obs_kind_nr+' '+kind

    time_dt = add_timezone_UTC(time_dt)
    dart_date_day, secs_thatday = get_dart_date(time_dt)
    print('secs, days:', secs_thatday, dart_date_day)

    if sat_channel:
        sun_az = str(get_azimuth(lat0, lon0, time_dt))
        sun_zen = str(90. - get_altitude(lat0, lon0, time_dt))
        print('sunzen', sun_zen, 'sunazi', sun_az)

        appendix = """visir
   """+sat_az+"""        """+sat_zen+"""        """+sun_az+"""
   """+sun_zen+"""
          12           4          21           """+str(sat_channel)+"""
  -888888.000000000
           1"""
    else:
        appendix = ''

    txt = preamble(n_obs_3d, line_obstypedef)

    for i_obs in range(n_obs_3d):
        last = False
        if i_obs == int(n_obs_3d)-1:
            last = True  # last_observation

        txt += write_section(dict(i=i_obs+1,
                                  kind_nr=obs_kind_nr,
                                  dart_date_day=dart_date_day,
                                  secs_thatday=secs_thatday,
                                  lon=coords[i_obs][1],
                                  lat=coords[i_obs][0],
                                  vert_coord=coords[i_obs][2],
                                  vert_coord_sys=vert_coord_sys,
                                  obserr_var=obserr_std[i_obs]**2,
                                  appendix=appendix),
                             last=last)

    write_file(txt, output_path=cluster.dartrundir+'/obs_seq.in')


def create_obsseqin_alltypes(time_dt, list_obscfg, obs_errors, archive_obs_coords=False):
    """Create obs_seq.in with multiple obs types in one file

    Args:
        time_dt (dt.datetime): time of observation
        list_obscfg (list of dict)
        obs_errors (list of float, False): contains observation errors, one for each observation
              if False: use zero error
        archive_obs_coords (bool, str): False or str (filepath where `obs_seq.in` will be saved)
    """
    print('creating obs_seq.in:')
    time_dt = add_timezone_UTC(time_dt)
    dart_date_day, secs_thatday = get_dart_date(time_dt)
    # print('secs, days:', secs_thatday, dart_date_day)

    txt = ''
    
    i_obs_total = 0
    for istage, obscfg in enumerate(list_obscfg):
        n_obs = obscfg['n_obs']

        coords = calc_obs_locations(n_obs, 
                    coords_from_domaincenter=False, 
                    distance_between_obs_km=obscfg.get('distance_between_obs_km', False), 
                    cov_loc_radius_km=obscfg['cov_loc_radius_km'],
                    fpath_coords=archive_obs_coords)

        kind = obscfg['kind']
        print('obstype', kind)
        sat_channel = obscfg.get('sat_channel', False)

        vert_coord_sys, vert_coords = determine_vert_coords(sat_channel, kind, obscfg)
        coords = append_hgt_to_coords(coords, vert_coords)
        n_obs_3d_thistype = len(coords)

        # define obs error
        if obs_errors == False:  
            obs_errors = np.zeros(n_obs_3d_thistype)
        assert len(obs_errors) == n_obs_3d_thistype, 'len(obs_errors) == n_obs_3d_thistype'
        obserr_std = obs_errors #np.zeros(n_obs_3d_thistype) 
        #if obs_errors:
        #    obserr_std += obscfg[obs_errors]

        sat_info = write_sat_angle_appendix(sat_channel, lat0, lon0, time_dt)

        for i_obs in range(n_obs_3d_thistype):
            i_obs_total += 1
            last = False

            is_last_obs_in_type = (i_obs == int(n_obs_3d_thistype)-1)
            is_last_obstype = (istage == len(list_obscfg)-1)

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
    pretxt = preamble_multi(n_obs_total, list_kinds)

    alltxt = pretxt + txt
    write_file(alltxt, output_path=cluster.dartrundir+'/obs_seq.in')



if __name__ == '__main__':
    # for testing
    time_dt = dt.datetime(2008, 7, 30, 9, 0)
    n_obs = 900  # radar: n_obs for each observation height level

    vis = dict(plotname='VIS 0.6µm',  plotunits='[1]',
            kind='MSG_4_SEVIRI_BDRF', sat_channel=1, n_obs=n_obs,
            error_generate=0.03, error_assimilate=0.06,
            cov_loc_radius_km=32)

    wv73 = dict(plotname='Brightness temperature WV 7.3µm',  plotunits='[K]',
                kind='MSG_4_SEVIRI_TB', sat_channel=6, n_obs=n_obs,
                error_generate=1., error_assimilate=False,
                cov_loc_radius_km=32)

    ir108 = dict(plotname='Brightness temperature IR 10.8µm', plotunits='[K]',
                kind='MSG_4_SEVIRI_TB', sat_channel=9, n_obs=n_obs,
                error_generate=5., error_assimilate=10.,
                cov_loc_radius_km=32)

    radar = dict(plotname='Radar reflectivity', plotunits='[dBz]',
                kind='RADAR_REFLECTIVITY', n_obs=n_obs,
                error_generate=2.5, error_assimilate=5.,
                heights=np.arange(1000, 15001, 1000),
                cov_loc_radius_km=32, cov_loc_vert_km=4)

    t2m = dict(plotname='SYNOP Temperature', plotunits='[K]',
            kind='SYNOP_TEMPERATURE', n_obs=n_obs,
            error_generate=0.1, error_assimilate=1.,
            cov_loc_radius_km=20, cov_loc_vert_km=3)

    psfc = dict(plotname='SYNOP Pressure', plotunits='[dBz]',
                kind='SYNOP_SURFACE_PRESSURE', n_obs=n_obs,
                error_generate=50., error_assimilate=100.,
                cov_loc_radius_km=32, cov_loc_vert_km=5)

    #create_obsseq_in(time_dt, radar, archive_obs_coords=False) #'./coords_stage1.pkl')

    create_obsseqin_alltypes(time_dt, [vis, wv73], obs_errors='error_generate', archive_obs_coords='./obs_coords.pkl')

    error_assimilate = 5.*np.ones(n_obs*len(radar['heights']))
    import assim_synth_obs as aso
    #aso.replace_errors_obsseqout(cluster.dartrundir+'/obs_seq.out', error_assimilate)


