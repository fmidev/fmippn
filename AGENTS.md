# FMI-PPN

Radar-based precipitation nowcasting system of the Finnish Meteorological Institute. Read [GLOSSARY.md](GLOSSARY.md) before naming things: "domain", "deterministic" and "unperturbed" each have a precise meaning here.

## Layout

- `fmippn/`: the Python nowcaster, where nearly all work happens. Entry point `run_ppn.py` → `ppn.run()`.
  - `ppn.py`: pipeline (read observations → motion → nowcast → write output).
  - `nowcasters.py`: nowcast method setup, one `Nowcaster` per deterministic/ensemble nowcast.
  - `ppn_config.py`: `defaults` dict and config loading/checks.
  - `odim_io.py`, `utils.py`: ODIM HDF5 output.
  - `config/*.json`: per-run configurations.
- `preprocess/`, `postprocess/`, `run-and-distribution/`, root `config/`: legacy operational shell/C chain. Treat as read-only unless the task names them; the same goes for `*.old`, `*.new`, `*.working` and `#…#` files anywhere.
- `run_mlcast_inference_example.py`: standalone experiment showing one ConvGRU checkpoint's handling. Background reading only; its constants belong to that checkpoint.

## Configuration

The source of truth is `ppn_config.defaults` deep-merged with `fmippn/config/<name>.json` (groups: `data_source`, `data_options`, `run_options`, `nowcast_options`, `output_options`, `logging`, `callback_options`). The parameter table in `README.md` describes an old flat format and is stale.

Deterministic and ensemble nowcasts normally run as separate runs with separate config files (e.g. `ravake-det.json`, `ravake-ens.json`), toggled by `run_options.run_deterministic` / `run_ensemble`.

## Adding a nowcast method

`nowcasters.get_nowcaster(method, kind, ...)` builds a `Nowcaster` for `run_options.deterministic_method` (kind `"deterministic"`) and `run_options.nowcast_method` (kind `"ensemble"`); `ppn.run()` builds only the ones the run generates. A `Nowcaster` bundles:

- `forecast`, called as `forecast(observations, motion_field, leadtimes, **kwargs)`; new backends get an adapter to that signature.
- `kwargs`, from `nowcasters.method_options()`: `nowcast_options` merged with `nowcast_options.method_specific_options.<method>`, as a new dict.
- `prepare_observations`, applied to observations read in the forecast quantity with NaN kept (default: pysteps thresholding/dBR). The motion field always uses the pysteps-prepared observations.
- `select_observations`, picking the input window from the prepared observations.

Ensemble output written leadtime by leadtime goes through `ppn.write_ensemble_leadtime()`; `ppn.postprocess_forecast()` converts any forecast to the output quantity. Motion and importer methods are still chosen by `optflow_method()` / `importer_method()` in `ppn.py`.

## mlcast integration (in progress)

Branch `mlcast-forecasting` adds mlcast machine-learning models as a nowcast backend for both the deterministic and ensemble runs. Read [docs/adr/0001-mlcast-nowcast-backend.md](docs/adr/0001-mlcast-nowcast-backend.md) before touching method dispatch, input reading or config for this work.

## Running and verifying

Run the tests from `fmippn/` in a test environment: `environment.yml` plus the test-only `environment-test.yml`.

```sh
mamba env create -f environment.yml -n ppn-test
mamba env update -f environment-test.yml -n ppn-test
cd fmippn && mamba run -n ppn-test python -m pytest tests
```

- Unit tests cover the extracted pipeline functions and need no data.
- Golden-master tests (`tests/golden.py`, `tests/test_golden.py`) run short, seeded copies of `finradfast-det` / `finradfast-ens` and compare every output HDF5 dataset and attribute against a recorded baseline. They need ODIM composites in `fmippn/tests/testdata/odim/` and the baseline in `fmippn/tests/testdata/golden/` (both untracked; the tests skip without them, so report a skip as unverified). Record a baseline with `python tests/golden.py record` only on code whose output is known to be right, and when a change is meant to alter output, show the `python tests/golden.py compare` differences before re-recording.

A full run is `python run_ppn.py -c <config-name> -t YYYYMMDDHHMM` inside the Docker image. Note that `docker-compose.yml` mounts hard-coded host paths that may point at a different checkout than this one.

Runtime gotchas: keep `OMP_NUM_THREADS=1` (OpenMP and dask conflict) and `HDF5_USE_FILE_LOCKING=FALSE`. `nowcast_options.seed` must be `None` or an int in `[0, 2**32-1]`.

## Conventions

- Format Python with `black` (default settings).
- Record user-visible changes (new options, changed output, dependency bumps) as a dated entry in `fmippn/CHANGELOG.md`.
- Runtime dependencies live in `environment.yml` (pinned `pysteps`), which the production image is built from; keep it minimal. Test-only tools go in `environment-test.yml`. The `environment_*.yml` and `Dockerfile_*` files are historical variants.
- Write ODIM output attributes that may hold strings with `utils.set_attr()`: it stores strings as fixed-length null-terminated strings like the ODIM input. Plain `attrs[key] = "..."` gives variable-length strings and `np.bytes_` null-padded ones.
