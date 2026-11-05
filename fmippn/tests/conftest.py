import copy
import sys
from pathlib import Path

import pytest

# Make the fmippn modules importable as top-level modules, as run_ppn.py does
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ppn  # noqa: E402
import ppn_config  # noqa: E402


@pytest.fixture
def pd_config():
    """Fill the global ppn.PD with the default configuration and reset it afterwards."""
    saved = copy.deepcopy(ppn.PD)
    ppn.PD.clear()
    ppn.PD.update(copy.deepcopy(ppn_config.defaults))
    yield ppn.PD
    ppn.PD.clear()
    ppn.PD.update(saved)
