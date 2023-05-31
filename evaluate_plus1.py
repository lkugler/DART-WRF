#!/usr/bin/python3
"""
Evaluate the forecast in observation space one minute after the analysis time.
"""
import datetime as dt
from dartwrf.workflows import WorkFlows

w = WorkFlows(exp_config='exp_nonlin.py', server_config='jet.py')


assim_times = [dt.datetime(2008,7,30,12), 
                dt.datetime(2008,7,30,12,30),  
                dt.datetime(2008,7,30,13),
                dt.datetime(2008,7,30,13,30),  
                dt.datetime(2008,7,30,14),]

# generate observations at +1 minute after the assimilation time
obs_times = [each+dt.timedelta(minutes=1) for each in assim_times]
w.generate_obsseq_out(obs_times)


# evaluate the forecast at +1 minute after the assimilation time
w.evaluate_plus1(assim_times)