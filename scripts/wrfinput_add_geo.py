#!/home/fs71386/lkugler/miniconda3/envs/DART/bin/python
#!/jetfs/home/lkugler/miniconda3/envs/DART/bin/python

"""Add geogrid data to wrfinput
this is needed for DART, but not provided by ideal.exe

take LAT,LON, mapfac from geogrid, so that they are consistent.
do not change E, F, HGT_M as they would alter the dynamics and have no impact on assimilation

example call:
    ./wrfinput_add_geo.py geo_em.d01.nc wrfinput_d01

"""
import os, sys
import netCDF4 as nc
#import xarray as xr

geo_data_file = sys.argv[1]  # '/home/fs71386/lkugler/compile_WRF/WPS-release-v4.2/geo_em.d01.nc'
wrfinput_file = sys.argv[2]  # '/home/fs71386/lkugler/DART/wrfinput_d01'


geo_ds = nc.Dataset(geo_data_file, 'r')
wrfinp_ds = nc.Dataset(wrfinput_file, 'r+')
#wrfinp_ds = xr.open_dataset(geo_data_file)

"""
  geog_field_names = (/  "XLAT_M",   "XLONG_M",      "CLAT",     "CLONG",   \
                          "HGT_M", "MAPFAC_M",   "MAPFAC_U",  "MAPFAC_V",   \
                      "MAPFAC_MX", "MAPFAC_MY", "MAPFAC_UX", "MAPFAC_UY",   \
                      "MAPFAC_VX", "MAPFAC_VY",  "SINALPHA",  "COSALPHA",   \
                              "E",         "F", \
                        "XLONG_U",  "XLONG_V",     "XLAT_U",    "XLAT_V"/)
  tmpl_field_names = (/    "XLAT",     "XLONG",      "CLAT",     "CLONG",  \
                            "HGT",  "MAPFAC_M",  "MAPFAC_U",  "MAPFAC_V",  \
                      "MAPFAC_MX", "MAPFAC_MY", "MAPFAC_UX", "MAPFAC_UY",  \
                      "MAPFAC_VX", "MAPFAC_VY",  "SINALPHA",  "COSALPHA",  \
                              "E",         "F", \
                        "XLONG_U",  "XLONG_V",     "XLAT_U",    "XLAT_V"/)
"""

fields_old = ["XLAT_M",   "XLONG_M",      "CLAT",
              "MAPFAC_M",   "MAPFAC_U",  "MAPFAC_V",
                "MAPFAC_MX", "MAPFAC_MY", "MAPFAC_UX", "MAPFAC_UY",
                "MAPFAC_VX", "MAPFAC_VY",  "SINALPHA",  "COSALPHA",
                "XLONG_U",  "XLONG_V",     "XLAT_U",    "XLAT_V"]
fields_new = ["XLAT",     "XLONG",      "CLAT",
               "MAPFAC_M",  "MAPFAC_U",  "MAPFAC_V",
                "MAPFAC_MX", "MAPFAC_MY", "MAPFAC_UX", "MAPFAC_UY",
                "MAPFAC_VX", "MAPFAC_VY",  "SINALPHA",  "COSALPHA",
                "XLONG_U",  "XLONG_V",     "XLAT_U",    "XLAT_V"]

for old, new in zip(fields_old, fields_new):
    print(old, new)
    print(geo_ds.variables[old][:].shape, wrfinp_ds.variables[new][:].shape)
    wrfinp_ds.variables[new][:] = geo_ds.variables[old][:]
    print(wrfinp_ds.variables[new][:])

wrfinp_ds.close()
geo_ds.close()