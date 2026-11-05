"""Golden-master runs of FMI-PPN for refactoring safety.

Each case derives a short, seeded configuration from an operational config,
runs FMI-PPN in a subprocess on the ODIM composites in the test input folder
and compares the output HDF5 files against a recorded baseline.

Record baselines (on code known to be correct):

    python tests/golden.py record [--out DIR]

Compare two output folders:

    python tests/golden.py compare DIR_A DIR_B
"""

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import h5py
import numpy as np

FMIPPN_DIR = Path(__file__).resolve().parents[1]
TESTDATA_DIR = FMIPPN_DIR / "tests" / "testdata"
INPUT_DIR = Path(os.environ.get("FMIPPN_TEST_INPUT", TESTDATA_DIR / "odim"))
GOLDEN_DIR = Path(os.environ.get("FMIPPN_GOLDEN_DIR", TESTDATA_DIR / "golden"))

# Overrides applied to every case: short leadtimes, few members, fixed seed
COMMON_OVERRIDES = {
    "nowcast_options": {"seed": 1, "num_workers": 2, "n_ens_members": 2},
    "run_options": {"max_leadtime": 30},
    "logging": {"write_log": False},
    "callback_options": {"tmp_folder": ""},
}

# case name -> (base config, extra overrides, index of input file to leave out)
CASES = {
    "det": ("finradfast-det", {}, None),
    "ens": ("finradfast-ens", {}, None),
    # Missing observation at t-10 min: input is trimmed to the last continuous files
    "det_missing": ("finradfast-det", {}, -3),
}


def input_files(input_dir=INPUT_DIR):
    """Return the sorted ODIM input files of the test case."""
    return sorted(Path(input_dir).glob("*.h5"))


def latest_timestamp(input_dir=INPUT_DIR):
    """Return the initialisation time (YYYYMMDDHHMM) of the latest input file."""
    return input_files(input_dir)[-1].name[:12]


def _deep_update(target, overrides):
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
    return target


def make_config(base, overrides, input_dir, output_dir, config_dir):
    """Write a test configuration derived from config/<base>.json and return its path."""
    with open(FMIPPN_DIR / "config" / f"{base}.json") as f:
        params = json.load(f)
    _deep_update(params, copy.deepcopy(COMMON_OVERRIDES))
    _deep_update(params, copy.deepcopy(overrides))
    _deep_update(
        params,
        {
            "data_source": {"root_path": str(input_dir)},
            "output_options": {"path": str(output_dir)},
            "logging": {"log_folder": str(output_dir)},
        },
    )
    path = Path(config_dir) / f"{base}.json"
    with open(path, "w") as f:
        json.dump(params, f, indent=2)
    return path


def run_case(name, output_dir, input_dir=INPUT_DIR, extra_overrides=None):
    """Run one golden-master case, writing its output files into output_dir."""
    base, overrides, drop_index = CASES[name]
    overrides = _deep_update(copy.deepcopy(overrides), extra_overrides or {})
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = latest_timestamp(input_dir)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if drop_index is not None:
            # Link all input files except one into a separate folder
            case_input = tmp / "input"
            case_input.mkdir()
            files = input_files(input_dir)
            dropped = files[drop_index]
            for fname in files:
                if fname != dropped:
                    (case_input / fname.name).symlink_to(fname.resolve())
        else:
            case_input = Path(input_dir).resolve()

        make_config(base, overrides, case_input, output_dir, tmp)
        env = dict(
            os.environ,
            OMP_NUM_THREADS="1",
            HDF5_USE_FILE_LOCKING="FALSE",
            PYSTEPSRC=str(FMIPPN_DIR / "pystepsrc"),
        )
        # The config name ends up in output filenames, so run from the config
        # folder and pass the bare name as in operational runs
        subprocess.run(
            [
                sys.executable,
                str(FMIPPN_DIR / "run_ppn.py"),
                "-c",
                base,
                "-t",
                timestamp,
            ],
            cwd=tmp,
            env=env,
            check=True,
        )
    return output_dir


def _attrs_differ(a, b):
    if set(a.keys()) != set(b.keys()):
        return f"attribute names {sorted(a.keys())} != {sorted(b.keys())}"
    for key in a.keys():
        va, vb = np.asarray(a[key]), np.asarray(b[key])
        if va.shape != vb.shape or not np.array_equal(va, vb):
            return f"attribute {key!r}: {a[key]!r} != {b[key]!r}"
        # h5py reads e.g. null-padded and null-terminated strings to the same value
        ta, tb = a.get_id(key).get_type(), b.get_id(key).get_type()
        if ta != tb:
            return f"attribute {key!r}: HDF5 type {_describe_type(ta)} != {_describe_type(tb)}"
    return None


def _describe_type(tid):
    if isinstance(tid, h5py.h5t.TypeStringID):
        if tid.is_variable_str():
            return "variable-length string"
        pad = {
            h5py.h5t.STR_NULLTERM: "null-terminated",
            h5py.h5t.STR_NULLPAD: "null-padded",
        }
        return f"fixed {tid.get_size()}-byte {pad.get(tid.get_strpad(), 'space-padded')} string"
    return str(tid.dtype)


def compare_files(path_a, path_b):
    """Return a list of differences between two HDF5 files."""
    diffs = []
    with h5py.File(path_a, "r") as fa, h5py.File(path_b, "r") as fb:
        names_a, names_b = [], []
        fa.visit(names_a.append)
        fb.visit(names_b.append)
        if sorted(names_a) != sorted(names_b):
            diffs.append(f"objects differ: {sorted(set(names_a) ^ set(names_b))}")
        for name in ["/"] + sorted(set(names_a) & set(names_b)):
            oa, ob = fa[name], fb[name]
            msg = _attrs_differ(oa.attrs, ob.attrs)
            if msg:
                diffs.append(f"{name}: {msg}")
            if isinstance(oa, h5py.Dataset):
                da, db = oa[()], ob[()]
                if da.dtype != db.dtype or not np.array_equal(
                    da, db, equal_nan=da.dtype.kind == "f"
                ):
                    diffs.append(f"{name}: data differs")
    return diffs


def compare_dirs(dir_a, dir_b):
    """Return a list of differences between the HDF5 files of two output folders."""
    files_a = {p.relative_to(dir_a) for p in Path(dir_a).rglob("*.h5")}
    files_b = {p.relative_to(dir_b) for p in Path(dir_b).rglob("*.h5")}
    diffs = [f"only in {dir_a}: {p}" for p in sorted(files_a - files_b)]
    diffs += [f"only in {dir_b}: {p}" for p in sorted(files_b - files_a)]
    for rel in sorted(files_a & files_b):
        diffs += [
            f"{rel}: {d}" for d in compare_files(Path(dir_a) / rel, Path(dir_b) / rel)
        ]
    return diffs


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record", help="Run all cases and store the outputs")
    rec.add_argument("--out", type=Path, default=GOLDEN_DIR)
    cmp = sub.add_parser("compare", help="Compare two output folders")
    cmp.add_argument("dir_a", type=Path)
    cmp.add_argument("dir_b", type=Path)
    args = parser.parse_args()

    if args.command == "record":
        for name in CASES:
            out = args.out / name
            if out.exists():
                shutil.rmtree(out)
            run_case(name, out)
            print(f"Recorded {name} -> {out}")
    else:
        diffs = compare_dirs(args.dir_a, args.dir_b)
        print("\n".join(diffs) if diffs else "Identical")
        sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
