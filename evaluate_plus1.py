#!/usr/bin/python3
"""
Evaluate the forecast in observation space one minute after the analysis time.
"""
import datetime as dt
from dartwrf.workflows import WorkFlows

w = WorkFlows(exp_config='exp_nonlin.py', server_config='jet.py')
id = None

assim_times = [dt.datetime(2008,7,30,12), ]
                # dt.datetime(2008,7,30,12,30),  
                # dt.datetime(2008,7,30,13),
                # dt.datetime(2008,7,30,13,30),  
                # dt.datetime(2008,7,30,14),]

# generate observations at +1 minute after the assimilation time

tuples = []
for init in assim_times:
    for s in range(30,3*60+1,30):
        tuples.append((init, init+dt.timedelta(seconds=s)))

w.evaluate_obs_posterior_after_analysis(tuples, depends_on=id)
