"""Nowcast method setup for FMI-PPN.

Functions here take the configuration as an argument instead of reading the
global configuration in ppn.py.
"""

import copy

import utils
from ppn_config import defaults

DEFAULT_N_CASCADE_LEVELS = defaults["nowcast_options"]["method_specific_options"][
    "steps"
]["n_cascade_levels"]


def method_options(nowcast_options, method):
    """Return the nowcast options for `method` as a new dictionary.

    Common options in `nowcast_options` are updated with the options under
    `method_specific_options.<method>`. `nowcast_options` is not modified.
    """
    options = copy.deepcopy(nowcast_options)
    method_specific = options.pop("method_specific_options", None) or {}
    options.update(method_specific.get(method) or {})
    return options


def method_how_attrs(configuration):
    """Return the nowcast method attributes stored in the /how group of output files.

    The attributes describe `run_options.nowcast_method`, also in deterministic
    output files.
    """
    method = configuration["run_options"]["nowcast_method"]
    options = method_options(configuration["nowcast_options"], method)
    if method == "steps":
        return {
            "ensemble_nowcast_method": "steps",
            "domain": options["domain"],
            "n_cascade_levels": options.get(
                "n_cascade_levels", DEFAULT_N_CASCADE_LEVELS
            ),
        }
    if method == "linda":
        return {
            "ensemble_nowcast_method": "linda",
            "feature_method": options["feature_method"],
            "ari_order": str(options["ari_order"]),
            "max_num_features": str(options["max_num_features"]),
        }
    return {}


def prepare_pysteps_observations(observations, metadata, configuration):
    """Prepare observations for pysteps motion and nowcast methods.

    Values under the rain threshold (`converted_rain_thr`) and, optionally,
    missing values are set to `run_options.steps_set_no_rain_to_value`. Rain
    rates are transformed to dBR if `run_options.transform_to_dBR` is set.
    The inputs are not modified.

    Return a tuple (observations, metadata).
    """
    run_options = configuration["run_options"]
    obs, meta = utils.thresholding(
        observations.copy(),
        dict(metadata),
        threshold=configuration["converted_rain_thr"],
        norain_value=run_options["steps_set_no_rain_to_value"],
        fill_nan=run_options.get("steps_fill_nan", True),
    )

    fct_qty = run_options.get("forecast_as_quantity", configuration["input_quantity"])
    if utils.quantity_is_rate(fct_qty) and run_options["transform_to_dBR"]:
        obs, meta = utils.transform_to_decibels(obs, meta)

    return obs, meta
