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


def test_deterministic_run_without_ensemble_method(tmp_path):
    # A deterministic-only run does not depend on run_options.nowcast_method,
    # except for the method attributes written in /how
    output = golden.run_case(
        "det",
        tmp_path / "det",
        extra_overrides={"run_options": {"nowcast_method": "not-a-method"}},
    )
    diffs = golden.compare_dirs(golden.GOLDEN_DIR / "det", output)
    # Differences are "<file>: <object>: <message>"
    assert diffs
    assert all(d.split(": ")[1] == "how" for d in diffs), diffs
