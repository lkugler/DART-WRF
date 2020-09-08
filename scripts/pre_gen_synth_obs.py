import os, sys, shutil
import datetime as dt
from config.cfg import exp, cluster
from utils import symlink, copy, sed_inplace, append_file
import create_obs_sat

time = dt.datetime.strptime(sys.argv[1], '%Y-%m-%d_%H:%M')
channel_id = int(sys.argv[2])

# ensure correct input.nml
copy(cluster.scriptsdir+'/../templates/input.nml',
     cluster.dartrundir+'/input.nml')
sed_inplace(cluster.dartrundir+'/input.nml', '<n_ens>', str(int(exp.n_ens)))

if channel_id in [1, 2, 3, 12]:
    rttov_nml = cluster.scriptsdir+'/../templates/obs_def_rttov.VIS.nml'
else:
    rttov_nml = cluster.scriptsdir+'/../templates/obs_def_rttov.IR.nml'
append_file(cluster.dartrundir+'/input.nml', rttov_nml)

# prepare observation file
create_obs_sat.run(time, channel_id, exp.n_obs, exp.error_variance,
                output_path=cluster.dartrundir,
                fpath_obs_locations=cluster.archivedir()+time.strftime('/%Y-%m-%d_%H:%M')
                +'/obs_coords_id'+str(channel_id)+'.pkl')

if not os.path.exists(cluster.dartrundir+'/obs_seq.in'):
    raise RuntimeError('obs_seq.in does not exist in '+cluster.dartrundir)
