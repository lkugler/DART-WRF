import os, sys, shutil
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy, sed_inplace, append_file

time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')

# ensure correct input.nml
copy(cluster.scriptsdir+'/../templates/input.nml',
     cluster.dartrundir+'/input.nml')
sed_inplace(cluster.dartrundir+'/input.nml', '<n_ens>', str(int(exp.n_ens)))
append_file(cluster.dartrundir+'/input.nml', cluster.scriptsdir+'/../templates/obs_def_rttov.VIS.nml')

# prepare observation file
import create_obs_sat
create_obs_sat.run(time, exp.n_obs, exp.error_variance, output_path=cluster.dartrundir)

if not os.path.exists(cluster.dartrundir+'/obs_seq.in'):
    raise RuntimeError('obs_seq.in does not exist in '+cluster.dartrundir)

# get wrfout_d01 from nature run
shutil.copy(time.strftime(cluster.nature_wrfout),
            cluster.dartrundir+'/wrfout_d01')

import wrfout_add_geo
wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', cluster.dartrundir+'/wrfout_d01')

# DART may need a wrfinput file as well, which serves as a template for dimension sizes
symlink(cluster.dartrundir+'/wrfout_d01', cluster.dartrundir+'/wrfinput_d01')
