Adding and modifying scripts
============================

Workflow methods are defined in `dartwrf/workflows.py`.
A workflow method is for example :meth:`dartwrf.workflows.assimilate`, which can be run like this

.. code-block:: python
    from dartwrf.workflows import WorkFlows

    prior_path_exp = '/users/students/lehre/advDA_s2023/data/sample_ensemble/'
    prior_init_time = dt.datetime(2008,7,30,12)
    prior_valid_time = dt.datetime(2008,7,30,13)
    assim_time = prior_valid_time

    w = WorkFlows(exp_config='exp_template.py', server_config='srvx1.py')

    id = w.assimilate(assim_time, prior_init_time, prior_valid_time, prior_path_exp)

Calling :meth:`dartwrf.workflows.assimilate` triggers the execution of the script `dartwrf/assim_synth_obs.py`.

- Why do I need a separate script (in this case `assim_synth_obs.py`) to execute a script?
Because some users need to use SLURM, which can only call scripts, not run python code directly.

Recipe to add new functionality
*******************************

Do you need a new script? If not, use an existing one.
If you need write a new script, you need to 
1. write a workflow method (`dartwrf/workflows.py`), e.g. copy and modify an existing one, 
2. therein you call the script with :meth:`dartwrf.utils.ClusterConfig.run_job` available via `self.cluster.run_job`, be careful which command-line arguments you need
3. write the script and parse the command-line arguments
4. call whatever python functions you may need