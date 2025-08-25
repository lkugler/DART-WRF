DART-WRF documentation
=======================

**DART-WRF** is a python package which allows you to

* run the `weather research and forecast model` (`WRF <https://www2.mmm.ucar.edu/wrf/users/docs/docs_and_pubs.html>`_),
* generate (satellite) observations from a nature run,
* and assimilate these observations in ensemble data assimilation using `DART <https://docs.dart.ucar.edu/en/latest/>`_,
* on a computing cluster or on your local machine.


Installation
*************

DART-WRF can be downloaded from `GitHub <https://github.com/lkugler/DART-WRF>`_ or `GitLab <https://gitlab.phaidra.org/dataassimilation/DART-WRF/>`_.
To use it, install its requirements:

.. code-block::
   
   git clone https://github.com/lkugler/DART-WRF.git
   pip install xarray netCDF4 docopt pysolar==0.10.0

Note that `pysolar` is necessary to generate synthetic satellite observations.


First steps
************

It is recommended to go through tutorials, to get familiar with DART-WRF's capabilities.
:ref:`Tutorial 1<Tutorial 1: Observations>` shows you how to create observations from a nature run simulation.
:ref:`Tutorial 2<Tutorial 2: The assimilation>` shows you how to combine observations and prior forecasts into an analysis.
:ref:`Tutorial 3<Tutorial 3: Forecast after DA>` shows you how to run a WRF forecast with an analysis.
:ref:`Tutorial 4<Tutorial 4: Cycle forecast and assimilation>` combines all steps into a single script.
See also `a graphical overview over DART-WRF's directory structure. <https://github.com/lkugler/DART-WRF/blob/17428cb29a9526c17d4878125a046777f0892996/docs/source/DART_WRF_visual.pdf>`_

.. toctree::
   :hidden:

   Home <self>

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   1_assimilate
   2_wrf
   notebooks/3_cycling
   4_customization


Other helpful resources
***********************

**DART documentation** `[here] <https://docs.dart.ucar.edu/en/latest/README.html>`_
**WRF user guide** `[here] <http://www2.mmm.ucar.edu/wrf/users/docs/user_guide_v4/v4.2/WRFUsersGuide_v42.pdf>`_

   
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
