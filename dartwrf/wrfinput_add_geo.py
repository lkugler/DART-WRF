"""Add geogrid data to wrfinput. 
DART needs a georeference, but ideal.exe does not provide it

Takes LAT,LON, mapfac from geogrid, so that they are consistent.
Does not change E, F, HGT_M as they would alter the dynamics and have no impact on assimilation

example call:
    ./wrfinput_add_geo.py geo_em.d01.nc wrfinput_d01

"""
import os, sys
import netCDF4 as nc
from dartwrf.utils import Config

def run(cfg: Config) -> None:
    
    geo_ds = nc.Dataset(cfg.geo_data_file, 'r')
    wrfinp_ds = nc.Dataset(cfg.wrfinput_file, 'r+')

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
        print('moving old field', old, 'into new field', new)
        print(geo_ds.variables[old][:].shape, wrfinp_ds.variables[new][:].shape)
        wrfinp_ds.variables[new][:] = geo_ds.variables[old][:]
        print(wrfinp_ds.variables[new][:])

    wrfinp_ds.close()
    geo_ds.close()

    # overwrite attributes
    os.system(cfg.ncks+' -A -x '+cfg.geo_data_file+' '+cfg.wrfinput_file)


if __name__ == '__main__':
    cfg = Config.from_file(sys.argv[1])
    run(cfg)
