Developer guide
===============

Overview of functionality
-------------------------

Workflow methods are defined in ``DART-WRF/dartwrf/workflows.py``.
A workflow method is for example :meth:`dartwrf.workflows.WorkFlows.assimilate`, which can be run like this:

.. code-block:: python

    from dartwrf.workflows import WorkFlows

    prior_path_exp = '/users/students/lehre/advDA_s2023/data/sample_ensemble/'
    prior_init_time = dt.datetime(2008,7,30,12)
    prior_valid_time = dt.datetime(2008,7,30,13)
    assim_time = prior_valid_time

    w = WorkFlows(exp_config='exp_template.py', server_config='srvx1.py')

    id = w.assimilate(assim_time, prior_init_time, prior_valid_time, prior_path_exp)

Calling :meth:`dartwrf.workflows.WorkFlows.assimilate` triggers the execution of the script `dartwrf/assimilate.py`.


Recipe to add new functionality
-------------------------------

Modify a workflow method
^^^^^^^^^^^^^^^^^^^^^^^^

Change the respective script in ``dartwrf/``.

Add a new workflow method
^^^^^^^^^^^^^^^^^^^^^^^^^^

Define the workflow method in ``dartwrf/workflows.py``.
Therein, call a separate script ``dartwrf/my_new_method.py``.
Copy and customize existing workflow methods as a template.
Then you can use any parameters in the ``cfg`` object.

Add an observation type
^^^^^^^^^^^^^^^^^^^^^^^

Define the forward operator in DART. 
Then its descriptor string ('kind') can be used as in tutorial 1.
