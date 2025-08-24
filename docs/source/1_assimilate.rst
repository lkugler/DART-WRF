Tutorial 1: Assimilate
#######################


Directory structure
*******************

There are five important directories.

1. A directory where you compile DART. E.g. ``/jetfs/scratch/username/DART``. Download and compile DART to this directory, see `docs.dart.ucar.edu <https://docs.dart.ucar.edu/en/latest>`_.
2. A directory where you develop DART-WRF and start experiments. E.g. ``/jetfs/scratch/username/DART-WRF``. Download DART-WRF to this directory, ``git clone https://gitlab.phaidra.org/dataassimilation/DART-WRF.git``.
3. A directory where you store your experiment data. To run this tutorial, download sample data (543 MB) using ``wget https://zenodo.org/records/12614519/files/raw_data.zip; unzip raw_data.zip``.
4. A directory to run DART in, containing temporary files. E.g. ``/jetfs/scratch/username/run_DART``.
5. A directory to run WRF in, containing temporary files. E.g. ``/jetfs/scratch/username/run_WRF``.


Basic configuration
*******************

Set these directories and other parameters in a configuration, 
you can take ``DART-WRF/config/jet_1node.py`` as an example.
The parameters are explained in the API reference :class:`dartwrf.utils.Config` 
(code in ``dartwrf/utils.py``).



Workflow
********

Now, we can set up a workflow in the script ``tutorial_1.py``. 

Customize the settings,

* ``expname`` should be a unique experiment name and will be used as folder name
* ``ensemble_size`` is the ensemble size
* ``update_vars`` are the WRF variables which shall be updated by the assimilation


.. code-block:: python

    import datetime as dt
    from dartwrf.workflows import WorkFlows
    from dartwrf.utils import Config

    from config.jet_1node import cluster_defaults
    from config.defaults import dart_nml, t2m

    cfg = Config(name='exp1',
        ensemble_size = 10,
        dart_nml = dart_nml,

        assimilate_these_observations = [t2m,],
        assimilate_existing_obsseq = False,
        nature_wrfout_pattern = '/jetfs/scratch/username/raw_data/nature/*/1/wrfout_d01_%Y-%m-%d_%H_%M_%S',
        
        geo_em_nature = '/jetfs/scratch/username/geo_em.d01.nc',
        geo_em_forecast = '/jetfs/scratch/username/geo_em.d01.nc',
        
        time = dt.datetime(2008, 7, 30, 11),
        update_vars = ['THM', 'PH', 'MU', 'QVAPOR',],
        **cluster_defaults)

    w = WorkFlows(cfg)
    w.prepare_WRFrundir(cfg)
    id = w.assimilate(cfg, depends_on=id)



Options
=======

* To create observations one by one, follow the instructions in the DART documentation for the ``perfect_model_obs`` program.
* To use existing obs_seq files, set ``assimilate_existing_obsseq = '/jetfs/scratch/username/obs/%Y-%m-%d_%H:%M_obs_seq.out'`` where time-placeholders (``%Y-%m-%d_%H:%M``) are filled in later, depending on the assimilation time.
* To create observations on the fly, set ``assimilate_existing_obsseq = False``.
    

By default, the DART namelist of the build directory will be used. 
If you want to set different parameters, specify your changes in ``/config/defaults.py`` or provide
them as arguments to the :class:`dartwrf.utils.Config` instance.
For a description of DART's parameters, see `the official DART documentation <https://docs.dart.ucar.edu/>`_.



Observations
************

If you want to assimilate one observation, use 

.. code-block:: python

    t = dict(plotname='Temperature', 
             kind='RADIOSONDE_TEMPERATURE', 
             obs_locations=[(45., 0.)],  # location of observations
             error_generate=0.2,    # observation error used to generate observations
             error_assimilate=0.2,  # observation error used for assimilation
             heights=[1000,],       # for radiosondes, use range(1000, 17001, 2000)
             loc_horiz_km=50,       # horizontal localization half-width
             loc_vert_km=2.5        # vertical localization half-width
            )  

    assimilate_these_observations = [t,]  # select observations for assimilation


Multiple observations
=====================

To generate a grid of observations with homogeneous observation density, 
set ``km_between_obs``and ``skip_border_km``.

.. code-block:: python

    t2m = dict(..., km_between_obs=12, skip_border_km=8.0,)
    assimilate_these_observations = [t2m,]


Alternatively, provide coordinates to the obs_locations argument of the obs-type:

.. code-block:: python

    t2m = dict(..., obs_locations=[(45., 0.), (45.1, 0.),],)
    assimilate_these_observations = [t2m,]


For vertical observations, set the ``heights`` parameter to specify the vertical levels at which to generate observations:

.. code-block:: python

    t = dict(..., heights=[1000, 2000, 3000])
    assimilate_these_observations = [t,]


Run the workflow
****************

Execute the programs by running ``python tutorial_1.py``.

