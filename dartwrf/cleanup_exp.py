import os, sys, glob, shutil
from utils import try_remove

"""Run this script to reduce wrfrst files

Example call:
    python ./cleanup_exp.py
"""
keep_last_init_wrfrst = True

datadir = '/gpfs/data/fs71386/lkugler/sim_archive/'
#exp = sys.argv[1]
for exp in os.listdir(datadir):
    
    print('removing files for exp', exp)
    
    inits = glob.glob(datadir+exp+'/20??-??-??_??:??')
    for init in inits:
        for iens in range(1, 41):
            rst_files = sorted(glob.glob(init+'/'+str(iens)+'/wrfrst_*'))
            #print(rst_files)
            if len(rst_files)>1:
                for f in sorted(rst_files)[:-1]:
                    try_remove(f)
                    print(f, 'removed')
    
