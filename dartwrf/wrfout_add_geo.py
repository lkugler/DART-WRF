import os
import netCDF4 as nc
from dartwrf.utils import Config

fields_old = ["XLAT_M",   "XLONG_M",]
             # "XLONG_U",  "XLONG_V",     
             # "XLAT_U",    "XLAT_V"]
# DART expects XLAT, XLAT_U, XLAT_V, XLONG_U, XLONG_V
fields_new = ["XLAT",     "XLONG",]
             # "XLONG_U",  "XLONG_V",
             # "XLAT_U",    "XLAT_V"]


def run(cfg: Config, 
        geo_data_file: str,
        wrfout_file: str) -> None: #geo_data_file, wrfout_file):
    """Add geogrid data to a wrfout file
    DART needs a georeference, but ideal.exe does not provide it

    Takes LAT,LON, mapfac from geogrid, so that they are consistent.
    Does not change E, F, HGT_M as they would alter the dynamics and have no impact on assimilation

    Args:
        cfg, needs attributes: geo_em_forecast (str), ncks (str)
        wrfout_file (str): Path to WRF history (wrfout) file

    Returns:
        None
    """
    print('updating geodata in', wrfout_file, 'from', geo_data_file)
    geo_ds = nc.Dataset(geo_data_file, 'r')
    wrfinp_ds = nc.Dataset(wrfout_file, 'r+')
    # print('wrfinput.variables', list(wrfinp_ds.variables))
    # print('geo_em.variables',  list(geo_ds.variables))

    for old, new in zip(fields_old, fields_new):

        # check
        if old not in list(geo_ds.variables):
            if old.endswith('_M'):
                old = old[:-2]  # without _M
            
            if old not in list(geo_ds.variables):
                raise KeyError(old, 'not in', geo_data_file, 'variables')

        geo_em_coord = geo_ds.variables[old][:]

        # check
        if new not in list(wrfinp_ds.variables):
            raise KeyError(new, 'not in', wrfout_file, 'variables',
                    'however, DART expects this variable to localize impact etc!')

        wrfinp_ds.variables[new][:] = geo_em_coord

    wrfinp_ds.close()
    geo_ds.close()

    # overwrite attributes
    os.system(cfg.ncks+' -A -x '+geo_data_file+' '+wrfout_file)
