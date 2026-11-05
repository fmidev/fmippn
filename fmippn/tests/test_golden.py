"""Compare FMI-PPN output against recorded golden-master baselines (see golden.py)."""

import pytest

import golden

pytestmark = pytest.mark.skipif(
    not golden.input_files() or not golden.GOLDEN_DIR.is_dir(),
    reason=f"golden-master input ({golden.INPUT_DIR}) or baseline ({golden.GOLDEN_DIR}) missing",
)


@pytest.mark.parametrize("case", sorted(golden.CASES))
def test_output_matches_baseline(case, tmp_path):
    output = golden.run_case(case, tmp_path / case)
    assert golden.compare_dirs(golden.GOLDEN_DIR / case, output) == []
