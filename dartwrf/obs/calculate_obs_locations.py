"""The functions in here create obs_seq.in files.
These are the template files defining obs locations and metadata
according to which observations are generated and subsequently assimilated.
"""
import os, sys, warnings
import numpy as np
import datetime as dt
import xarray as xr

from config.cfg import exp
from config.clusters import cluster

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
            m_per_degree_x = 2*np.pi*radius_earth_meters*np.sin(lat/180*np.pi)/360
            dx_4km_in_degree = distance_between_obs_meters/m_per_degree_x
            lon = lon0_center + ix*dx_4km_in_degree
            coords.append((lat, lon))
    return coords

def evenly_on_grid(n_obs, omit_covloc_radius_on_boundary=True):
    """Observations spread evenly over domain
    
    omit_covloc_radius_on_boundary : leave out a distance to the border of the domain
                                     so that the assimilation increments are zero on the boundary
                                     distance to boundary = 50 km

    Returns
        tuple of (lat, lon) coordinates
    """
    fcoords = cluster.geo_em
    ds = xr.open_dataset(fcoords)

    lons = ds.XLONG_M.isel(Time=0).values
    lats = ds.XLAT_M.isel(Time=0).values
    n_obs_x = int(np.sqrt(n_obs))
    nx = len(ds.south_north)  # number of gridpoints in one direction
    model_dx_km = exp.model_dx/1000
    print('assuming', model_dx_km, 'km model grid')


    if omit_covloc_radius_on_boundary:  #  in order to avoid an increment step on the boundary
        skip_km = 50  
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

    coords = []
    for i in range(n_obs_x):
        for j in range(n_obs_x):
            coords.append((lats[skip_gridpoints+i*gridpoints_between_obs, skip_gridpoints+j*gridpoints_between_obs],
                            lons[skip_gridpoints+i*gridpoints_between_obs, skip_gridpoints+j*gridpoints_between_obs]))
    return coords