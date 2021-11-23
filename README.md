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
