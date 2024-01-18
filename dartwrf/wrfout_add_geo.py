import os, sys
import netCDF4 as nc
from dartwrf.server_config import cluster

fields_old = ["XLAT_M",   "XLONG_M",      "CLAT",
                "XLONG_U",  "XLONG_V",     "XLAT_U",    "XLAT_V"]
fields_new = ["XLAT",     "XLONG",      "CLAT",
                "XLONG_U",  "XLONG_V",     "XLAT_U",    "XLAT_V"]

def run(geo_data_file, wrfout_file):
    """Add geogrid data to a wrfout file
    DART needs a georeference, but ideal.exe does not provide it

    Takes LAT,LON, mapfac from geogrid, so that they are consistent.
    Does not change E, F, HGT_M as they would alter the dynamics and have no impact on assimilation
    
    Args:
        geo_data_file (str): Path to WRF's geo_em file
        wrfout_file (str): Path to WRF history (wrfout) file
        
    Returns:
        None
    """

    debug = False

    print('updating geodata in', wrfout_file, 'from', geo_data_file)
    geo_ds = nc.Dataset(geo_data_file, 'r')
    wrfinp_ds = nc.Dataset(wrfout_file, 'r+')

    for old, new in zip(fields_old, fields_new):
        if debug:
            print('moving old field', old, 'into new field', new)
            print(geo_ds.variables[old][:].shape, wrfinp_ds.variables[new][:].shape)
        wrfinp_ds.variables[new][:] = geo_ds.variables[old][:]

    wrfinp_ds.close()
    geo_ds.close()

    # overwrite attributes
    os.system(cluster.ncks+' -A -x '+geo_data_file+' '+wrfout_file)


if __name__ == '__main__':
    """
    Example:
        $ ./wrfout_add_geo.py geo_em.d01.nc wrfinput_d01
    """
    geo_data_file = sys.argv[1]  # '/home/fs71386/lkugler/compile_WRF/WPS-release-v4.2/geo_em.d01.nc'
    wrfout_file = sys.argv[2]  # '/home/fs71386/lkugler/DART/wrfinput_d01'

    run(geo_data_file, wrfout_file)
