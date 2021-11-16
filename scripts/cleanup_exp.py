import os
from config.cfg import exp, cluster
from utils import try_remove

"""Run this script after an experiment to reduce cluster disk usage.

1) remove wrfrst
2) remove run_DART folders from exp
3) remove run_WRF files from exp
"""
expname = sys.argv[1]
keep_last_init_wrfrst = True

print('removing files for exp', exp)

# 1) wrfrst
inits = reversed(sorted(glob.glob(cluster.archive_base+'/'+expname+'/20??-??-??_??:??')))
for k, init in enumerate(inits):
    rst_files = glob.glob(init+'/*/wrfrst_*')

    if k == 0:  # last init of exp
        
        if not keep_last_init_wrfrst:
            for f in rst_files:
                try_remove(f)
    else:
        for f in rst_files:
            try_remove(f)

# 2) run_DART/exp
os.removedirs(cluster.tmpfiledir+'/run_DART/'+expname)

# 3) run_WRF/exp
for iens in range(1, exp.n_ens+1):
    os.removedirs(cluster.wrf_rundir(iens))
    print(cluster.wrf_rundir(iens), 'removed.')