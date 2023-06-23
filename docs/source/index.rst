Welcome to the DART-WRF documentation!
======================================

**DART-WRF** is a python package to run an Ensemble Data Assimilation system using the data assimilation suite `DART <https://docs.dart.ucar.edu/en/latest/README.html>`_ and the weather research and forecast model `WRF <https://www2.mmm.ucar.edu/wrf/users/docs/docs_and_pubs.html>`_.

Installation
------------

DART-WRF is available at `github.com/lkugler/DART-WRF <https://github.com/lkugler/DART-WRF>`_ using the command line. To use it, you don't need to install it, but only its requirements:

.. code-block::
   
   git clone https://github.com/lkugler/DART-WRF.git
   pip install xarray netCDF4 docopt pysolar==0.10.0

Note that `pysolar` is only necessary if you will be using satellite observations.



Other helpful resources
-----------------------

**DART documentation** `[here] <https://docs.dart.ucar.edu/en/latest/README.html>`_
**WRF user guide** `[here] <http://www2.mmm.ucar.edu/wrf/users/docs/user_guide_v4/v4.2/WRFUsersGuide_v42.pdf>`_


.. toctree::
   :hidden:

   Home <self>

.. toctree::
   :maxdepth: 2
   :caption: Tutorials

   notebooks/tutorial1
   notebooks/tutorial2
   notebooks/tutorial3
   custom_scripts
   
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
