Setup DART-WRF
==============

1) Install DART
^^^^^^^^^^^^^^^^^^^

Download and compile DART to this directory, see `docs.dart.ucar.edu <https://docs.dart.ucar.edu/en/latest>`_.


2) Install DART-WRF
^^^^^^^^^^^^^^^^^^^^^^^^

DART-WRF can be downloaded from `GitHub <https://github.com/lkugler/DART-WRF>`_ or `GitLab <https://gitlab.phaidra.org/dataassimilation/DART-WRF/>`_.
To use it, install its requirements:

.. code-block::
   
   git clone https://github.com/lkugler/DART-WRF.git
   pip install xarray netCDF4 docopt pysolar==0.10.0

Note that `pysolar` is necessary to generate synthetic satellite observations.


3) Data directory
^^^^^^^^^^^^^^^^^^^

Create a directory where you store your experiment data.
E.g. ``/jetfs/scratch/username/data``.
To run this tutorial, download sample data (543 MB) using ``wget https://zenodo.org/records/12614519/files/raw_data.zip; unzip raw_data.zip``.



Directory structure
-------------------

There are five important directories.

1. A directory where you compile DART. E.g. ``/jetfs/scratch/username/DART``. 
2. A directory where you develop DART-WRF and start experiments. E.g. ``/jetfs/scratch/username/DART-WRF``. 
3. A directory where you store your experiment data. E.g. ``/jetfs/scratch/username/data``.

Additional directories are created at runtime:

4. A directory to run DART in, containing temporary files. E.g. ``/jetfs/scratch/username/run_DART``.
5. A directory to run WRF in, containing temporary files. E.g. ``/jetfs/scratch/username/run_WRF``.


Before running DART-WRF, you need to set paths, specifically the parameters to :class:`dartwrf.utils.Config`.
See the file ``DART-WRF/config/jet_1node.py`` as an example.
The settings will be imported later.
