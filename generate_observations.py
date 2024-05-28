#!/usr/bin/python3
"""
Generate observation files from an experiment
"""
import datetime as dt
from dartwrf.workflows import WorkFlows

w = WorkFlows(exp_config='nature.py', server_config='jet.py')

obs_times = [dt.datetime(2008,7,30,12,15),]
#             dt.datetime(2008,7,30,12), dt.datetime(2008,7,30,12,1),
#             dt.datetime(2008,7,30,12,30),  dt.datetime(2008,7,30,12,31),
#             dt.datetime(2008,7,30,13), dt.datetime(2008,7,30,13,1),
#             dt.datetime(2008,7,30,13,30),  dt.datetime(2008,7,30,13,31),
#             dt.datetime(2008,7,30,14), dt.datetime(2008,7,30,14,1),]

w.generate_obsseq_out(obs_times)
