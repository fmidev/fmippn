"""Parameter configuration for FMI-PPN

Dictionary `defaults` contains default parameter settings for FMI-PPN.

Other dictionaries should contain non-default parameters. Program should
update defaults with non-default dictionary.

Utility method `get_params(name)` returns a dictionary.

Adding new parametrizations:
  1. Create a new dictionary object
  2. Add new parameter values in the new dictionary
  3. Update the lookup dictionary inside get_params() method
"""
import logging

# TODO: Each parametrization in its own file?

# TODO: Explain these constants/settings in readme.md

def get_params(name):
    """Utility function for easier access to wanted parametrizations.

    Input:
        name -- name of the parametrization dictionary

    Return dictionary of parameters for overriding defaults. Non-existing
    names will return an empty dictionary.
    """
    # Lookup dictionary
    names = {
        'defaults': defaults,
        'dev': dev,
        'verification': verification,
        'road_weather': road_weather,
        '2019-08-23-event': demo_heavy_rainfall_pks,
    }

    return names.get(name, dict())

# Default parameters for PPN, other dictionaries should override these parameters
# using dict.update() method.
defaults = {
    # Method selections
    "DOMAIN": "fmi", # See pystepsrc for valid data sources
    "OPTFLOW_METHOD": "lucaskanade",
    "FFT_METHOD": "pyfftw",
    "GENERATE_ENSEMBLE": True,
    "GENERATE_UNPERTURBED": False,
    "GENERATE_DETERMINISTIC": False,
    "REGENERATE_PERTURBED_MOTION": False,  # Re-calculate the perturbed motion fields used for pysteps nowcasting
    "VALUE_DOMAIN": "dbz",  # dbz or rrate
    # Z-R conversion parameters
    "ZR_A": 223.,
    "ZR_B": 1.53,
    # Nowcasting parameters
    "NUM_PREV_OBSERVATIONS": 3,
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 30,
    "NUM_TIMESTEPS": None,
    "ENSEMBLE_SIZE": 5,
    "NUM_CASCADES": 6,
    "NUM_WORKERS": 6,
    "R_MIN": 0.1,
    "R_THRESHOLD": 0.1,
    "DBZ_MIN": -10,
    "DBZ_THRESHOLD": -10,
    "KMPERPIXEL": 1.0,
    "SEED": None,  # Default value in pysteps is None
    # Motion perturbation parameters
    # Set to VEL_PERT_KWARGS to `None` to use pysteps's default values
    "VEL_PERT_METHOD": "bps",
    "VEL_PERT_KWARGS": {
        # lucaskanade/fmi values given in pysteps.nowcasts.steps.forecast() method documentation
        "p_par": [2.20837526, 0.33887032, -2.48995355],
        "p_perp": [2.21722634, 0.32359621, -2.57402761],
    },
    # Storing parameters
    "FIELD_VALUES": "dbz",  # Store values as rrate or dbz
    "OUTPUT_PATH": None,  # None uses pystepsrc output path
    "OUTPUT_TIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "STORE_ENSEMBLE": True, # Write each ensemble member to output
    "STORE_UNPERTURBED": False,
    "STORE_DETERMINISTIC": False,  # Write det_fct to output
    "STORE_MOTION": False, # Write deterministic motion to output
    "STORE_PERTURBED_MOTION": False,  # Write motion for each ensemble member to output
    "SCALER": 100,
    "SCALE_ZERO": "auto",  # Value for "0" in scaled units. Set to "auto" or None for minimum value found before scaling
    # Logging parameters
    "WRITE_LOG": False,
    "LOG_LEVEL": logging.INFO,  # see logging module documentation for valid levels
    "LOG_FOLDER": "../logs",
}

# Add new parametrizations here
dev = {
    "DOMAIN": "fmi_archive",
    "LOG_LEVEL": logging.DEBUG,
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 30,
    "ENSEMBLE_SIZE": 5,
    "WRITE_LOG": False,
    "STORE_ENSEMBLE": True,
    "GENERATE_DETERMINISTIC": True,
    "STORE_DETERMINISTIC": True,
    "STORE_MOTION": True,
    "SEED": 0,
    "FIELD_VALUES": "rrate",
    "SCALER": 10,
    "VALUE_DOMAIN": "rrate",
    "REGENERATE_PERTURBED_MOTION": True,
    "STORE_PERTURBED_MOTION": True,
    "GENERATE_UNPERTURBED": True,
    "STORE_UNPERTURBED": True,
}

verification = {
    "DOMAIN": "verification",
    "MAX_LEADTIME": 180,
    "ENSEMBLE_SIZE": 50,
    "NUM_WORKERS": 30,
    "WRITE_LOG": True,
    "LOG_LEVEL": logging.INFO,
    "STORE_ENSEMBLE": True,
    "STORE_MOTION": True,
    "GENERATE_DETERMINISTIC": True,
    "STORE_DETERMINISTIC": True,
    "OUTPUT_PATH": "~/tmp-data",
    "SEED": 2019050104,
    "REGENERATE_PERTURBED_MOTION": True,
    "STORE_PERTURBED_MOTION": True,
    "VALUE_DOMAIN": "rrate",
    "FIELD_VALUES": "rrate",
}

road_weather = {
    "DOMAIN": "fmi_archive",
    "WRITE_LOG": False,
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 180,
    "ENSEMBLE_SIZE": 1,
    "STORE_ENSEMBLE": False,
    "STORE_MOTION": False,
    "STORE_DETERMINISTIC": True,
    "GENERATE_DETERMINISTIC": True,
    "GENERATE_ENSEMBLE": False,
    "OUTPUT_PATH": "~/devel/fmippn/out/road",
    "SEED": 1234567890,
    "FIELD_VALUES": "DBZ",
    "SCALER": 10,
}

demo_heavy_rainfall_pks = { # 2019-08-23 was heavy rainfall event in Helsinki region
    "DOMAIN": "fmi",
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 120,
    "ENSEMBLE_SIZE": 51,
    "NUM_WORKERS": 25,
    "STORE_ENSEMBLE": True,
    "STORE_DETERMINISTIC": True,
    "GENERATE_DETERMINISTIC": True,
    "STORE_MOTION": True,
    "SEED": 20190823,
    "FIELD_VALUES": "dbz",
    "VALUE_DOMAIN": "dbz",
    "SCALER": 10,
    "OUTPUT_PATH": "~/tmp-data/2019-08-23-event",
    "WRITE_LOG": True,
    "LOG_LEVEL": logging.DEBUG,
    "LOG_FOLDER": "~/tmp-data/2019-08-23-event",
    "DBZ_MIN": 8,
    "DBZ_THRESHOLD": 8,
}
