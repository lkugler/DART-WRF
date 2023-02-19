import os
from config.cfg import exp
from config.clusters import cluster
from utils import symlink, copy_scp_srvx8, copy, sed_inplace

joinp = os.path.join

if __name__ == "__main__":

        # DART executables
        bins = ['perfect_model_obs', 'filter', 'obs_diag', 'obs_seq_to_netcdf']
        for b in bins:
        symlink(joinp(cluster.dart_srcdir, b),
                joinp(cluster.dartrundir, b))
        print(joinp(cluster.dartrundir, b), 'created')

        rttov_files = ['rttov13pred54L/rtcoef_msg_4_seviri_o3.dat', 
                #'mfasis_lut/rttov_mfasis_cld_msg_4_seviri_deff.dat',
                'mfasis_lut/rttov_mfasis_cld_msg_4_seviri_deff.H5',
                'cldaer_visir/sccldcoef_msg_4_seviri.dat']

        for f_src in rttov_files:
        destname = os.path.basename(f_src)
        if 'rtcoef' in f_src:
                destname = 'rtcoef_msg_4_seviri.dat'

        symlink(cluster.rttov_srcdir + f_src, 
                cluster.dartrundir+'/'+destname)

        ##################
        symlink(cluster.dartrundir+'/rttov_mfasis_cld_msg_4_seviri_deff.H5', 
                cluster.dartrundir+'/rttov_mfasis_cld_msg_4_seviri.H5')

        symlink(cluster.dart_srcdir+'/../../../observations/forward_operators/rttov_sensor_db.csv',
                cluster.dartrundir+'/rttov_sensor_db.csv')

        symlink(cluster.dart_srcdir+'/../../../assimilation_code/programs/gen_sampling_err_table/work/sampling_error_correction_table.nc',
                cluster.dartrundir+'/sampling_error_correction_table.nc')

        print('prepared DART & RTTOV links in', cluster.dartrundir)
