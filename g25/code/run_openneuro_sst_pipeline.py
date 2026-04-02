#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import json
import os
import re
import shutil
import ssl
import struct
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path


DATASET_ID = "ds007486"
SNAPSHOT_TAG = "1.0.0"
OPENNEURO_API = "https://openneuro.org/crn/graphql"
APPROVED_SUBJECTS = ["sub-10562", "sub-10665", "sub-11028", "sub-11039", "sub-11450"]
ROOT_METADATA_FILES = [
    "CHANGES",
    "README",
    "dataset_description.json",
    "participants.json",
    "participants.tsv",
    "scans.json",
    "task-SST_bold.json",
]


def log(message: str) -> None:
    print(message, flush=True)


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    log("$ " + " ".join(cmd))
    run_env = dict(os.environ)
    if env:
        run_env.update(env)
    if cwd is not None:
        run_env["PWD"] = str(cwd)
        run_env["OLDPWD"] = str(cwd)
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=run_env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout, end="")
    if result.stderr.strip():
        print(result.stderr, end="", file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed with code {result.returncode}: {' '.join(cmd)}")
    return result


def update_env_from_env0(env_dump: bytes) -> None:
    for entry in env_dump.split(b"\0"):
        if not entry or b"=" not in entry:
            continue
        key, value = entry.split(b"=", 1)
        os.environ[key.decode(errors="ignore")] = value.decode(errors="ignore")


def ensure_fsl_on_path() -> tuple[bool, str | None]:
    required_tools = ("feat", "mcflirt", "fslnvols")
    if all(shutil.which(tool) for tool in required_tools):
        return True, "already-on-path"

    attempts = [
        ("ml fsl", "type ml >/dev/null 2>&1 && ml fsl"),
        ("module load fsl", "type module >/dev/null 2>&1 && module load fsl"),
    ]
    for label, shell_cmd in attempts:
        result = subprocess.run(
            ["bash", "-lc", f"{shell_cmd} >/dev/null 2>&1 && env -0"],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0 or not result.stdout:
            continue
        update_env_from_env0(result.stdout)
        if all(shutil.which(tool) for tool in required_tools):
            return True, label

    return False, None


def gql(query: str) -> dict:
    payload = json.dumps({"query": query}).encode("utf-8")
    req = urllib.request.Request(
        OPENNEURO_API,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, context=ssl._create_unverified_context()) as resp:
        return json.load(resp)


def snapshot_files(tree: str | None = None) -> list[dict]:
    if tree:
        query = f'''query {{
          snapshot(datasetId: "{DATASET_ID}", tag: "{SNAPSHOT_TAG}") {{
            files(tree: "{tree}") {{ filename directory key size urls }}
          }}
        }}'''
    else:
        query = f'''query {{
          snapshot(datasetId: "{DATASET_ID}", tag: "{SNAPSHOT_TAG}") {{
            files {{ filename directory key size urls }}
          }}
        }}'''
    return gql(query)["data"]["snapshot"]["files"]


def project_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def choose_runtime_paths(project_root: Path) -> tuple[Path, Path, str]:
    if " " not in str(project_root):
        runtime_root = project_root / "output" / "jupyter-notebook" / "_runtime"
        runtime_root.mkdir(parents=True, exist_ok=True)
        return runtime_root, project_root, "project-local"

    runtime_root = Path(tempfile.gettempdir()) / f"{project_root.name}_openneuro_runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_project = runtime_root / project_root.name
    if runtime_project.is_symlink() or runtime_project.exists():
        if runtime_project.resolve() != project_root.resolve():
            runtime_project.unlink()
    if not runtime_project.exists():
        runtime_project.symlink_to(project_root, target_is_directory=True)
    return runtime_root, runtime_project, "tmp-symlink"


def ensure_bidsutils(project_root: Path) -> Path:
    candidates = [
        project_root / "tools" / "bidsutils" / "BIDSto3col" / "BIDSto3col.sh",
        project_root / "output" / "jupyter-notebook" / "_vendor" / "bidsutils" / "BIDSto3col" / "BIDSto3col.sh",
        project_root.parent / "rf1-ug" / "code" / "BIDSto3col.sh",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    target_root = project_root / "tools" / "bidsutils"
    target_root.parent.mkdir(parents=True, exist_ok=True)
    if not target_root.exists():
        run(["git", "clone", "https://github.com/bids-standard/bidsutils.git", str(target_root)])
    converter = target_root / "BIDSto3col" / "BIDSto3col.sh"
    if not converter.exists():
        raise FileNotFoundError(f"Missing BIDSto3col.sh after clone: {converter}")
    return converter


def ensure_root_metadata(project_root: Path, root_rows: list[dict]) -> None:
    bids_root = project_root / "bids"
    bids_root.mkdir(parents=True, exist_ok=True)
    url_map = {row["filename"]: row["urls"][0] for row in root_rows if row.get("urls")}
    for filename in ROOT_METADATA_FILES:
        if filename not in url_map:
            continue
        destination = bids_root / filename
        if destination.exists() and destination.stat().st_size > 0:
            continue
        log(f"Downloading dataset-level file {filename}")
        with urllib.request.urlopen(url_map[filename], context=ssl._create_unverified_context()) as resp:
            destination.write_bytes(resp.read())


def subject_tree_keys(root_rows: list[dict], subjects: list[str]) -> dict[str, str]:
    return {row["filename"]: row["key"] for row in root_rows if row["directory"] and row["filename"] in subjects}


def select_subject_files(
    subject: str,
    anat_rows: list[dict],
    func_rows: list[dict],
    runs: list[int],
    include_feat_inputs: bool = True,
) -> list[dict]:
    run_token = "|".join(str(run) for run in runs)
    anat_re = re.compile(rf"^{re.escape(subject)}_T1w(\.json|\.nii\.gz)$")
    event_re = re.compile(rf"^{re.escape(subject)}_task-SST_run-({run_token})_events\.tsv$")
    bold_re = re.compile(rf"^{re.escape(subject)}_task-SST_run-({run_token})_echo-1_part-mag_bold(\.json|\.nii\.gz)$")
    selected = []
    if include_feat_inputs:
        for row in anat_rows:
            if row.get("urls") and anat_re.match(row["filename"]):
                selected.append(row)
    for row in func_rows:
        if not row.get("urls"):
            continue
        if event_re.match(row["filename"]) or (include_feat_inputs and bold_re.match(row["filename"])):
            selected.append(row)
    return selected


def is_valid_nifti_gz(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        with gzip.open(path, "rb") as src:
            header = src.read(352)
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                pass
    except OSError:
        return False
    if len(header) < 352:
        return False
    sizeof_hdr_le = struct.unpack("<I", header[:4])[0]
    sizeof_hdr_be = struct.unpack(">I", header[:4])[0]
    return sizeof_hdr_le == 348 or sizeof_hdr_be == 348


def ensure_uncompressed_nifti(source_path: Path, destination_path: Path) -> Path:
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists() and destination_path.stat().st_size > 0:
        if destination_path.stat().st_mtime >= source_path.stat().st_mtime:
            return destination_path
        destination_path.unlink()

    tmp_path = destination_path.with_name(destination_path.name + ".tmp")
    if tmp_path.exists():
        tmp_path.unlink()

    if source_path.name.endswith(".nii.gz"):
        with gzip.open(source_path, "rb") as src, tmp_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    else:
        shutil.copy2(source_path, tmp_path)

    if not tmp_path.exists() or tmp_path.stat().st_size == 0:
        raise RuntimeError(f"Failed to materialize runtime NIfTI for {source_path}")
    os.replace(tmp_path, destination_path)
    return destination_path


def download_rows(rows: list[dict], destination_dir: Path) -> list[Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    downloaded: list[Path] = []
    for row in rows:
        target = destination_dir / row["filename"]
        if target.name.endswith(".nii.gz") and target.exists() and not is_valid_nifti_gz(target):
            log(f"Cached file is not a valid NIfTI, deleting and redownloading: {target.name}")
            target.unlink()
        if target.exists() and target.stat().st_size > 0:
            downloaded.append(target)
            continue
        log(f"Downloading {target.name}")
        with urllib.request.urlopen(row["urls"][0], context=ssl._create_unverified_context()) as resp:
            target.write_bytes(resp.read())
        if target.name.endswith(".nii.gz") and not is_valid_nifti_gz(target):
            raise RuntimeError(f"Downloaded file is not a valid gzipped NIfTI: {target}")
        downloaded.append(target)
    return downloaded


def write_mcflirt_tsv(par_file: Path, tsv_file: Path) -> None:
    headers = ["rot_x", "rot_y", "rot_z", "trans_x", "trans_y", "trans_z"]
    with par_file.open() as src, tsv_file.open("w", newline="") as dst:
        writer = csv.writer(dst, delimiter="\t")
        writer.writerow(headers)
        for line in src:
            parts = line.strip().split()
            if parts:
                writer.writerow(parts[:6])


def compute_fd_from_mcflirt(par_file: Path) -> list[float]:
    rows: list[list[float]] = []
    with par_file.open() as src:
        for line in src:
            parts = line.strip().split()
            if parts:
                rows.append([float(value) for value in parts[:6]])

    fd_values: list[float] = []
    previous: list[float] | None = None
    for row in rows:
        if previous is None:
            fd_values.append(0.0)
        else:
            rot = sum(abs(row[index] - previous[index]) for index in range(3))
            trans = sum(abs(row[index] - previous[index]) for index in range(3, 6))
            fd_values.append((50.0 * rot) + trans)
        previous = row
    return fd_values


def write_fd_metric(fd_values: list[float], metric_file: Path) -> None:
    metric_file.write_text("".join(f"{value:.6f}\n" for value in fd_values))


def write_fd_plot(fd_values: list[float], plot_file: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        log(f"SKIP: could not create FD plot at {plot_file} ({exc})")
        return

    figure, axis = plt.subplots(figsize=(10, 3))
    axis.plot(range(len(fd_values)), fd_values, linewidth=1.2)
    axis.set_title("Framewise displacement from MCFLIRT parameters")
    axis.set_xlabel("Volume")
    axis.set_ylabel("FD (mm)")
    axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(plot_file, dpi=150)
    plt.close(figure)


def generate_sst_evs(project_root: Path, converter: Path, subject: str, runs: list[int]) -> None:
    func_dir = project_root / "bids" / subject / "func"
    ev_dir = project_root / "derivatives" / "fsl" / "EVfiles" / subject / "SST"
    ev_dir.mkdir(parents=True, exist_ok=True)

    for run_id in runs:
        events = func_dir / f"{subject}_task-SST_run-{run_id}_events.tsv"
        if not events.exists():
            log(f"SKIP: cannot locate {events}")
            continue
        run_prefix = ev_dir / f"run-{run_id}"
        run(["bash", str(converter), str(events), str(run_prefix)])


def choose_sst_model(ev_dir: Path, run: int) -> tuple[str, int]:
    go_incorrect = ev_dir / f"run-{run}_go_incorrect.txt"
    go_miss = ev_dir / f"run-{run}_go_miss.txt"
    if go_incorrect.exists():
        model = "1a"
    else:
        model = "1b"
    ev_shape = 3 if go_miss.exists() else 10
    return model, ev_shape


def apply_registration_fix(feat_dir: Path, feat_bin: Path) -> None:
    fsl_dir = feat_bin.parent.parent
    ident = fsl_dir / "etc" / "flirtsch" / "ident.mat"
    mean_func = feat_dir / "mean_func.nii.gz"
    if not ident.exists() or not mean_func.exists():
        return
    reg_dir = feat_dir / "reg"
    reg_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ident, reg_dir / "example_func2standard.mat")
    shutil.copy2(ident, reg_dir / "standard2example_func.mat")
    shutil.copy2(mean_func, reg_dir / "standard.nii.gz")


def run_sst_firstlevel(
    project_root: Path,
    runtime_root: Path,
    runtime_project: Path,
    subject: str,
    runs: list[int],
    force: bool,
) -> list[dict]:
    summary: list[dict] = []
    fsl_ready, fsl_load_method = ensure_fsl_on_path()
    if fsl_load_method and fsl_load_method != "already-on-path":
        log(f"Loaded FSL environment with `{fsl_load_method}`")
    feat_bin = shutil.which("feat")
    mcflirt_bin = shutil.which("mcflirt")
    fslnvols_bin = shutil.which("fslnvols")
    if not fsl_ready or not all([feat_bin, mcflirt_bin, fslnvols_bin]):
        raise EnvironmentError(
            "FSL commands feat, mcflirt, and fslnvols must be on PATH. "
            "In Neurodesk, load FSL with `ml fsl` or `module load fsl` before rerunning if auto-load does not succeed."
        )

    deriv_root = runtime_project / "derivatives" / "fsl"
    conf_root = deriv_root / "confounds_openneuro" / subject
    conf_root.mkdir(parents=True, exist_ok=True)
    ev_dir = deriv_root / "EVfiles" / subject / "SST"
    project_feat_root = project_root / "derivatives" / "fsl" / subject
    project_feat_root.mkdir(parents=True, exist_ok=True)
    feat_runtime_root = runtime_root / "feat" / subject
    feat_runtime_root.mkdir(parents=True, exist_ok=True)

    for run_id in runs:
        func_dir = runtime_project / "bids" / subject / "func"
        bold_gz = func_dir / f"{subject}_task-SST_run-{run_id}_echo-1_part-mag_bold.nii.gz"
        events = func_dir / f"{subject}_task-SST_run-{run_id}_events.tsv"
        if not bold_gz.exists() or not events.exists():
            summary.append({"subject": subject, "run": run_id, "status": "skip-missing-inputs"})
            continue
        if not is_valid_nifti_gz(bold_gz):
            summary.append({"subject": subject, "run": run_id, "status": "skip-invalid-bold"})
            continue

        bold = ensure_uncompressed_nifti(
            bold_gz,
            feat_runtime_root / f"{subject}_task-SST_run-{run_id}_echo-1_part-mag_bold.nii",
        )

        mcf_base = conf_root / f"{subject}_task-SST_run-{run_id}_mcf"
        fd_metric = conf_root / f"{subject}_task-SST_run-{run_id}_fd-metric.txt"
        fd_plot = conf_root / f"{subject}_task-SST_run-{run_id}_fd-plot.png"
        confound_tsv = conf_root / f"{subject}_task-SST_run-{run_id}_mcflirt_confounds.tsv"

        if force or not mcf_base.with_suffix(".par").exists():
            run([mcflirt_bin, "-in", str(bold), "-out", str(mcf_base), "-plots", "-mats", "-report"])
        write_mcflirt_tsv(mcf_base.with_suffix(".par"), confound_tsv)
        fd_values = compute_fd_from_mcflirt(mcf_base.with_suffix(".par"))
        write_fd_metric(fd_values, fd_metric)
        write_fd_plot(fd_values, fd_plot)

        model, ev_shape = choose_sst_model(ev_dir, run_id)
        template = runtime_project / "templates" / f"L1_task-SST_model-{model}_type-act.fsf"
        runtime_output_root = feat_runtime_root / f"L1_task-SST_model-{model}_type-act_run-{run_id}_sm-5"
        runtime_feat_dir = Path(str(runtime_output_root) + ".feat")
        project_output_root = project_feat_root / f"L1_task-SST_model-{model}_type-act_run-{run_id}_sm-5"
        project_feat_dir = Path(str(project_output_root) + ".feat")
        fsf_path = feat_runtime_root / f"L1_{subject}_task-SST_model-{model}_run-{run_id}.fsf"

        nvols = run([fslnvols_bin, str(bold)], check=True).stdout.strip()
        fsf_text = (
            template.read_text()
            .replace("OUTPUT", str(runtime_output_root))
            .replace("DATA", str(mcf_base.with_suffix(".nii.gz")))
            .replace("EVDIR", str(ev_dir / f"run-{run_id}"))
            .replace("SMOOTH", "5")
            .replace("NVOLS", nvols)
            .replace("CONFOUNDEVS", str(mcf_base.with_suffix(".par")))
            .replace("EV_SHAPE", str(ev_shape))
        )
        fsf_path.write_text(fsf_text)

        if force or not (project_feat_dir / "stats" / "zstat1.nii.gz").exists():
            if runtime_feat_dir.exists():
                shutil.rmtree(runtime_feat_dir)
            run([feat_bin, str(fsf_path)], cwd=feat_runtime_root)
            apply_registration_fix(runtime_feat_dir, Path(feat_bin))
            if project_feat_dir.exists():
                shutil.rmtree(project_feat_dir)
            shutil.copytree(runtime_feat_dir, project_feat_dir)
            shutil.copy2(fsf_path, project_feat_root / fsf_path.name)

        summary.append(
            {
                "subject": subject,
                "run": run_id,
                "status": "ok",
                "model": model,
                "feat_dir": str(project_feat_dir.resolve()),
                "confounds_tsv": str((runtime_project / confound_tsv.relative_to(runtime_project)).resolve()),
                "fd_plot": str((runtime_project / fd_plot.relative_to(runtime_project)).resolve()),
            }
        )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download approved ds007486 SST files directly from OpenNeuro, generate EVs, and run portable first-level FEAT."
    )
    parser.add_argument("--subjects", nargs="+", default=APPROVED_SUBJECTS, help="Subject IDs like sub-11039")
    parser.add_argument("--runs", nargs="+", type=int, default=[1, 2, 3], help="SST run numbers to process")
    parser.add_argument("--skip-download", action="store_true", help="Do not download from OpenNeuro; use whatever is already in bids/")
    parser.add_argument("--skip-evs", action="store_true", help="Do not generate 3-column EV files")
    parser.add_argument("--skip-feat", action="store_true", help="Do not run first-level FEAT")
    parser.add_argument("--force", action="store_true", help="Re-download or re-run stages even if outputs already exist")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    subjects = sorted(dict.fromkeys(args.subjects))
    invalid = [subject for subject in subjects if not subject.startswith("sub-")]
    if invalid:
        raise ValueError(f"Subjects must include the 'sub-' prefix: {invalid}")

    project_root = project_root_from_script()
    runtime_root, runtime_project, runtime_mode = choose_runtime_paths(project_root)
    log(f"Runtime mode: {runtime_mode}")
    log(f"Runtime root: {runtime_root}")
    root_rows = snapshot_files()
    ensure_root_metadata(project_root, root_rows)
    subject_keys = subject_tree_keys(root_rows, subjects) if not args.skip_download else {}
    converter = ensure_bidsutils(project_root) if not args.skip_evs else None

    summary_rows: list[dict] = []
    for subject in subjects:
        if not args.skip_download:
            if subject not in subject_keys:
                raise FileNotFoundError(f"Subject not present in {DATASET_ID} {SNAPSHOT_TAG}: {subject}")
            subject_rows = snapshot_files(subject_keys[subject])
            dir_keys = {row["filename"]: row["key"] for row in subject_rows if row["directory"]}
            anat_rows = snapshot_files(dir_keys["anat"])
            func_rows = snapshot_files(dir_keys["func"])
            selected_rows = select_subject_files(
                subject,
                anat_rows,
                func_rows,
                args.runs,
                include_feat_inputs=not args.skip_feat,
            )
            if not args.skip_feat:
                download_rows(
                    [row for row in selected_rows if "_T1w" in row["filename"]],
                    project_root / "bids" / subject / "anat",
                )
            download_rows(
                [row for row in selected_rows if "_task-SST_" in row["filename"]],
                project_root / "bids" / subject / "func",
            )

        if not args.skip_evs and converter is not None:
            generate_sst_evs(project_root, converter, subject, args.runs)

        if not args.skip_feat:
            summary_rows.extend(run_sst_firstlevel(project_root, runtime_root, runtime_project, subject, args.runs, args.force))

    summary_path = project_root / "output" / "openneuro_sst_firstlevel_summary.tsv"
    fieldnames = ["subject", "run", "status", "model", "feat_dir", "confounds_tsv", "fd_plot"]
    if summary_rows:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        with summary_path.open("w", newline="") as dst:
            writer = csv.DictWriter(dst, fieldnames=fieldnames, delimiter="\t")
            writer.writeheader()
            for row in summary_rows:
                writer.writerow({key: row.get(key, "") for key in fieldnames})
        log(f"Wrote summary: {summary_path}")
    else:
        log("No FEAT runs were requested, so no FEAT summary table was written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
