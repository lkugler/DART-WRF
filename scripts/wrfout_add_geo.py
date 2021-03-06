"""Add geogrid data to wrfinput
this is needed for DART, but not provided by ideal.exe

take LAT,LON, mapfac from geogrid, so that they are consistent.
do not change E, F, HGT_M as they would alter the dynamics and have no impact on assimilation

example call:
    ./wrfout_add_geo.py geo_em.d01.nc wrfinput_d01
"""
import os, sys
import netCDF4 as nc

from config.cfg import exp, cluster

def run(geo_data_file, wrfout_file):
    geo_ds = nc.Dataset(geo_data_file, 'r')
    wrfinp_ds = nc.Dataset(wrfout_file, 'r+')

    fields_old = ["XLAT_M",   "XLONG_M",      "CLAT",
                  "XLONG_U",  "XLONG_V",     "XLAT_U",    "XLAT_V"]
    fields_new = ["XLAT",     "XLONG",      "CLAT",
                  "XLONG_U",  "XLONG_V",     "XLAT_U",    "XLAT_V"]

    for old, new in zip(fields_old, fields_new):
        print('moving old field', old, 'into new field', new)
        #print(geo_ds.variables[old][:].shape, wrfinp_ds.variables[new][:].shape)
        wrfinp_ds.variables[new][:] = geo_ds.variables[old][:]
        #print(wrfinp_ds.variables[new][:])

    wrfinp_ds.close()
    geo_ds.close()

    # overwrite attributes
    os.system(cluster.ncks+' -A -x '+geo_data_file+' '+wrfout_file)


if __name__ == '__main__':
    geo_data_file = sys.argv[1]  # '/home/fs71386/lkugler/compile_WRF/WPS-release-v4.2/geo_em.d01.nc'
    wrfout_file = sys.argv[2]  # '/home/fs71386/lkugler/DART/wrfinput_d01'

    run(geo_data_file, wrfout_file)
