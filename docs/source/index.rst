Welcome to the DART-WRF documentation!
===================================

DART-WRF is a Python package to run an Ensemble Data Assimilation system with the software packages DART and WRF.

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



Contents
--------

.. toctree::

   usage
   api
   example

