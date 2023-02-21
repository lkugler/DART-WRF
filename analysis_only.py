#!/usr/bin/python3
"""
running the forecast model without assimilation
"""
import os, sys, shutil
import datetime as dt

from dartwrf.workflows import WorkFlows


prior_path_exp = '/mnt/jetfs/scratch/lkugler/data/sim_archive/exp_v1.19_P3_wbub7_noDA'
prior_init_time = dt.datetime(2008,7,30,12)
prior_valid_time = dt.datetime(2008,7,30,12,30)
assim_time = prior_valid_time

w = WorkFlows(exp_config='cfg.py', server_config='srvx1.py')

id = w.assimilate(assim_time, prior_init_time, prior_valid_time, prior_path_exp)

# w.create_satimages(time, depends_on=id)
