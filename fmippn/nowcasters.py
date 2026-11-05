"""Nowcast method setup for FMI-PPN.

Functions here take the configuration as an argument instead of reading the
global configuration in ppn.py.
"""

import copy

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
