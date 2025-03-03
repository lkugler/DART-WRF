
import os, sys
import netCDF4 as nc
from dartwrf.utils import Config

def update_initials_in_WRF_rundir(cfg: Config) -> None:
    """Updates wrfrst-files in `/run_WRF/` directory 
    with posterior state from ./filter output, e.g. filter_restart_d01.0001
    """
    time = cfg.time  # dt.datetime
    
    use_wrfrst = True  # if wrfrst is used to restart (recommended)
    if use_wrfrst:
        initials_fmt = '/wrfrst_d01_%Y-%m-%d_%H:%M:%S'
    else:
        initials_fmt = '/wrfinput_d01' 

    # which WRF variables will be updated?
    update_vars = ['Times',]
    update_vars.extend(cfg.update_vars)

    for iens in range(1, cfg.ensemble_size+1):
        ic_file = cfg.dir_wrf_run.replace('<exp>', cfg.name
                                          ).replace('<ens>', str(iens)
                                                    )+time.strftime(initials_fmt)
        if not os.path.isfile(ic_file):
            raise IOError(ic_file+' does not exist, updating impossible!')
        else:
            # overwrite DA updated variables
            filter_out = cfg.dir_archive.replace('<exp>', cfg.name) \
                + time.strftime('/%Y-%m-%d_%H:%M/filter_restart_d01.'+str(iens).zfill(4))

            with nc.Dataset(filter_out, 'r') as ds_filter:
                with nc.Dataset(ic_file, 'r+') as ds_new:

                    # update all other variables
                    for var in update_vars:
                        if var in ds_new.variables:
                            # regular case
                            ds_new.variables[var][:] = ds_filter.variables[var][:]
                            print('updated', var)
                        else:
                            # special case, where a variable has 2 time levels, e.g. THM_1, THM_2
                            for var_suffix in ['_1', '_2']:
                                ds_new.variables[var+var_suffix][:] = ds_filter.variables[var][:]
                                print('updated', var+var_suffix)

                print(ic_file, 'created, updated from', filter_out)


if __name__ == '__main__':
    cfg = Config.from_file(sys.argv[1])
    
    update_initials_in_WRF_rundir(cfg)
