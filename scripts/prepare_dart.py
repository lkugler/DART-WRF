
import os, sys
from config.cfg import exp, cluster
from utils import symlink
joinp = os.path.join

dart_bin_dir = '/home/fs71386/lkugler/DART/DART_WRF_RTTOV_early_access/models/wrf/work/'
rttov_dir = '/home/fs71386/lkugler/RTTOV/'

# DART executables
bins = ['perfect_model_obs', 'filter', 'obs_diag']
for b in bins:
    symlink(joinp(dart_bin_dir, b),
            joinp(cluster.dartrundir, b))

# DART RTTOV capability
symlink('/home/fs71386/lkugler/DART/DART_WRF_RTTOV_early_access/'
        +'observations/forward_operators/rttov_sensor_db.csv',
        joinp(cluster.dartrundir, 'rttov_sensor_db.csv'))

# Basic MSG4 Seviri
files = ['rtcoef_rttov12/rttov9pred54L/rtcoef_msg_4_seviri.dat',
         'rtcoef_rttov12/cldaer_visir/sccldcoef_msg_4_seviri.dat',]
for f in files:
    symlink(joinp(rttov_dir, f),
            joinp(cluster.dartrundir, os.path.basename(f)))

# MFASIS
deff = True
if deff:
    mfasis_tbl = 'rtcoef_rttov12/mfasis_lut/rttov_mfasis_cld_msg_4_seviri_deff.H5'
else:
    mfasis_tbl = 'rtcoef_rttov12/mfasis_lut/rttov_mfasis_cld_msg_4_seviri_opac.H5'

symlink(joinp(rttov_dir, mfasis_tbl),
        joinp(cluster.dartrundir, 'rttov_mfasis_cld_msg_4_seviri.dat'))
