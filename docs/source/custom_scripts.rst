Adding and modifying scripts
============================

Workflow methods are defined in the :class:`dartwrf.workflows.WorkFlows` class (`dartwrf/workflows.py`).
A workflow method is for example :meth:`dartwrf.workflows.WorkFlows.assimilate`, which can be run like this

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
*******************************

Option 1: Add a function in an existing script
----------------------------------------------

Easy. Only change the respective script in ``dartwrf/``.


Option 2: Add a new script
--------------------------

Let's say you need a new script ``verification.py``. Then you need to do the following:

#. Write a workflow method ``WorkFlow.call_verif()`` in ``dartwrf/workflows.py``, e.g. copy and modify an existing one, 
#. Inside, you call ``verification.py`` with :meth:`dartwrf.utils.ClusterConfig.run_job` (this will submit a SLURM job). Be careful which command-line arguments you need.
#. Write the script ``verification.py`` and parse the command-line arguments.
#. Lastly, call the workflow method ``WorkFlow.call_verif()`` from your control-script, e.g. ``cycled_exp.py``.

