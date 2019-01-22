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
    "GENERATE_DETERMINISTIC": False,
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
    "KMPERPIXEL": 1.0,
    "VEL_PERT_METHOD": "bps",
    # Storing parameters
    "OUTPUT_PATH": None,  # None uses pystepsrc output path
    "OUTPUT_TIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "STORE_ENSEMBLE": True, # Write each ensemble member to output
    "STORE_DETERMINISTIC": False,  # Write det_fct to output
    "STORE_MOTION": False, # Write motion to output
    # Logging parameters
    "WRITE_LOG": False,
    "LOG_LEVEL": logging.INFO  # see logging module documentation for valid levels
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

}

verification = {
    "DOMAIN": "fmi_archive",
    "MAX_LEADTIME": 360,
    "ENSEMBLE_SIZE": 50,
    "WRITE_LOG": True,
    "LOG_LEVEL": logging.INFO,
    "STORE_ENSEMBLE": True,
    "STORE_MOTION": True,
    "OUTPUT_PATH": "~/devel/fmippn/out/cases",
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
}
