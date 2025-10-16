# Tutorial 1: Assimilate

Now, we can set up a workflow in the script `tutorial_assim.py`.
In the following, its contents are explained step-by-step.

The first block of imports never changes.

```python
from dartwrf.workflows import WorkFlows
from dartwrf.utils import Config
```

### Default configuration

The second block of imports loads dictionaries that contain a default configuration.
You can customize those by modifying `config/jet.py` and `config/defaults.py`.

```python
from config.jet import cluster_defaults
from config.defaults import dart_nml
```

## Set ensemble size

The ensemble size needs to be set in the DART namelist and for DART-WRF.
To do that, we overwrite the default values in `dart_nml`:

```python
ensemble_size = 10
dart_nml['&filter_nml'].update(num_output_state_members=ensemble_size,
                               ens_size=ensemble_size)
cluster_defaults.update(ensemble_size=ensemble_size,)
```

## Select observations

- To create observations one by one, follow the instructions in the DART documentation for the `perfect_model_obs` program.
- To use existing obs_seq files, set `assimilate_existing_obsseq = '/jetfs/scratch/username/obs/%Y-%m-%d_%H:%M_obs_seq.out'` where time-placeholders (`%Y-%m-%d_%H:%M`) are filled in later, depending on the assimilation time.
- To create observations on the fly, set `assimilate_existing_obsseq = False`.

By default, the DART namelist of the build directory will be used.
If you want to set different parameters, specify your changes in `/config/defaults.py` or provide
them as arguments to the {class}`dartwrf.utils.Config` instance.
For a description of DART's parameters, see [the official DART documentation](https://docs.dart.ucar.edu/).

### Single observation

To define an observation type, we use a dictionary.
If you want to assimilate radiosonde temperature observations, use

```python
t = dict(
         kind='RADIOSONDE_TEMPERATURE',
         obs_locations=[(45., 0.)],  # location of observations
         error_generate=0.25,    # observation error used to generate observations
         error_assimilate=0.5,  # observation error used for assimilation
         heights=[1000,],       # for radiosondes, use range(1000, 17001, 2000)
         loc_horiz_km=50,       # horizontal localization half-width
         loc_vert_km=2.5        # vertical localization half-width
        )

assimilate_these_observations = [t,]  # select observations for assimilation
```

- `kind` is the observation type as defined by DART (`DART/observations/forward_operators/obs_def_mod.f90`)
- `obs_locations` takes a list of coordinates for each observation

### Multiple observations

To generate a grid of observations with homogeneous observation density,
set ``` km_between_obs``and ``skip_border_km ```.

```python
t2m = dict(..., km_between_obs=12, skip_border_km=8.0,)
assimilate_these_observations = [t2m,]
```

Alternatively, provide coordinates to the obs_locations argument of the obs-type:

```python
t2m = dict(..., obs_locations=[(45., 0.), (45.1, 0.),],)
assimilate_these_observations = [t2m,]
```

For vertical observations, set the `heights` parameter to specify the vertical levels at which to generate observations:

```python
t = dict(..., heights=[1000, 2000, 3000])
assimilate_these_observations = [t,]
```

## Modify localization radius

To modify the localization radius for an observation, set the `loc_horiz_km` and `loc_vert_km` parameters in the observation dictionary:

```python
t = dict(..., loc_horiz_km=100, loc_vert_km=5)
assimilate_these_observations = [t,]
```

## Modify observation error

To assimilate observations assuming a larger error, set the `error_assimilate` parameter in the observation dictionary, e.g.:

```python
t = dict(..., error_assimilate=1.2)
assimilate_these_observations = [t,]
```

## Passing config parameters

We create a {class}`dartwrf.utils.Config` object and fill it with all parameters we want.

- `name` should be a unique experiment name and will be used as folder name
- `update_vars` are the WRF variables which shall be updated by the assimilation
- `time` is the time of the assimilation
- `dart_nml` is a dictionary with DART namelist parameters

**Which parameters are required?** This depends on the code you're running.
The advantage of this behavior is that you can easily introduce new parameters.
You just need to pass them as argument into {class}`dartwrf.utils.Config`.
Existing configs can be updated by calling `cfg.update(new_parameter = 'abc')`.

## Assimilate

In this example, we set up the run_WRF directories with `w.prepare_WRFrundir(cfg)` and
then assimilate using `w.assimilate(cfg)`.
Workflow methods are defined in `DART-WRF/dartwrf/workflows.py`.

```python
cfg = Config(
    name='exp1',
    dart_nml = dart_nml,

    assimilate_these_observations = [t2m,],
    assimilate_existing_obsseq = False,
    nature_wrfout_pattern = '/jetfs/scratch/username/raw_data/nature/*/1/wrfout_d01_%Y-%m-%d_%H_%M_%S',

    geo_em_nature = '/jetfs/scratch/username/geo_em.d01.nc',
    geo_em_forecast = '/jetfs/scratch/username/geo_em.d01.nc',

    time = dt.datetime(2008, 7, 30, 13),
    update_vars = ['THM', 'PH', 'MU', 'QVAPOR',],
    **cluster_defaults)

w = WorkFlows(cfg)
w.prepare_WRFrundir(cfg)
w.assimilate(cfg)
```

Execute the script with `python tutorial_assim.py`.
