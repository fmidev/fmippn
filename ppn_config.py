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


def get_params(name):
    """Utility function for easier access to wanted parametrizations.

    Two parametrisations should be provided: `defaults` and `test`.
    `defaults` contains all possible parameters and default values for them.
    The default values are used unless explicitly overriden.

    `test` contains parametrisations for short nowcast that generates all
    different nowcasts. Suitable for quickly testing different parameters and
    for development purposes.

    Input:
        name -- name of the parametrization dictionary

    Return dictionary of parameters for overriding defaults. Non-existing
    names will return an empty dictionary.
    """
    # Lookup dictionary
    names = {
        'defaults': defaults,
        'test': test,
        'esteri': esteri,
        'esteri_archive': esteri_archive,
        'docker_ravake': docker_ravake,
    }

    return names.get(name, dict())

# Default parameters for PPN, other dictionaries should override these parameters
# using dict.update() method.
defaults = {
    # Method selections
    "DOMAIN": "fmi", # See pystepsrc for valid data sources
    "OPTFLOW_METHOD": "lucaskanade",
    "FFT_METHOD": "pyfftw",
    "GENERATE_DETERMINISTIC": True,
    "GENERATE_ENSEMBLE": True,
    "GENERATE_UNPERTURBED": False,
    "REGENERATE_PERTURBED_MOTION": False,  # Re-calculate the perturbed motion fields used for pysteps nowcasting
    "VALUE_DOMAIN": "dbz",  # dbz or rrate
    # Z-R conversion parameters
    "ZR_A": 223.,
    "ZR_B": 1.53,
    # Nowcasting parameters
    "NUM_PREV_OBSERVATIONS": 3,
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 120,
    "NUM_TIMESTEPS": None,
    "ENSEMBLE_SIZE": 25,
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
    "STORE_UNPERTURBED": True,
    "STORE_DETERMINISTIC": True,  # Write det_fct to output
    "STORE_MOTION": True, # Write deterministic motion to output
    "STORE_PERTURBED_MOTION": True,  # Write motion for each ensemble member to output
    "SCALER": 100,
    "SCALE_ZERO": "auto",  # Value for "0" in scaled units. Set to "auto" or None for minimum value found before scaling
    # Logging parameters
    "WRITE_LOG": False,
    "LOG_LEVEL": logging.INFO,  # see logging module documentation for valid levels
    "LOG_FOLDER": "../logs",
}

# Add new parametrizations here
test = {
    "DOMAIN": "fmi_archive",
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 30,
    "ENSEMBLE_SIZE": 5,
    "SEED": 0,

    "FIELD_VALUES": "rrate",
    "VALUE_DOMAIN": "rrate",

    "GENERATE_DETERMINISTIC": True,
    "GENERATE_ENSEMBLE": True,
    "GENERATE_UNPERTURBED": True,
    "REGENERATE_PERTURBED_MOTION": True,

    "STORE_DETERMINISTIC": True,
    "STORE_ENSEMBLE": True,
    "STORE_UNPERTURBED": True,
    "STORE_PERTURBED_MOTION": True,
    "STORE_MOTION": True,

    "LOG_LEVEL": logging.DEBUG,
    "WRITE_LOG": False,
}

esteri = {
    "DOMAIN": "fmi_realtime_ravake",
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 90,
    "ENSEMBLE_SIZE": 15,
    "NUM_WORKERS": 30,
    "GENERATE_UNPERTURBED": True,
    "REGENERATE_PERTURBED_MOTION": True,  # Re-calculate the perturbed motion fields used for pysteps nowcasting
    "GENERATE_DETERMINISTIC": True,
    "OUTPUT_PATH": "/dev/shm/ppn",
    "STORE_MOTION": True,
    "STORE_ENSEMBLE": True,
    "STORE_DETERMINISTIC": True,
    "SEED": 20190823,
    "FIELD_VALUES": "dbz",
    "VALUE_DOMAIN": "dbz",
    "SCALER": 10,
    "WRITE_LOG": True,
    "LOG_LEVEL": logging.DEBUG,
    "LOG_FOLDER": "/var/tmp/log",
    "DBZ_MIN": -10,
    "DBZ_THRESHOLD": -10,
    "VEL_PERT_KWARGS": {
        # lucaskanade/fmi values given in pysteps.nowcasts.steps.forecast() method documentation
        "p_par": [0, 0, 0],
        "p_perp": [0, 0, 0],
    },
}

esteri_archive = {
    "DOMAIN": "fmi_archived_ravake",
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 60,
    "ENSEMBLE_SIZE": 15,
    "NUM_WORKERS": 25,
    "GENERATE_DETERMINISTIC": True,
    "OUTPUT_PATH": "/dev/shm/ppn",
    "STORE_MOTION": True,
    "STORE_ENSEMBLE": True,
    "STORE_DETERMINISTIC": True,
    "SEED": 20190823,
    "FIELD_VALUES": "dbz",
    "VALUE_DOMAIN": "dbz",
    "SCALER": 10,
    "WRITE_LOG": True,
    "LOG_LEVEL": logging.DEBUG,
    "LOG_FOLDER": "/var/tmp/log",
    "DBZ_MIN": -6,
    "DBZ_THRESHOLD": -6,
}

docker_ravake = {
    "DOMAIN": "fmi_realtime_ravake_docker",
    "NOWCAST_TIMESTEP": 5,
    "MAX_LEADTIME": 90,
    "ENSEMBLE_SIZE": 15,
    "NUM_WORKERS": 30,
    "GENERATE_UNPERTURBED": True,
    "REGENERATE_PERTURBED_MOTION": True,  # Re-calculate the perturbed motion fields used for pysteps nowcasting
    "GENERATE_DETERMINISTIC": True,
    "OUTPUT_PATH": "~/fmippn-run/fmippn-run-and-distribution/output",
    "STORE_MOTION": True,
    "STORE_ENSEMBLE": True,
    "STORE_DETERMINISTIC": True,
    "SEED": 20190823,
    "FIELD_VALUES": "dbz",
    "VALUE_DOMAIN": "dbz",
    "SCALER": 10,
    "WRITE_LOG": True,
    "LOG_LEVEL": logging.DEBUG,
    "LOG_FOLDER": "~/fmippn-run/fmippn-run-and-distribution/logs",
    "DBZ_MIN": -10,
    "DBZ_THRESHOLD": -10,
    "VEL_PERT_KWARGS": {
        # lucaskanade/fmi values given in pysteps.nowcasts.steps.forecast() method documentation
        "p_par": [0, 0, 0],
        "p_perp": [0, 0, 0],
    },
}
