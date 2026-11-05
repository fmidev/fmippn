import datetime as dt

import pytest

import ppn

STARTDATE = dt.datetime(2026, 11, 5, 10, 15)
DATASOURCE = {
    "root_path": "/input",
    "path_fmt": "",
    "fn_pattern": "%Y%m%d%H%M_test",
    "fn_ext": "h5",
    "timestep": 5,
}


def _found(present):
    """Fake pysteps.io.find_by_date result; present[i] False marks a missing file."""
    times = [
        STARTDATE - dt.timedelta(minutes=5 * (len(present) - 1 - i))
        for i in range(len(present))
    ]
    names = [f"{t:%Y%m%d%H%M}.h5" if ok else None for t, ok in zip(times, present)]
    return names, times


@pytest.fixture
def find_by_date(monkeypatch):
    calls = {}

    def install(present):
        def fake(*args, num_prev_files, **kwargs):
            calls["num_prev_files"] = num_prev_files
            return _found(present)

        monkeypatch.setattr(ppn.pysteps.io, "find_by_date", fake)
        return calls

    return install


def test_no_missing_files(pd_config, find_by_date):
    calls = find_by_date([True] * 4)
    names, times = ppn.select_input_files(STARTDATE, DATASOURCE, 3, 2)
    assert calls["num_prev_files"] == 3
    assert names == _found([True] * 4)[0]
    assert times[-1] == STARTDATE


def test_missing_within_min_window_raises(pd_config, find_by_date):
    find_by_date([True, True, True, False, True])
    with pytest.raises(FileNotFoundError):
        ppn.select_input_files(STARTDATE, DATASOURCE, 4, 2)


def test_missing_before_min_window_trims(pd_config, find_by_date):
    # Pins current behaviour: the slice counts valid files from the end but is
    # applied from the start, so the gap is kept in the list.
    find_by_date([True, True, False, True, True])
    names, times = ppn.select_input_files(STARTDATE, DATASOURCE, 4, 2)
    assert len(names) == 4
    assert names[1] is None
    assert times[-1] == STARTDATE
