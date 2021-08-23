# DART-WRF

This code runs an Ensemble Data Assimilation system with the software packages DART and WRF. All workflow steps are submitted to the cluster manager SLURM, which takes care of the dependencies (the order in which tasks are done).

- Why should I use it?
  - It's pythonic: see what it does at first glance, modular, flexible
  - It handles dependencies using SLURM without '`sleep` loops in the bash script'. 
Functions return a SLURM ID which can be used to trigger the start of another function (interface by [brentp/slurmpy](https://github.com/brentp/slurmpy)).

- How does it work?
  - There are two kinds of code/scripts: One that is run immediately and one that is run later on.
  - The first one instructs the cluster (SLURM) to do the things you tell it - in the right order - using the right input. Example: [`scheduler.py`](https://github.com/lkugler/DART-WRF/blob/master/scheduler.py)
  - The latter kind of code actually does the things. Its code is not executed right away, but when there are resources assigned to you by SLURM. Example: [`prepare_nature.py`](https://github.com/lkugler/DART-WRF/blob/master/scripts/prepare_nature.py) and other files in the `/scripts` folder.

- Can I use it for real weather?
  -  Yes, but you need to [convert your observations into DART format.](https://docs.dart.ucar.edu)

### A possible workflow:
[`scheduler.py`](https://github.com/lkugler/DART-WRF/blob/master/scheduler.py) 
```python
### define your functions gen_synth_obs, assimilate, run_ENS, ...

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
$ squeue -u `whoami` --sort=i
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

### Configure your experiment
Define simulation specific variables in [`config/cfg.py`](https://github.com/lkugler/DART-WRF/blob/master/config/cfg.py).

### Easily switch between clusters
Define cluster specific variables in `config/clusters.py `:
```python

clusterA = ClusterConfig()
clusterA.name = 'vsc'
clusterA.userdir = '/home/pathA/myuser/'
...
clusterB = ClusterConfig()
clusterB.name = 'jet'
clusterB.userdir = '/home/pathB/myuser/'
```


### References
This workflow was created following the [DART-WRF Tutorial](http://www.image.ucar.edu/wrfdart/tutorial/).
Read the DART documentation: [docs.dart.ucar.edu](https://docs.dart.ucar.edu).
DART is available at github: [@NCAR/DART](https://github.com/NCAR/DART).

### License
This repo is licensed under Apache License 2.0

[@NCAR/DART](https://github.com/NCAR/DART) is licensed under the Apache License, Version 2.0
Copyright 2019 University Corporation for Atmospheric Research
