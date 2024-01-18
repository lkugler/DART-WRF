Tutorial 1: The assimilation step
##################################

DART-WRF is a python package which automates many things like configuration, program dependencies, archiving code, configuration and output, handling computing resources, etc.

This tutorial can be executed with pre-existing input data accessible for students of the "University of Vienna - Department of Meteorology and Geophysics" on the server `srvx1`/Teachinghub.

The main control scripts are in the main folder of DART-WRF, e.g. ``analysis_only.py``.
A control script defines the jobs (work packages, programs) which need to be completed and in which order they need to be done.
Every control script starts with setting up the experiment.

.. code-block:: python

    from dartwrf.workflows import WorkFlows
    w = WorkFlows(exp_config='exp_template.py', server_config='srvx1.py')


The imported class :class:`dartwrf.workflows.WorkFlows` (code in ``dartwrf/workflows.py``) defines these jobs.
The keywords ``exp_config`` and ``server_config`` point to the configuration files of the experiment and the hardware, located in the directory ``config/``.
A configuration file can be copied and customized. Note that ``git pull`` (updating DART-WRF) can overwrite default files like ``exp_template.py``.


Configuring the hardware
*************************

In case you are a student of our courses, you can use the prebuilt configuration ``config/srvx1.py`` or ``config/jet.py``.
In other cases, copy and modify an existing configuration.
The parameters of the server configuration are explained in the API reference :class:`dartwrf.utils.ClusterConfig` (code in ``dartwrf/utils.py``).


Configuring the experiment
***************************

Now, we need to configure our experiment. 
Copy the existing template and modify it ``cp config/exp_template.py config/exp1.py``.
Then set ``exp_config='exp1.py`` in the call to :class:`dartwrf.workflows.WorkFlows`.

**Customize your settings:**

Customize the settings in ``config/exp1.py``:
* `expname` should be a unique experiment name and will be used as folder name
* `n_ens` is the ensemble size
* `update_vars` are the WRF variables which shall be updated by the assimilation

.. code-block:: python

    exp = Experiment()
    exp.expname = "exp1"
    exp.n_ens = 40
    exp.update_vars = ['THM', 'PH', 'MU', 'QVAPOR',]


More parameters are described in the API reference :class:`dartwrf.utils.Experiment` (code in ``dartwrf/utils.py``).



Generating observations
=========================

In case you want to generate new observations, like for an observing system simulations experiment (OSSE), set :class:`dartwrf.workflows.WorkFlows`

.. code-block:: python

    exp.use_existing_obsseq = False
    
in this case, you need to set the path to WRF nature run files from where DART can generate observations:

.. code-block:: python

    exp.nature_wrfout_pattern = '/usr/data/sim_archive/exp_v1_nature/*/1/wrfout_d01_%Y-%m-%d_%H:%M:%S'


Using pre-existing observation files
=====================================

You can use pre-existing observation files with

.. code-block:: python

    exp.use_existing_obsseq = '/usr/data/sim_archive/exp_ABC/obs_seq_out/%Y-%m-%d_%H:%M_obs_seq.out'
    
where time-placeholders (``%Y-%m-%d_%H:%M``) are filled in later, depending on the assimilation time.


Customizing the DART namelist
================================

By default, the DART namelist of the build directory will be used (copied). 
If you want to modify any parameters, specify your changes in a python dictionary like below. For a description of the parameters, see `the official DART documentation <https://docs.dart.ucar.edu/>`_.

