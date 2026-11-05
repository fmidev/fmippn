# FMI-PPN

Radar-based precipitation nowcasting system of the Finnish Meteorological Institute. Read [GLOSSARY.md](GLOSSARY.md) before naming things: "domain", "deterministic" and "unperturbed" each have a precise meaning here.

## Layout

- `fmippn/`: the Python nowcaster, where nearly all work happens. Entry point `run_ppn.py` → `ppn.run()`.
  - `ppn.py`: pipeline (read observations → motion → nowcast → write output).
  - `ppn_config.py`: `defaults` dict and config loading/checks.
  - `odim_io.py`, `utils.py`: ODIM HDF5 output.
  - `config/*.json`: per-run configurations.
- `preprocess/`, `postprocess/`, `run-and-distribution/`, root `config/`: legacy operational shell/C chain. Treat as read-only unless the task names them; the same goes for `*.old`, `*.new`, `*.working` and `#…#` files anywhere.
- `run_mlcast_inference_example.py`: standalone experiment showing one ConvGRU checkpoint's handling. Background reading only; its constants belong to that checkpoint.

## Configuration

The source of truth is `ppn_config.defaults` deep-merged with `fmippn/config/<name>.json` (groups: `data_source`, `data_options`, `run_options`, `nowcast_options`, `output_options`, `logging`, `callback_options`). The parameter table in `README.md` describes an old flat format and is stale.

Deterministic and ensemble nowcasts normally run as separate runs with separate config files (e.g. `ravake-det.json`, `ravake-ens.json`), toggled by `run_options.run_deterministic` / `run_ensemble`.

## Adding a nowcast or motion method

Methods are dispatched by the `*_method(module=...)` getters in `ppn.py` (`importer_method`, `optflow_method`, `nowcast_method`, `deterministic_method`); each has a `pysteps` branch and room for more. Method kwargs are assembled in `generate_pysteps_setup()` from `nowcast_options`, with per-method options under `nowcast_options.method_specific_options.<method>`. `generate()` calls every nowcaster as `nowcaster(observations, motion_field, leadtimes, **kwargs)`; new backends get an adapter to that signature.

## mlcast integration (in progress)

Branch `mlcast-forecasting` adds mlcast machine-learning models as a nowcast backend for both the deterministic and ensemble runs. Read [docs/adr/0001-mlcast-nowcast-backend.md](docs/adr/0001-mlcast-nowcast-backend.md) before touching method dispatch, input reading or config for this work.

## Running and verifying

There is no test suite. A change is verified by a real run inside the Docker image:

```sh
docker-compose run --rm fmippn          # interactive shell in the container
cd /fmippn && python run_ppn.py -c <config-name> -t YYYYMMDDHHMM
```

then inspecting the ODIM HDF5 files in the output folder. Runs need radar input mounted at `/input`, which is usually not available to you: propose the exact command and what to check in the output, and report the change as unverified. Note that `docker-compose.yml` mounts hard-coded host paths that may point at a different checkout than this one.

Runtime gotchas: keep `OMP_NUM_THREADS=1` (OpenMP and dask conflict) and `HDF5_USE_FILE_LOCKING=FALSE`. `nowcast_options.seed` must be `None` or an int in `[0, 2**32-1]`.

## Conventions

- Format Python with `black` (default settings).
- Record user-visible changes (new options, changed output, dependency bumps) as a dated entry in `fmippn/CHANGELOG.md`.
- Dependencies live in `environment.yml` (pinned `pysteps`); the other `environment_*.yml` and `Dockerfile_*` files are historical variants.
- Output HDF5 string attributes use `np.bytes_` (numpy ≥ 2).
