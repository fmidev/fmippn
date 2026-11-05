import h5py
import numpy as np
import pytest

import utils


@pytest.mark.parametrize("value", ["DBZH", b"DBZH", np.bytes_(b"DBZH")])
def test_set_attr_stores_null_terminated_string(tmp_path, value):
    with h5py.File(tmp_path / "test.h5", "w") as f:
        utils.set_attr(f.attrs, "quantity", value)

    with h5py.File(tmp_path / "test.h5", "r") as f:
        tid = f.attrs.get_id("quantity").get_type()
        assert not tid.is_variable_str()
        assert tid.get_strpad() == h5py.h5t.STR_NULLTERM
        assert tid.get_size() == len("DBZH") + 1
        assert f.attrs["quantity"] == b"DBZH"


def test_set_attr_keeps_numbers(tmp_path):
    with h5py.File(tmp_path / "test.h5", "w") as f:
        utils.set_attr(f.attrs, "gain", 0.01)

    with h5py.File(tmp_path / "test.h5", "r") as f:
        assert f.attrs["gain"] == 0.01
        assert f.attrs["gain"].dtype == np.float64
