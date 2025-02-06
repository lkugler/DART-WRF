#!/usr/bin/python3
"""
Generate observation files from an experiment
"""
import datetime as dt
import pandas as pd
from dartwrf.workflows import WorkFlows

w = WorkFlows(exp_config='exp_hires.py', server_config='jet.py')

#obs_times = [dt.datetime(2008,7,30,14,),]
obs_times = pd.date_range(start='2008-07-30 13:00:00', end='2008-07-30 14:00:00', freq='15min')

w.generate_obsseq_out(obs_times)
