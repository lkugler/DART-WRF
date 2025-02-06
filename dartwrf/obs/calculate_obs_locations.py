"""The functions in here create obs_seq.in files.
These are the template files defining obs locations and metadata
according to which observations are generated and subsequently assimilated.
"""
import os
import sys
import warnings
import numpy as np
import datetime as dt
import xarray as xr

from dartwrf.exp_config import exp
from dartwrf.server_config import cluster

#####################
# Global variables

# position on Earth for DART, domain center when coords_from_domaincenter=True
lat0_center = 45.
lon0_center = 0.

radius_earth_meters = 6.371*1E6


def square_array_from_domaincenter(n_obs, distance_between_obs_km):
    """
    Create equally spaced grid for satellite observations every 4 km
    e.g. ny,nx = 10
    -> obs locations are from -5 to +5 times dy in south_north direction
    and from -5 to +5 times dx in west_east direction

    Returns
        tuple of (lat, lon) coordinates
    """
    coords = []
    nx, ny = int(np.sqrt(n_obs)), int(np.sqrt(n_obs))

    m_per_degree = 2*np.pi*radius_earth_meters/360
    distance_between_obs_meters = distance_between_obs_km*1000.
    dy_4km_in_degree = distance_between_obs_meters/m_per_degree

    for iy in range(int(-ny/2), int(ny/2+1)):
        for ix in range(int(-nx/2), int(nx/2+1)):

            lat = lat0_center + iy*dy_4km_in_degree
            m_per_degree_x = 2*np.pi*radius_earth_meters * \
                np.sin(lat/180*np.pi)/360
            dx_4km_in_degree = distance_between_obs_meters/m_per_degree_x
            lon = lon0_center + ix*dx_4km_in_degree
            coords.append((lat, lon))
    return coords


def evenly_on_grid(km_between_obs, skip_border_km=0):
    """Observations spread evenly over domain

    skip_border_km : no observations within this distance to the border

    Returns
        tuple of (lat, lon) coordinates of observed gridpoints in degrees
    """
    fcoords = cluster.geo_em_nature
    ds = xr.open_dataset(fcoords)

    lons = ds.XLONG_M.isel(Time=0).values
    lats = ds.XLAT_M.isel(Time=0).values

    domain_width = len(ds.south_north)  # number of gridpoints in one direction
    assert domain_width == len(ds.west_east), 'domain is not square'
    
    try:
        grid_dx_km = float(ds.attrs['DX'])/1000
    except Exception as e:
        raise KeyError('DX not found in file '+fcoords) from e
    
    # skip this many gridpoints to the border
    skip_gridpoints = int(skip_border_km/grid_dx_km)
    gridpoints_observed = domain_width - 2*skip_gridpoints

    # now spread observations evenly across the space left
    gridpoints_between_obs = int(km_between_obs/grid_dx_km)

    # number of observations in one direction
    # +1 because 100 gridpoints with dx=10 can fit 11 observations
    n_obs_x = int(gridpoints_observed/gridpoints_between_obs) + 1

    # for info
    print('no observations within', skip_gridpoints, 'gridpoints or', skip_gridpoints*grid_dx_km, 'km to the border.')
    print('grid resolution [km]=', grid_dx_km, ', shape of domain=', lons.shape, ', observed gridpoints:', gridpoints_observed)
    print('gridpoints_between_obs=', gridpoints_between_obs, '=>', n_obs_x, 'observations in one direction')
    print('total number of observations=', n_obs_x**2) 

    coords = []
    for i_obs in range(n_obs_x):
        for j_obs in range(n_obs_x):
            i_grid = skip_gridpoints+i_obs*gridpoints_between_obs
            j_grid = skip_gridpoints+j_obs*gridpoints_between_obs

            coords.append((lats[i_grid, j_grid], lons[i_grid, j_grid]))

    print('first observation at gridpoint', skip_gridpoints,', last observation at gridpoint', i_grid)
    return coords


if __name__ == '__main__':
    
    evenly_on_grid(12, skip_border_km=16)