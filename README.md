# Finnish Meteorological Institute Probabilistic Precipitation Nowcasting system (FMI-PPN)

FMI-PPN is a modular weather-radar-based nowcasting system built for research and operational usage.

## Subsystems

### Precipitation motion

Current implementation of FMI-PPN uses Lucas-Kanade optical flow method to estimate precipitation movement from radar measurements.

### Nowcasting

Currently FMI-PPN uses [pysteps](https://pysteps.github.io) to generate ensemble nowcasts.

## Known issues and limitations

- Parameter `SEED` must be `None` or an integer between `0` and `2**32 - 1`. This is a limitation in `numpy.random`.
- OpenMPI conflicts with dask when both are installed, leading to significant decrease FMI-PPN performance. Workaround is to set OpenMPI use only one thread. In Linux you can set environment variable `OMP_NUM_THREADS=1`.

## Usage

### Installation

1. Install [conda](https://conda.io/en/latest/) (Miniconda is recommended)
2. Clone this repository
3. Change directory to FMI-PPN folder
4. Setup conda environment: `$ conda env create -f environment.yml`
5. Modify pystepsrc file: Add your data source configuration under `data_sources` (see pysteps documentation for details)
6. Replace the value for `DOMAIN` parameter under `defaults` with your data source configuration's name
7. Activate conda environment: `$ conda activate fmippn`
8. Run FMI-PPN with default settings: `$ python run_ppn.py`

### Model selection

#### STEPS

To use the STEPS model, set at least the following parameters:

Parameter|Explanation|Value
----|----|----
`deterministic_method` | Nowcasting method for deterministic nowcast | `extrapolation`
`nowcast_method` | Nowcasting method for ensemble nowcast | `steps`
`transform_to_dBR` | Whether to transform rain rate to dBR. | `true`

Note also STEPS model parameters, listed below.

#### LINDA

To use the STEPS model, set at least the following parameters:

Parameter|Explanation|Value
----|----|----
`deterministic_method` | Nowcasting method for deterministic nowcast | `linda`
`nowcast_method` | Nowcasting method for ensemble nowcast | `linda`
`transform_to_dBR` | Whether to transform rain rate to dBR. | `false`
`forecast_as_quantity` | Quantity that data is transformed to before nowcasting. | `RATE`
`steps_set_no_rain_to_value` | No data value for nowcasting. | 0

Note also LINDA model parameters, listed below.

### Running FMI-PPN

Before running FMI-PPN, you should configure pysteps (via `pystepsrc` file) and PPN by adding your parametrisations to `ppn_config.py`.

How to run:

1. Activate your conda environment
2. Run FMI-PPN with your settings: `$ python run_ppn.py -c your_config_parametrisation`

## Configuration

### Adding new parametrisations

Create a `json` file with parameters you want to change from defaults and put it in `config` folder. The file's name (without file type extension) will be used to select the settings.

The `ppn_config.py` module has a utility function `dump_defaults()` for creating a configuration file based on default settings.

### Parametrisations

Parameter|Explanation|Default value
----|----|----
`DOMAIN`|Data source used from pystepsrc|`fmi`
`ENSEMBLE_SIZE`|Number of ensemble members|`24`
`FIELD_VALUES`|Select the units to store the nowcast (before scaling). Valid units are `dbz` for dBZ and `rrate` for mm/h.|`dbz`
`GENERATE_DETERMINISTIC`|Calculate extrapolation-only nowcast|`True`
`GENERATE_ENSEMBLE`|If `True`, then calculate ensemble members|`True`
`GENERATE_UNPERTURBED`|Calculate nowcast using pysteps, but without noise|`False`
`KMPERPIXEL`|Pixel size in kilometers|`1.0`
`LOG_FOLDER`|Path where log files should be stored|`../logs`
`LOG_LEVEL`|Logging level used by [Python Logging Module](https://docs.python.org/3/library/logging.html#levels)|`20`
`MAX_LEADTIME`|How long your nowcast will be (in minutes)|`120`
`NORAIN_VALUE`|Value assigned to dry pixels during thresholding. Units depend on `VALUE_DOMAIN` parameter (dBZ or mm/h). Must be less than `RAIN_THRESHOLD` value!|`1.5`
`NOWCAST_TIMESTEP`|Timestep between consecutive nowcast images|`5`
`NUM_PREV_OBSERVATIONS`|Number of previous observations used in optical flow calculation|`3`
`NUM_TIMESTEPS`|How many timesteps will be calculated in nowcasts (If this setting is `None`, this value is automatically calculated based on `MAX_LEADTIME` and `NOWCAST_TIMESTEP` parameters) |`None`
`NUM_WORKERS`|Number of worker threads used in parallel computing|`6`
`OPTFLOW_METHOD`|Optical flow method (see pysteps docs)|`lucaskanade`
`OUTPUT_PATH`|If not `None`, then use this path to store output instead of setting in pysteprc|`None`
`OUTPUT_TIME_FORMAT`|Python datetime format for showing timestamps|`%Y-%m-%d %H:%M:%S`
`RAIN_THRESHOLD`|Thresholding value for rain. Pixels with values under this parameter are regarded as dry pixels. Units depend on `VALUE_DOMAIN` parameter (dBZ or mm/h).|`6.5`
`REGENERATE_PERTURBED_MOTION`|Re-calculate motion for each ensemble member (requires `SEED != None`) |`False`
`SCALER`|Scaling coefficient for output|`100`
`SCALE_ZERO`|Value for "0" after scaling the output. Setting to `"auto"` or `None` uses the minimum value found in data before scaling.|`auto`
`SEED`|Seed parameter for random number generation. Use `None` for unseeded nowcasts.|`None`
`STORE_DETERMINISTIC`|Write "deterministic" nowcast in output file|`True`
`STORE_ENSEMBLE`|Write all ensemble members in output file|`True`
`STORE_MOTION`|Write optical flow motion field in output file|`True`
`STORE_PERTURBED_MOTION`|Write optical flow motion for each ensemble member in output file|`True`
`STORE_UNPERTURBED`|Write "unperturbed" nowcast in output file|`True`
`VALUE_DOMAIN`|Choose if nowcasting is performed for data in dBZ or mm/h units. Valid parameters are `dbz` for dBZ and `rrate` for mm/h.|`dbz`
`VEL_PERT_KWARGS`|Parameters for velocity perturbation (see pysteps docs). Set this parameter to `None` to use default pysteps values.|`{'p_par': [2.20837526, 0.33887032, -2.48995355], 'p_perp': [2.21722634, 0.32359621, -2.57402761]}`
`VEL_PERT_METHOD`|Velocity perturbation method used in pysteps|`bps`
`WRITE_LOG`|If `True`, then generate a log file|`False`
`ZR_A`|Value for coefficient _a_ in R(Z) relation|`223.0`
`ZR_B`|Value for coefficient _b_ in R(Z) relation|`1.53`

#### STEPS model specific parameters

For a more detailed description of the parameters, see the PySTEPS documentation.

Parameter|Explanation|Default value
----|----|----
`n_cascade_levels` | Number of cascade levels for scale decomposition. | 6
`fft_method` | FFT method used in pysteps calculations | `pyfftw`
`domain` | Computation domain, options `spectral` and `spatial` |  `spectral`
`noise_method` | Name of the noise generator to use for perturbing the precipitation field. |  `nonparametric`
`ar_order` | The order of the AR(p) model. | 2
`mask_method` | The method to use for masking no precipitation areas in the forecast field. |  `incremental`

#### LINDA model specific parameters

For a more detailed description of the parameters, see the PySTEPS documentation.

Parameter|Explanation|Default value
----|----|----
`max_num_features` | Maximum number of features detected. | 25
`feature_method` | Feature detection method. `domain` disables feature detection, other option `blob`. | `domain`
`feature_kwargs` | Keyword arguments for feature detection function. | {}
`ari_order` | Order of ARI(p, 1) model. | 1
`kernel_type` | Kernel type. | `anisotropic`
`localization_window_radius` | The standard deviation of the Gaussian localization window. | None
`errdist_window_radius` | The standard deviation of the Gaussian window for estimating the forecast error distribution. | None
`acf_window_radius` | The standard deviation of the Gaussian window for estimating the forecast error ACF. | None
`extrap_kwargs` | Extrapolation method keyword arguments. | `{}`
`pert_thrs` | Two-element tuple containing the threshold values for estimating the perturbation parameters (mm/h) | (0.5, 1.0)
