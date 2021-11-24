# DART-WRF

This code runs an Ensemble Data Assimilation system with the software packages DART and WRF. All workflow steps are submitted to the cluster manager SLURM, which takes care of the dependencies (the order in which tasks are done).

- Why should I use it?
  - It's pythonic: see what it does at first glance, modular, flexible
  - It handles dependencies using SLURM without '`sleep` loops in the bash script'. 
Functions return a SLURM ID which can be used to trigger the start of another function (interface by [brentp/slurmpy](https://github.com/brentp/slurmpy)).

- How does it work?
  - There are two kinds of code/scripts: One that is run immediately and one that is run later on.
  - The first one instructs the cluster (SLURM) to do the things you tell it - in the right order - using the right input. 
  - The latter kind of code actually does the things. Its code is not executed right away, but when there are resources assigned to you by SLURM. 

- Can I use it for real weather?
  -  Yes, but you need to [convert your observations into DART format.](https://docs.dart.ucar.edu)


## Workflow
### Configure your experiment
Define simulation specific variables in [`config/cfg.py`](https://github.com/lkugler/DART-WRF/blob/master/config/cfg.py).
Define paths for python, ncks, etc. in [`config/clusters.py`](https://github.com/lkugler/DART-WRF/blob/master/config/clusters.py).
Dependencies are `numpy, pandas, scipy, xarray, netCDF4`. Install non-standard packages with `pip install docopt slurmpy --user`.

### Prepare initial conditions (from input_sounding)
1) Define starting time: 
`begin = dt.datetime(2008, 7, 30, 7)`
2) WRF needs directories with certain files:
`id = prepare_WRFrundir(begin)` 
3) Create 3D initial conditions from input_sounding etc.:
`id = run_ideal(depends_on=id)` 

### Run free forecast
...

### Prepare initial conditions from a previous run (wrfrst/wrfout)
`prepare_IC_from_prior` (set initial state to prior wrfrst/out)

### Update initial conditions from Data Assimilation
`update_IC_from_DA` (overwrite assimilated variables in initial state)

### Examples
[`scheduler.py`](https://github.com/lkugler/DART-WRF/blob/master/scheduler.py) 
[`generate_free.py`](https://github.com/lkugler/DART-WRF/blob/master/generate_free.py) 

## Finally

### SLURM submissions
`scheduler.py` submits jobs into the SLURM queue with dependencies, so that SLURM starts the jobs itself as soon as resources are available. Most jobs need only one node, but model integration is done in a SLURM job array across e.g. 10 nodes:
```
$ squeue -u `whoami` --sort=i
             JOBID PARTITION     NAME     USER ST       TIME  NODES NODELIST(REASON)
           1710274  mem_0384 prepwrfr  lkugler PD       0:00      1 (Priority)
           1710275  mem_0384 IC-prior  lkugler PD       0:00      1 (Dependency)
           1710276  mem_0384 Assim-42  lkugler PD       0:00      1 (Dependency)
           1710277  mem_0384 IC-prior  lkugler PD       0:00      1 (Dependency)
           1710278  mem_0384 IC-updat  lkugler PD       0:00      1 (Dependency)
           1710279  mem_0384 preWRF2-  lkugler PD       0:00      1 (Dependency)
    1710280_[1-10]  mem_0384 runWRF2-  lkugler PD       0:00      1 (Dependency)
           1710281  mem_0384 pRTTOV-6  lkugler PD       0:00      1 (Dependency)
           1710282  mem_0384 Assim-3a  lkugler PD       0:00      1 (Dependency)
           1710283  mem_0384 IC-prior  lkugler PD       0:00      1 (Dependency)
           1710284  mem_0384 IC-updat  lkugler PD       0:00      1 (Dependency)
           1710285  mem_0384 preWRF2-  lkugler PD       0:00      1 (Dependency)
    1710286_[1-10]  mem_0384 runWRF2-  lkugler PD       0:00      1 (Dependency)
           1710287  mem_0384 pRTTOV-7  lkugler PD       0:00      1 (Dependency)
```

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
