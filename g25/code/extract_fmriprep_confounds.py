#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


DEFAULT_TASKS = ["SST", "trust", "adview"]
DEFAULT_RUNS = [1, 2, 3]
MOTION_COLS = ["trans_x", "trans_y", "trans_z", "rot_x", "rot_y", "rot_z"]
QC_COLS = ["framewise_displacement", "dvars"]
ACOMPCOR_COLS = [f"a_comp_cor_{idx:02d}" for idx in range(6)]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract a FEAT-friendly subset of fMRIPrep confounds across subjects/tasks/runs."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Path to the g25 project root.",
    )
    parser.add_argument(
        "--subjects",
        nargs="*",
        default=[],
        help="Subjects to process, with or without the sub- prefix. Defaults to all subjects with local BIDS folders.",
    )
    parser.add_argument(
        "--tasks",
        nargs="*",
        default=DEFAULT_TASKS,
        help="Tasks to scan. Defaults to SST trust adview.",
    )
    parser.add_argument(
        "--runs",
        nargs="*",
        type=int,
        default=DEFAULT_RUNS,
        help="Runs to scan. Defaults to 1 2 3.",
    )
    parser.add_argument(
        "--outdir",
        type=Path,
        default=None,
        help="Output directory for extracted confounds. Defaults to derivatives/fsl/confounds_fmriprep.",
    )
    return parser.parse_args()


def normalize_subjects(subjects: list[str], bids_root: Path) -> list[str]:
    if subjects:
        normalized = []
        for subject in subjects:
            clean = subject.removeprefix("sub-")
            normalized.append(f"sub-{clean}")
        return normalized
    return sorted(path.name for path in bids_root.glob("sub-*") if path.is_dir())


def select_confound_columns(frame: pd.DataFrame) -> list[str]:
    cols: list[str] = []
    cols.extend([col for col in QC_COLS if col in frame.columns])
    cols.extend([col for col in MOTION_COLS if col in frame.columns])
    cols.extend([col for col in ACOMPCOR_COLS if col in frame.columns])
    cols.extend(sorted(col for col in frame.columns if col.startswith("cosine")))
    cols.extend(sorted(col for col in frame.columns if col.startswith("non_steady_state_outlier")))
    return cols


def main() -> None:
    args = parse_args()
    project_root = args.project_root.resolve()
    bids_root = project_root / "bids"
    fmriprep_root = project_root / "derivatives" / "fmriprep"
    outdir = args.outdir.resolve() if args.outdir else (project_root / "derivatives" / "fsl" / "confounds_fmriprep")
    outdir.mkdir(parents=True, exist_ok=True)

    subjects = normalize_subjects(args.subjects, bids_root)
    records: list[dict[str, object]] = []

    for subject in subjects:
        for task in args.tasks:
            for run in args.runs:
                filename = f"{subject}_task-{task}_run-{run}_part-mag_desc-confounds_timeseries.tsv"
                source = fmriprep_root / subject / "func" / filename
                record: dict[str, object] = {
                    "subject": subject,
                    "task": task,
                    "run": run,
                    "source_file": str(source),
                }

                if not source.exists():
                    record["status"] = "missing"
                    record["n_input_columns"] = 0
                    record["n_output_columns"] = 0
                    record["output_file"] = ""
                    records.append(record)
                    continue

                frame = pd.read_csv(source, sep="\t")
                selected_cols = select_confound_columns(frame)
                confounds = frame[selected_cols].fillna(0)

                sub_outdir = outdir / subject
                sub_outdir.mkdir(parents=True, exist_ok=True)
                output = sub_outdir / f"{subject}_task-{task}_run-{run}_desc-fmriprepSelectedConfounds.tsv"
                confounds.to_csv(output, sep="\t", index=False, header=False)

                record["status"] = "written"
                record["n_input_columns"] = len(frame.columns)
                record["n_output_columns"] = len(selected_cols)
                record["selected_columns"] = ",".join(selected_cols)
                record["output_file"] = str(output)
                records.append(record)

    manifest = pd.DataFrame(records).sort_values(["subject", "task", "run"]).reset_index(drop=True)
    manifest_path = outdir / "confounds_manifest.csv"
    manifest.to_csv(manifest_path, index=False)
    print(manifest.to_string(index=False))
    print()
    print(f"Manifest saved to: {manifest_path}")


if __name__ == "__main__":
    main()
