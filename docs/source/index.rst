DART-WRF documentation
=======================

**DART-WRF** is a python package which allows you to

* run the Weather Research and Forecast model (`WRF <https://www2.mmm.ucar.edu/wrf/users/docs/docs_and_pubs.html>`_),
* generate (satellite) observations from a nature run,
* and assimilate these observations in ensemble data assimilation using `DART <https://docs.dart.ucar.edu/en/latest/>`_,
* on a computing cluster or on your local machine.


Installation
------------

No install required, just download it from the University of Vienna (`gitlab.phaidra.org <PHAIDRA_URL>`_) or Github (`github.com/lkugler/DART-WRF <GITHUB_URL>`_).

Documentation and tutorials are available at `readthedocs.io <READTHEDOCS_URL>`_.


Program Structure
-----------------

DART-WRF is controlled by a **control script** which defines a high-level workflow. The control script specifies the workflow you want to run in an experiment by calling **workflow functions**.

For example, to assimilate observations, then initialize, and run a forecast, you call the respective workflow functions in this order:

.. code-block:: python

    w = WorkFlows(cfg)
    w.prepare_WRFrundir(cfg)
    id = w.assimilate(cfg)
    id = w.prepare_IC_from_prior(cfg)
    id = w.update_IC_from_DA(cfg)
    id = w.run_WRF(cfg)


Workflow Functions
^^^^^^^^^^^^^^^^^^

**Workflow functions** are python functions which define resource requirements and submit jobs to the queueing system. They look like this for example:

.. code-block:: python

    def assimilate(self, cfg, depends_on=None):
        """Calls assimilate.py
        
        :returns: job ID of the submitted job
        :rtype: str
        """
        path_to_script = self.dir_dartwrf_run + '/assimilate.py'
        cmd = ' '.join([self.python, path_to_script, cfg.f_cfg_current])
        id = self.run_job(cmd, cfg, depends_on=[depends_on], 
                          **{"ntasks": str(cfg.max_nproc), "time": "30", 
                             "mem": "110G", "ntasks-per-node": str(cfg.max_nproc), "ntasks-per-core": "1"}, 
                     )
        return id

In this example, ``assimilate.py`` is the task script.


Task Scripts
^^^^^^^^^^^^

A **task script** like ``assimilate.py`` does the actual work. It is not executed right away, but only after its dependencies are met, e.g. completion of WRF forecasts. Task scripts are called with a (auto-generated) configuration file path as argument. Any parameters in the config file can be easily accessed in a task script. For example, the task script ``update_IC.py`` looks like this:

.. code-block:: python

    import os, sys
    import netCDF4 as nc
    from dartwrf.utils import Config

    def update_initials_in_WRF_rundir(cfg: Config) -> None:
        """Updates wrfrst-files in `/run_WRF/` directory 
        with posterior state from ./filter output, e.g. filter_restart_d01.0001
        """
        time = cfg.time  # dt.datetime
        
        for iens in range(1, cfg.ensemble_size+1):
            ic_file = cfg.dir_wrf_run.replace('<exp>', cfg.name
                                              ).replace('<ens>', str(iens)
                                                        )+time.strftime(initials_fmt)
            #### code omitted ####

    if __name__ == '__main__':
        cfg = Config.from_file(sys.argv[1]) 
        update_initials_in_WRF_rundir(cfg)

That's it. For examples of actual applications, have a look at the tutorials.


Directory Structure
-------------------

The most important directories are:

* **DART-WRF home**: that is the place where you clone DART-WRF to, and where you develop it.
* **WRF run directory**: is the place where the temporary "run" directory of WRF is located.
* **DART run directory**: same as above for DART.
* **Sim-archive**: stores all data for an experiment that is not temporary, e.g. diagnostics, WRF output, DART output.

You only need to create DART-WRF home. The rest is automatically created.

Set these paths in your cluster's config file, e.g. ``DART-WRF/config/jet.py``.

What's Next?
------------

To get familiar with DART-WRF's capabilities, please have a look at the **tutorials**:

* **Tutorial 1** shows you how to create observations from a nature run simulation. 
* **Tutorial 2** shows you how to combine observations and prior forecasts into an analysis. 
* **Tutorial 3** shows you how to run a WRF forecast with an analysis. 
* **Tutorial 4** combines all steps into a single script.

..
   Explicit Target Definitions (for uniformity)
   This section is hidden from the main rendered text.
..

.. _WRF_URL: https://www2.mmm.ucar.edu/wrf/users/docs/docs_and_pubs.html
.. _DART_URL: https://docs.dart.ucar.edu/en/latest/
.. _PHAIDRA_URL: https://gitlab.phaidra.org/dataassimilation/DART-WRF/
.. _GITHUB_URL: https://github.com/lkugler/DART-WRF
.. _READTHEDOCS_URL: https://dart-wrf.readthedocs.io/en/latest/

.. toctree::
   :hidden:

   Home <self>
   setup

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   t1
   t2
   t3
   t4
   dev


Other helpful resources
-----------------------

* `DART documentation <https://docs.dart.ucar.edu/en/latest/README.html>`_
* `WRF user guide <http://www2.mmm.ucar.edu/wrf/users/docs/user_guide_v4/v4.2/WRFUsersGuide_v42.pdf>`_

   
.. toctree::
   :hidden:
   :caption: Reference
   
   modules
   genindex 
   

API
***
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
