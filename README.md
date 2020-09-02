# DART-WRF

This code runs an OSSE with DART and WRF on a cluster with SLURM.

- readable: see what it does at first glance
- flexible: schedule jobs in python or any other language
- Slurm-aware: functions return a SLURM ID `id1 = function()`, to start another function as soon as the one before returned `function2(depends_on=id1)` thanks to ![brentp/slurmpy](https://github.com/brentp/slurmpy).


### A possible workflow:
`scheduler.py`
```python

# create initial conditions
id = prep_osse()  

# spin up the ensemble
background_init_time = dt.datetime(2008, 7, 30, 6, 0)
integration_end_time = dt.datetime(2008, 7, 30, 11, 0)
id = run_ENS(begin=background_init_time,
             end=integration_end_time,
             depends_on=id)
             
time = integration_end_time  # time now

# now, start the ensemble data assimilation cycles
timedelta_integrate = dt.timedelta(minutes=15)
timedelta_btw_assim = dt.timedelta(minutes=15)

while time < dt.datetime(2008, 7, 30, 16, 15):
     assim_time = time
     id = gen_synth_obs(assim_time, depends_on=id)
     id = assimilate(assim_time,
                     background_init_time,
                     depends_on=id)

     background_init_time = assim_time  # start integration now
     integration_end_time = assim_time + timedelta_integrate
     id = run_ENS(begin=background_init_time,
                  end=integration_end_time,
                  depends_on=id)

     time += timedelta_btw_assim
```

### SLURM submissions
`scheduler.py` submits jobs into the SLURM queue with dependencies, so that SLURM starts the jobs itself as soon as resources are available. Most jobs need only one node, but model integration is done in a SLURM job array across e.g. 5 nodes:
```
$ squeue -u `whoami` --sort=$E
            308377  mem_0384 ideal-01  lkugler PD       0:00      1 (Resources)
            308378  mem_0384 prerun-a  lkugler PD       0:00      1 (Priority)
      308379_[1-5]  mem_0384 EnsWRF-3  lkugler PD       0:00      1 (Dependency)
            308380  mem_0384 pregensy  lkugler PD       0:00      1 (Dependency)
            308381  mem_0384 gensynth  lkugler PD       0:00      1 (Dependency)
            308382  mem_0384 preassim  lkugler PD       0:00      1 (Dependency)
            308383  mem_0384 assim-37  lkugler PD       0:00      1 (Dependency)
            308384  mem_0384 postassi  lkugler PD       0:00      1 (Dependency)
            308385  mem_0384 prerun-e  lkugler PD       0:00      1 (Dependency)
      308386_[1-5]  mem_0384 EnsWRF-3  lkugler PD       0:00      1 (Dependency)
            308387  mem_0384 pregensy  lkugler PD       0:00      1 (Dependency)
            308388  mem_0384 gensynth  lkugler PD       0:00      1 (Dependency)
            308389  mem_0384 preassim  lkugler PD       0:00      1 (Dependency)
            308390  mem_0384 assim-37  lkugler PD       0:00      1 (Dependency)
            308391  mem_0384 postassi  lkugler PD       0:00      1 (Dependency)
            308392  mem_0384 prerun-6  lkugler PD       0:00      1 (Dependency)
      308393_[1-5]  mem_0384 EnsWRF-3  lkugler PD       0:00      1 (Dependency)
```

### Easily switch between clusters

`config/clusters.py `
```python

clusterA = ClusterConfig()
clusterA.name = 'vsc'
clusterA.userdir = '/home/pathA/myuser/'
...
clusterB = ClusterConfig()
clusterB.name = 'jet'
clusterB.userdir = '/home/pathB/myuser/'
```

`config/cfg.py`
```python

from . import clusters
cluster = clusters.clusterA  # change cluster configuration here
```


### References
This repo is a simplified python version of the code provided in the [DART-WRF Tutorial](http://www.image.ucar.edu/wrfdart/tutorial/).
DART itself is available at github: [@NCAR/DART](https://github.com/NCAR/DART)

### License
DART is licensed under the Apache License, Version 2.0
Copyright 2019 University Corporation for Atmospheric Research
