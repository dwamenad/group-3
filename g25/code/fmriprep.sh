#!/usr/bin/env bash

set -euo pipefail

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
projectdir="$(dirname "$scriptdir")"
bidsdir="${BIDS_DIR:-${projectdir}/bids}"
outdir="${FMRIPREP_OUTDIR:-${projectdir}/derivatives/fmriprep}"
filterfile="${BIDS_FILTER_FILE:-${projectdir}/code/fmriprep_config.json}"

subject="${1:-}"
if [ -z "$subject" ]; then
  echo "Usage: $(basename "$0") <subject-id-without-sub-prefix>"
  echo "Example: $(basename "$0") 11039"
  exit 1
fi

subject="${subject#sub-}"

singularity_cmd="${SINGULARITY_CMD:-singularity}"
fmriprep_image="${FMRIPREP_IMAGE:-}"
scratch_base="${SCRATCH_BASE:-$HOME/scratch/g25}"
scratchdir="${scratch_base}/fmriprep/sub-${subject}"
dry_run="${DRY_RUN:-0}"

templateflow_dir="${TEMPLATEFLOW_DIR:-}"
mplconfigdir_dir="${MPLCONFIGDIR_DIR:-}"
fs_license_file="${FS_LICENSE_FILE:-}"

if [ -z "$templateflow_dir" ] && [ -n "${TOOLS_DIR:-}" ]; then
  templateflow_dir="${TOOLS_DIR}/templateflow"
fi
if [ -z "$mplconfigdir_dir" ] && [ -n "${TOOLS_DIR:-}" ]; then
  mplconfigdir_dir="${TOOLS_DIR}/mplconfigdir"
fi
if [ -z "$fs_license_file" ] && [ -n "${TOOLS_DIR:-}" ]; then
  fs_license_file="${TOOLS_DIR}/licenses/fs_license.txt"
fi
if [ -z "$fmriprep_image" ] && [ -n "${TOOLS_DIR:-}" ]; then
  fmriprep_image="${TOOLS_DIR}/fmriprep-24.1.1.simg"
fi

image_arg="${fmriprep_image:-<FMRIPREP_IMAGE>}"

if [ ! -d "${bidsdir}/sub-${subject}" ]; then
  echo "ERROR: Missing BIDS directory ${bidsdir}/sub-${subject}"
  exit 2
fi

mkdir -p "$outdir" "$scratchdir"

cmd=(
  "$singularity_cmd" run --cleanenv
  -B "${projectdir}:/base"
  -B "${scratchdir}:/scratch"
)

if [ -n "$templateflow_dir" ]; then
  cmd+=(-B "${templateflow_dir}:/opt/templateflow")
fi
if [ -n "$mplconfigdir_dir" ]; then
  cmd+=(-B "${mplconfigdir_dir}:/opt/mplconfigdir")
fi
if [ -n "$fs_license_file" ]; then
  cmd+=(-B "$(dirname "$fs_license_file"):/opts")
fi

cmd+=(
  "$image_arg"
  /base/bids /base/derivatives/fmriprep
  participant --participant_label "$subject"
  --stop-on-first-crash
  --skip-bids-validation
  --nthreads 14
  --me-output-echos
  --output-spaces MNI152NLin6Asym
  --bids-filter-file /base/code/fmriprep_config.json
  --fs-no-reconall
  -w /scratch
)

if [ -n "$fs_license_file" ]; then
  cmd+=(--fs-license-file "/opts/$(basename "$fs_license_file")")
fi

echo "Subject: sub-${subject}"
echo "BIDS dir: ${bidsdir}"
echo "Output dir: ${outdir}"
echo "Scratch dir: ${scratchdir}"
echo "Filter file: ${filterfile}"
echo "TemplateFlow dir: ${templateflow_dir:-<unset>}"
echo "Matplotlib config dir: ${mplconfigdir_dir:-<unset>}"
echo "FreeSurfer license: ${fs_license_file:-<unset>}"
echo "fMRIPrep image: ${fmriprep_image:-<unset>}"
echo "Command:"
printf ' %q' "${cmd[@]}"
printf '\n'

if [ "$dry_run" = "1" ]; then
  missing=()
  for required_var in templateflow_dir mplconfigdir_dir fs_license_file fmriprep_image; do
    if [ -z "${!required_var}" ]; then
      missing+=("$required_var")
    fi
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "Missing prerequisites for a real run: ${missing[*]}"
  fi
  echo "DRY_RUN=1, command not executed."
  exit 0
fi

if ! command -v "$singularity_cmd" >/dev/null 2>&1; then
  echo "ERROR: Cannot find container runtime '${singularity_cmd}'."
  echo "Set SINGULARITY_CMD, or rerun with DRY_RUN=1 for a preflight-only check."
  exit 3
fi

for required_path in "$templateflow_dir" "$mplconfigdir_dir" "$fs_license_file" "$fmriprep_image" "$filterfile"; do
  if [ ! -e "$required_path" ]; then
    echo "ERROR: Missing required path: ${required_path}"
    exit 4
  fi
done

export SINGULARITYENV_TEMPLATEFLOW_HOME=/opt/templateflow
export SINGULARITYENV_MPLCONFIGDIR=/opt/mplconfigdir

"${cmd[@]}"
