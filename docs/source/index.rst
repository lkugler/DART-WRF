DART-WRF documentation
=======================

**DART-WRF** is a python package which allows you to
* run the `weather research and forecast model` (`WRF <https://www2.mmm.ucar.edu/wrf/users/docs/docs_and_pubs.html>`_),
* generate (satellite) observations from a nature run,
* and assimilate these observations in ensemble data assimilation using `DART <https://docs.dart.ucar.edu/en/latest/>`_,
* on a computing cluster or on your local machine.


Installation
*************

DART-WRF can be downloaded from `github.com/lkugler/DART-WRF <https://github.com/lkugler/DART-WRF>`_. To use it, you don't need to install it, but only its requirements:

.. code-block::
   
   git clone https://github.com/lkugler/DART-WRF.git
   pip install xarray netCDF4 docopt pysolar==0.10.0

Note that `pysolar` is necessary to generate synthetic satellite observations.


First steps
************

To get started, go through the tutorials in the :ref:`tutorials` section.
:ref:`tutorial1` shows you how to configure DART-WRF, generate observations and assimilate them.
:ref:`tutorial2` shows you how to run a WRF forecast with the output from data assimilation.
:ref:`tutorial3` shows you how assimilation and forecast can be run in a cycle.

.. toctree::
   :hidden:

   Home <self>

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   tutorial1
   notebooks/tutorial2
   notebooks/tutorial3
   custom_scripts


Other helpful resources
=======================

**DART documentation** `[here] <https://docs.dart.ucar.edu/en/latest/README.html>`_
**WRF user guide** `[here] <http://www2.mmm.ucar.edu/wrf/users/docs/user_guide_v4/v4.2/WRFUsersGuide_v42.pdf>`_



   
.. toctree::
   :hidden:
   :caption: Reference
   
   modules
   genindex 
   

API
===

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
