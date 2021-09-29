import os, sys, shutil
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy

time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')

# get wrfout_d01 from nature run
shutil.copy(time.strftime(exp.nature_wrfout),
            cluster.dartrundir+'/wrfout_d01')

import wrfout_add_geo
wrfout_add_geo.run(cluster.dartrundir+'/geo_em.d01.nc', cluster.dartrundir+'/wrfout_d01')

# DART may need a wrfinput file as well, which serves as a template for dimension sizes
symlink(cluster.dartrundir+'/wrfout_d01', cluster.dartrundir+'/wrfinput_d01')