.. code-block:: python

    exp.dart_nml = {'&assim_tools_nml':
                        dict(filter_kind='1',
                             sampling_error_correction='.true.',
                            ),
                    '&filter_nml':
                        dict(ens_size=exp.n_ens,
                             num_output_state_members=exp.n_ens,
                             num_output_obs_members=exp.n_ens,
                             inf_flavor=['0', '4'],
                             output_members='.true.',
                             output_mean='.true.',
                             output_sd='.true.',
                             stages_to_write='output',
                            ),
                    '&quality_control_nml':
                        dict(outlier_threshold='-1',
                            ),
                    '&location_nml':
                        dict(horiz_dist_only='.false.',
                    '&model_nml':
                        dict(wrf_state_variables =
                            [['U',     'QTY_U_WIND_COMPONENT',     'TYPE_U',    'UPDATE','999',],
                             ['V',     'QTY_V_WIND_COMPONENT',     'TYPE_V',    'UPDATE','999',],
                             ['W',     'QTY_VERTICAL_VELOCITY',    'TYPE_W',    'UPDATE','999',],
                             ['PH',    'QTY_GEOPOTENTIAL_HEIGHT',  'TYPE_GZ',   'UPDATE','999',],
                             ['THM',   'QTY_POTENTIAL_TEMPERATURE','TYPE_T',    'UPDATE','999',],
                             ['MU',    'QTY_PRESSURE',             'TYPE_MU',   'UPDATE','999',],
                             ['QVAPOR','QTY_VAPOR_MIXING_RATIO',   'TYPE_QV',   'UPDATE','999',],
                             ['QICE',  'QTY_ICE_MIXING_RATIO',     'TYPE_QI',   'UPDATE','999',],
                             ['QCLOUD','QTY_CLOUDWATER_MIXING_RATIO','TYPE_QC', 'UPDATE','999',],
                             ['CLDFRA','QTY_CLOUD_FRACTION',       'TYPE_CFRAC','UPDATE','999',],
                             ['PSFC',  'QTY_SURFACE_PRESSURE',     'TYPE_PSFC', 'UPDATE','999',],
                             ['T2',    'QTY_2M_TEMPERATURE',       'TYPE_T',    'UPDATE','999',],
                             ['TSK',   'QTY_SKIN_TEMPERATURE',     'TYPE_T',    'UPDATE','999',],
                             ['REFL_10CM','QTY_RADAR_REFLECTIVITY','TYPE_REFL', 'UPDATE','999',]]),
                    }

Any parameters in this dictionary will be overwritten compared to the default namelist.



Single observation experiment
===============================

If you want to assimilate one observation, use 

.. code-block:: python

    t = dict(plotname='Temperature', plotunits='[K]',
             kind='RADIOSONDE_TEMPERATURE', 
             n_obs=1,                    # number of observations
             obs_locations=[(45., 0.)],  # location of observations
             error_generate=0.2,    # observation error used to generate observations
             error_assimilate=0.2,  # observation error used for assimilation
             heights=[1000,],       # for radiosondes, use range(1000, 17001, 2000)
             loc_horiz_km=50,       # horizontal localization half-width
             loc_vert_km=2.5        # vertical localization half-width
            )  

    exp.observations = [t,]  # select observations for assimilation


Assimilating multiple observations
===================================

To generate a grid of observations, use

.. code-block:: python

    vis = dict(plotname='VIS 0.6µm', plotunits='[1]',
               kind='MSG_4_SEVIRI_BDRF', sat_channel=1, 
               n_obs=961, obs_locations='square_array_evenly_on_grid',
               error_generate=0.03, error_assimilate=0.03,
               loc_horiz_km=50)
    exp.observations = [t, vis,]


Caution, n_obs should only be one of the following:

* 22500 for 2km observation density/resolution 
* 5776 for 4km; 
* 961 for 10km; 
* 256 for 20km; 
* 121 for 30km

For vertically resolved data, like radar, ``n_obs`` is the number of observations at each observation height level.



Set up the workflow 
********************

We start by importing some modules. 
To assimilate observations at dt.datetime `time` we set the directory paths and times of the prior ensemble forecasts.
Then we set up the experiment with the ``WorkFlow()`` call. It will also create the output folders and backup the configuration files and scripts. Finally, we run the data assimilation by calling :func:`dartwrf.workflows.WorkFlows.assimilate`.


.. code-block:: python

    from dartwrf.workflows import WorkFlows

    prior_path_exp = '/users/students/lehre/advDA_s2023/data/sample_ensemble/'
    prior_init_time = dt.datetime(2008,7,30,12)
    prior_valid_time = dt.datetime(2008,7,30,13)
    assim_time = prior_valid_time

    w = WorkFlows(exp_config='exp_template.py', server_config='srvx1.py')

    id = w.assimilate(assim_time, prior_init_time, prior_valid_time, prior_path_exp)
    

Congratulations! You're done!
