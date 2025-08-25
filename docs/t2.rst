Tutorial 2: Forecast after DA
##############################

**Goal**: To run an ensemble of forecasts. 
`[free_forecast.py] <https://github.com/lkugler/DART-WRF/blob/master/free_forecast.py>`_ contains examples.

Initialize the forecast with either (1) or (2). Run the forecast with (3)

#. Initialize a forecast from defined profiles of temperature, humidity and wind, i.e. from a `wrf_profile` (see WRF guide)
#. Initialize a forecast from an existing forecast, i.e. from WRF restart files - optionally with updates from data assimilation.
#. Run the forecast


1) Initialize from sounding profiles
************************************

It is necessary to set the path to the prepared WRF input soundings in `config/cfg.py` like this

.. code-block:: python

    exp.input_profile = '/users/students/lehre/advDA_s2023/data/initial_profiles/raso.fc.<iens>.wrfprof'

where `<iens>` is a placeholder, since there is one file for each member, from `raso.fc.001.wrfprof` to `raso.fc.040.wrfprof`.

Then, we set up the workflows as usual and prepare the input profiles.

.. code-block:: python

    import datetime as dt
    from dartwrf.workflows import WorkFlows

    w = WorkFlows(exp_config='cfg.py', server_config='srvx1.py')

    begin = dt.datetime(2008, 7, 30, 7)
    w.prepare_WRFrundir(begin)


Finally, the WRF's ideal.exe program is called for all ensemble members to create initial condition files, called `wrfinput_d01`, for each member.

.. code-block:: python

    w.run_ideal()


Now we can go to step 3 to run the forecast.


2) Initialize a forecast from a previous forecast
*************************************************

Let's say you want to run a forecast starting at 9 UTC until 12 UTC.
We use initial conditions of a previous experiment ``/user/test/data/sim_archive/exp_abc`` which was initialized at 6 UTC and there are WRF restart files for 9 UTC.
Documentation can be found at :func:`dartwrf.workflows.WorkFlows.prepare_IC_from_prior`.

.. code-block:: python

    import datetime as dt
    from dartwrf.workflows import WorkFlows
    w = WorkFlows(exp_config='cfg.py', server_config='srvx1.py')

    prior_path_exp = '/user/test/data/sim_archive/exp_abc'
    prior_init_time = dt.datetime(2008,7,30,6)
    prior_valid_time = dt.datetime(2008,7,30,9)

    begin = dt.datetime(2008, 7, 30, 9)
    end = dt.datetime(2008, 7, 30, 12)

    w.prepare_WRFrundir(begin)
    w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time)

Now, we are ready :ref:`to start a forecast <3) Run the Forecast>`.


2b) Optional: Update posterior with increments from assimilation
-------------------------------------------------------------------

In order to continue a forecast after assimilation you need the posterior = prior (1) + increments (2)

1. Prepare initial conditions from a prior forecast (see above)

.. code-block:: python

    w.prepare_IC_from_prior(prior_path_exp, prior_init_time, prior_valid_time)



2. Update the initial conditions from data assimilation.
:func:`dartwrf.workflows.WorkFlows.update_IC_from_DA` updates the initial conditions (WRFrst files) with assimilation increments from DART output and copies them to the WRF run directories.

.. code-block:: python

    w.update_IC_from_DA(time)


Now you can run the forecast ensemble.


3) Run the Forecast
*******************

Define how long you want to run the forecast (keywords `begin` and `end`) and how often you want WRF-restart files (`output_restart_interval` in minutes, only integers allowed, default is 12 hours).

.. code-block:: python

    timedelta_integrate = dt.timedelta(hours=5)

    w.run_ENS(begin=begin,  # start integration from here
            end=time + timedelta_integrate,  # integrate until here
            )

If you want to assimilate in 15 minutes again, you can use

.. code-block:: python

    w.run_ENS(begin=time,  # start integration from here
                end=time + dt.timedelta(hours=5),  # integrate until here
                output_restart_interval=15  # in minutes, only integers allowed
                )

By default, it assumes that the input data is a WRF restart file. To use a WRF input file for initial conditions, set the keyword ``input_is_restart=False``.
More documentation is in the docstring of :func:`dartwrf.workflows.WorkFlows.run_ENS`.
