"""Nowcast method setup for FMI-PPN.

Functions here take the configuration as an argument instead of reading the
global configuration in ppn.py.
"""

import copy
from dataclasses import dataclass
from typing import Callable

import pysteps

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


def _all_observations(observations):
    return observations


@dataclass
class Nowcaster:
    """A configured nowcast method.

    forecast -- called as forecast(observations, motion_field, leadtimes, **kwargs)
    kwargs -- keyword arguments for `forecast`
    prepare_observations -- called as prepare_observations(observations,
        metadata, configuration) on the observations read from input, returns
        (observations, metadata)
    select_observations -- picks the input for `forecast` from the prepared
        observations
    """

    method: str
    forecast: Callable
    kwargs: dict
    prepare_observations: Callable = prepare_pysteps_observations
    select_observations: Callable = _all_observations


ENSEMBLE_METHODS = ("steps", "linda")


def pysteps_kwargs(method, configuration, rain_thresholds, callback=None):
    """Return keyword arguments for a pysteps ensemble nowcast method.

    `rain_thresholds` is the tuple (r_thr, dbr_thr) from
    ppn.compute_rain_threshold(). If output leadtimes are written separately,
    `callback` is called by pysteps with the forecast of each leadtime.
    """
    r_thr, dbr_thr = rain_thresholds
    nowcast_kwargs = method_options(configuration["nowcast_options"], method)

    if method == "steps":
        # STEPS-specific options derived from other configurations
        # Threshold for masking
        nowcast_kwargs["precip_thr"] = dbr_thr if dbr_thr is not None else r_thr

    if configuration["output_options"].get("write_leadtimes_separately", False):
        nowcast_kwargs["callback"] = callback
        # Do not store whole forecast array but write out step by step
        nowcast_kwargs["return_output"] = False

    return nowcast_kwargs


def get_nowcaster(method, kind, configuration, rain_thresholds, callback=None):
    """Return the Nowcaster for nowcast method `method`.

    Input:
        method -- run_options.nowcast_method or run_options.deterministic_method
        kind -- "deterministic" or "ensemble"
        configuration -- FMI-PPN configuration
        rain_thresholds -- tuple (r_thr, dbr_thr) from ppn.compute_rain_threshold()
        callback -- leadtime callback for ensemble nowcasts written separately

    Deterministic nowcasts use LINDA without perturbations or any other pysteps
    nowcast method (e.g. extrapolation) with the latest observation.
    """
    if kind == "deterministic":
        if method == "linda":
            kwargs = pysteps_kwargs(method, configuration, rain_thresholds)
            kwargs["add_perturbations"] = False
            kwargs["return_output"] = True
            kwargs["callback"] = None
            kwargs["n_ens_members"] = 1
            # LINDA needs the last ari_order+2 observations
            n_obs = kwargs["ari_order"] + 2
            return Nowcaster(
                method,
                pysteps.nowcasts.get_method(method),
                kwargs,
                select_observations=lambda obs: obs[-n_obs:],
            )
        # Extrapolation-type method with one input timestep
        return Nowcaster(
            method,
            pysteps.nowcasts.get_method(method),
            {},
            select_observations=lambda obs: obs[-1],
        )

    if kind == "ensemble":
        if method not in ENSEMBLE_METHODS:
            raise NotImplementedError(
                f"nowcast_method = {method} not implemented, possible values are "
                + ", ".join(f"'{m}'" for m in ENSEMBLE_METHODS)
            )
        return Nowcaster(
            method,
            pysteps.nowcasts.get_method(method),
            pysteps_kwargs(method, configuration, rain_thresholds, callback),
        )

    raise ValueError(f"Unknown nowcast kind {kind!r}")
