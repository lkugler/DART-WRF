import os, sys
import datetime as dt
from dartwrf import utils
from config.cfg import exp

"""Configuration name docs

When coding, use attributes of a dictionary like this: 
$ from cfg import exp, cluster
$ path = cluster.archivedir


attribute name    |     description
------------------------------------------------------
name                    any string (currently unused)

python                  path of python version to use
python_enstools         path of python version to use for verification script (not provided)
ncks                    path to 'ncks' program; type 'which ncks' to find the path,
                            if it doesn't exist, try to load the module first ('module load nco')
ideal                   path to WRF's ideal.exe
wrfexe                  path to WRF's wrf.exe

wrf_rundir_base         path for temporary files for WRF
dart_rundir_base        path for temporary files for DART
archive_base            path for long-time output storage

srcdir                  path to where WRF has been compiled, including the 'run' folder of WRF, e.g. /home/WRF-4.3/run
dart_srcdir             path to DART compile directory, e.g. /home/DART-9.11.9/models/wrf/work
rttov_srcdir            path to RTTOV compile directory, e.g. /home/RTTOV13/rtcoef_rttov13/
scriptsdir              path where DART-WRF scripts reside, e.g. /home/DART-WRF/scripts

namelist                path to a namelist template; strings like <hist_interval>, will be overwritten in scripts/prepare_namelist.py
run_WRF                 path to script which runs WRF on a node of the cluster
obs_impact_filename     path to obs_impact_filename (see DART guide; module assim_tools_mod and program obs_impact_tool)
geo_em                  path to NetCDF file of WRF domain (see WRF guide)

slurm_cfg               python dictionary, containing options of SLURM
                            defined in SLURM docs (https://slurm.schedmd.com/sbatch.html)
                            this configuration can be overwritten later on, for example:
                            'dict(cluster.slurm_cfg, **cfg_update)' where
                            'cfg_update = {"nodes": "2"}'
"""


cluster = utils.ClusterConfig(exp)
cluster.name = 'jet'
cluster.max_nproc = 12
cluster.use_slurm = True
cluster.size_jobarray = 40

# binaries
cluster.python = '/jetfs/home/lkugler/miniconda3/envs/DART/bin/python'
cluster.python_verif = '/jetfs/home/lkugler/miniconda3/envs/enstools/bin/python'
cluster.ncks = '/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-2021.7.1/nco-5.1.0-izrhxv24jqco5epjhf5ledsqwanojc5m/bin/ncks'
cluster.ideal = '/jetfs/home/lkugler/bin/ideal-v4.3_v1.22.exe'
cluster.wrfexe = '/jetfs/home/lkugler/bin/wrf-v4.3_v1.22_ifort_20230413.exe'
cluster.dart_modules = 'module purge; module load netcdf-fortran/4.5.3-gcc-8.5.0-qsqbozc;'
cluster.wrf_modules = """module purge; module load intel-oneapi-compilers/2022.2.1-zkofgc5 hdf5/1.12.2-intel-2021.7.1-w5sw2dq netcdf-fortran/4.5.3-intel-2021.7.1-27ldrnt netcdf-c/4.7.4-intel-2021.7.1-lnfs5zz intel-oneapi-mpi/2021.7.1-intel-2021.7.1-pt3unoz
export HDF5=/jetfs/spack/opt/spack/linux-rhel8-skylake_avx512/intel-2021.7.1/hdf5-1.12.2-w5sw2dqpcq2orlmeowleamoxr65dhhdc
"""

# paths for data output
cluster.wrf_rundir_base = '/jetfs/home/lkugler/data/run_WRF/'  # path for temporary files
cluster.dart_rundir_base = '/jetfs/home/lkugler/data/run_DART/'  # path for temporary files
cluster.archive_base = '/jetfs/home/lkugler/data/sim_archive/'

# paths used as input
cluster.srcdir = '/jetfs/home/lkugler/data/compile/WRF-4.3/run'
cluster.dart_srcdir = '/jetfs/home/lkugler/data/compile/DART/DART-10.5.3/models/wrf/work'
cluster.rttov_srcdir = '/jetfs/home/lkugler/data/compile/RTTOV13/rtcoef_rttov13/'
cluster.scriptsdir = '/jetfs/home/lkugler/DART-WRF/dartwrf/'

# other inputs
cluster.geo_em_for_WRF_ideal = '/jetfs/home/lkugler/data/geo_em.d01.nc'
cluster.obs_impact_filename = cluster.scriptsdir+'/../templates/impactfactor_T.txt'
cluster.namelist = cluster.scriptsdir+'/../templates/namelist.input'
cluster.run_WRF = '/jetfs/home/lkugler/DART-WRF/dartwrf/run_ens.jet.sh'

cluster.slurm_cfg = {"account": "lkugler", "partition": "compute", #"nodelist": "jet07",
                 "ntasks": "1", "ntasks-per-core": "1", "mem": "50G",
                 "mail-type": "FAIL", "mail-user": "lukas.kugler@univie.ac.at"}
