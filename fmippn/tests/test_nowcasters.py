import copy

import numpy as np
import pytest

import nowcasters
import ppn
import ppn_config


def test_method_options_merges_without_mutating():
    nowcast_options = copy.deepcopy(ppn_config.defaults["nowcast_options"])
    nowcast_options["n_cascade_levels"] = 8
    original = copy.deepcopy(nowcast_options)

    options = nowcasters.method_options(nowcast_options, "steps")

    assert nowcast_options == original
    assert "method_specific_options" not in options
    # Method-specific options override common ones
    assert options["n_cascade_levels"] == 6
    assert options["num_workers"] == nowcast_options["num_workers"]


def test_method_options_unknown_method_has_common_options_only():
    nowcast_options = copy.deepcopy(ppn_config.defaults["nowcast_options"])
    options = nowcasters.method_options(nowcast_options, "extrapolation")
    assert "n_cascade_levels" not in options
    assert options["seed"] is None


@pytest.mark.parametrize(
    "method, expected",
    [
        (
            "steps",
            {
                "ensemble_nowcast_method": "steps",
                "domain": "spectral",
                "n_cascade_levels": 6,
            },
        ),
        (
            "linda",
            {
                "ensemble_nowcast_method": "linda",
                "feature_method": "domain",
                "ari_order": "1",
                "max_num_features": "25",
            },
        ),
        ("extrapolation", {}),
    ],
)
def test_method_how_attrs(pd_config, method, expected):
    pd_config["run_options"]["nowcast_method"] = method
    assert nowcasters.method_how_attrs(pd_config) == expected


@pytest.fixture
def output_config(pd_config):
    pd_config["input_quantity"] = "DBZH"
    pd_config["data_undetect"] = -32.0
    pd_config["output_options"]["as_quantity"] = "DBZH"
    pd_config["data_options"]["rain_threshold"] = 8
    return pd_config


def test_postprocess_forecast_dbz(output_config):
    forecast = np.array([[[0.0, 7.9], [8.0, 40.0]]])
    meta = {"unit": "dBZ", "transform": None, "threshold": 8, "zerovalue": -10}

    out, out_meta = ppn.postprocess_forecast(forecast, meta)

    np.testing.assert_array_equal(out, [[[-32.0, -32.0], [8.0, 40.0]]])
    assert out_meta["zerovalue"] == -32.0
    assert out_meta["threshold"] == 8


def test_postprocess_forecast_dbr_to_dbz(output_config):
    # 10 dBR = 10 mm/h -> Z = 223 * 10**1.53. -30 dBR is raised to the zero
    # value (-15 dBR, about 0.5 dBZ), which is below the 8 dBZ output threshold.
    forecast = np.array([[[10.0, -30.0]]])
    meta = {"unit": "mm/h", "transform": "dB", "threshold": -10.0, "zerovalue": -15.0}

    out, out_meta = ppn.postprocess_forecast(forecast, meta)

    expected_dbz = 10 * np.log10(223.0 * 10**1.53)
    np.testing.assert_allclose(out, [[[expected_dbz, -32.0]]])
    assert out_meta["unit"] == "dBZ"


def test_prepare_pysteps_observations(pd_config):
    pd_config["converted_rain_thr"] = 8.0
    pd_config["input_quantity"] = "DBZH"
    pd_config["run_options"]["steps_set_no_rain_to_value"] = -10
    obs = np.array([[[np.nan, 5.0], [8.0, 30.0]]])
    meta = {"unit": "dBZ", "transform": None, "threshold": -32, "zerovalue": -32}

    prepared, prepared_meta = nowcasters.prepare_pysteps_observations(
        obs, meta, pd_config
    )

    np.testing.assert_array_equal(prepared, [[[-10.0, -10.0], [8.0, 30.0]]])
    assert prepared_meta["zerovalue"] == -10
    assert prepared_meta["threshold"] == 8.0
    # Inputs are kept intact
    assert np.isnan(obs[0, 0, 0])
    assert meta["zerovalue"] == -32


@pytest.fixture
def nowcast_config(pd_config):
    pd_config["nowcast_options"]["n_ens_members"] = 3
    pd_config["output_options"]["write_leadtimes_separately"] = True
    return pd_config


def callback(field):
    pass


def test_deterministic_extrapolation(nowcast_config):
    nc = nowcasters.get_nowcaster(
        "extrapolation", "deterministic", nowcast_config, (8.0, None)
    )
    assert nc.kwargs == {}
    obs = np.zeros((3, 4, 5))
    assert nc.select_observations(obs).shape == (4, 5)


def test_deterministic_linda(nowcast_config):
    nc = nowcasters.get_nowcaster("linda", "deterministic", nowcast_config, (8.0, None))
    assert nc.kwargs["add_perturbations"] is False
    assert nc.kwargs["return_output"] is True
    assert nc.kwargs["callback"] is None
    assert nc.kwargs["n_ens_members"] == 1
    # ari_order 1 -> 3 latest observations
    obs = np.arange(5)[:, None, None] * np.ones((5, 2, 2))
    np.testing.assert_array_equal(nc.select_observations(obs)[:, 0, 0], [2, 3, 4])


def test_ensemble_steps(nowcast_config):
    nc = nowcasters.get_nowcaster(
        "steps", "ensemble", nowcast_config, (0.5, 3.0), callback=callback
    )
    assert nc.kwargs["precip_thr"] == 3.0
    assert nc.kwargs["callback"] is callback
    assert nc.kwargs["return_output"] is False
    assert nc.kwargs["n_ens_members"] == 3
    assert nc.kwargs["n_cascade_levels"] == 6
    assert "method_specific_options" in nowcast_config["nowcast_options"]
    obs = np.zeros((3, 4, 5))
    assert nc.select_observations(obs) is obs


def test_ensemble_steps_without_dbr_threshold(nowcast_config):
    nowcast_config["output_options"]["write_leadtimes_separately"] = False
    nc = nowcasters.get_nowcaster("steps", "ensemble", nowcast_config, (8.0, None))
    assert nc.kwargs["precip_thr"] == 8.0
    assert "callback" not in nc.kwargs


@pytest.mark.parametrize("method", ["extrapolation", "not-a-method"])
def test_ensemble_unknown_method_raises(nowcast_config, method):
    with pytest.raises(NotImplementedError):
        nowcasters.get_nowcaster(method, "ensemble", nowcast_config, (8.0, None))
