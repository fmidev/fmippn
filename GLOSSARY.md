# FMI-PPN

FMI-PPN produces short-range precipitation forecasts (nowcasts) by extrapolating recent weather radar observations, using statistical (pysteps) or machine-learning (mlcast) models.

## Runs and configuration

**Config**:
A named set of parameter overrides selecting the input data, methods and output for one kind of run (e.g. `ravake-ens`).
_Avoid_: domain (for this meaning), profile

**Radar area**:
The geographic coverage of an input composite, such as the Finnish RAVAKE area or the European OPERA area.
_Avoid_: domain

**Computation domain**:
Whether pysteps STEPS works in the `spectral` or `spatial` space.
_Avoid_: domain (unqualified)

**Data source**:
A description of where input composites live and how they are read: path, filename pattern, importer, timestep.
_Avoid_: domain

**Initialisation time**:
The timestamp of the latest observation a nowcast starts from; the time given with `--timestamp`.
_Avoid_: analysis time, start time, init time

## Observations

**Observation**:
One radar composite field at one time, used as nowcast input.
_Avoid_: frame, input image

**Filled observation**:
An observation missing from the archive that was replaced by extrapolating an adjacent real observation.
_Avoid_: interpolated observation, synthetic frame

**Quantity**:
The physical variable a field holds, named with ODIM codes: `DBZH` (reflectivity, dBZ) or `RATE` (rain rate, mm/h).
_Avoid_: units, variable

**Undetect**:
The value marking pixels that were observed but had no precipitation echo.
_Avoid_: no-rain, zero

**Nodata**:
The value marking pixels without a valid observation, such as outside radar coverage.
_Avoid_: missing, NaN

## Nowcasts

**Motion field**:
The precipitation velocity field estimated from successive observations with optical flow.
_Avoid_: advection field, optical flow (for the result)

**Deterministic nowcast**:
A single-valued nowcast produced by a deterministic run, e.g. pure extrapolation of the latest observation or a single-member ML model.
_Avoid_: control run

**Unperturbed nowcast**:
A STEPS nowcast computed without stochastic noise; distinct from the deterministic nowcast.
_Avoid_: control member

**Ensemble nowcast**:
A set of equally likely nowcast members expressing forecast uncertainty.
_Avoid_: probabilistic output (for the members themselves)

**Member**:
One realisation within an ensemble nowcast.
_Avoid_: realisation, sample

**Leadtime**:
The time between the initialisation time and a forecast field.
_Avoid_: forecast step, horizon (for a single field)

**Timestep**:
The interval between consecutive observations or consecutive forecast fields.
_Avoid_: time resolution

## Models

**mlcast**:
The machine-learning nowcasting library that provides trained models to FMI-PPN.
_Avoid_: ML backend (as a name)

**ConvGRU**:
A recurrent convolutional neural network nowcasting model provided by mlcast.
_Avoid_: mlcast model (when this specific model is meant)

**Checkpoint**:
A saved set of trained weights and hyperparameters for one mlcast model.
_Avoid_: model file, weights

**STEPS**:
The pysteps stochastic ensemble nowcasting method based on cascade decomposition.

**LINDA**:
The pysteps nowcasting method based on localised feature-based extrapolation.
