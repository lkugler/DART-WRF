Developer guide
===============

Overview of functionality
-------------------------

Workflow methods are defined in ``DART-WRF/dartwrf/workflows.py``.
A workflow method is for example :meth:`dartwrf.workflows.WorkFlows.assimilate`.
Calling it triggers the execution of the script ``DART-WRF/dartwrf/assimilate.py``.


Recipe to add new functionality
-------------------------------

Modify a workflow method
^^^^^^^^^^^^^^^^^^^^^^^^

Change the respective script in ``DART-WRF/dartwrf/workflows.py``.

Add a new workflow method
^^^^^^^^^^^^^^^^^^^^^^^^^^

Define the workflow method in ``DART-WRF/dartwrf/workflows.py``.
Therein, call a separate script ``DART-WRF/dartwrf/my_new_method.py``.
Copy and customize existing workflow methods as a template.
Then you can use any parameters in the ``cfg`` object.

Add an observation type
^^^^^^^^^^^^^^^^^^^^^^^

Define the forward operator in DART. 
Then its descriptor string ('kind') can be used as in tutorial 1.
