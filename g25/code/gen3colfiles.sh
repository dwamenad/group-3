#!/usr/bin/env bash

set -euo pipefail

# Convert BIDS *_events.tsv files into FSL 3-column EV files.
# The script writes outputs under derivatives/fsl/EVfiles and tries a few
# project-local locations for BIDSto3col.sh before failing.

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
projectdir="$(dirname "$scriptdir")"
bidsdir="${projectdir}/bids"
baseout="${projectdir}/derivatives/fsl/EVfiles"

usage() {
  echo "Usage: $(basename "$0") <subject-id-without-sub-prefix> <task>"
  echo "Example: $(basename "$0") 11039 SST"
}

find_converter() {
  local candidates=(
    "${BIDSTO3COL_SCRIPT:-}"
    "${projectdir}/output/jupyter-notebook/_vendor/bidsutils/BIDSto3col/BIDSto3col.sh"
    "${projectdir}/tools/bidsutils/BIDSto3col/BIDSto3col.sh"
    "${projectdir}/../rf1-ug/code/BIDSto3col.sh"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [ -n "$candidate" ] && [ -f "$candidate" ]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if [ "$#" -ne 2 ]; then
  usage
  exit 1
fi

sub="$1"
task="$2"

if ! converter="$(find_converter)"; then
  echo "ERROR: Could not locate BIDSto3col.sh."
  echo "Set BIDSTO3COL_SCRIPT or place the converter under one of these paths:"
  echo "  ${projectdir}/output/jupyter-notebook/_vendor/bidsutils/BIDSto3col/BIDSto3col.sh"
  echo "  ${projectdir}/tools/bidsutils/BIDSto3col/BIDSto3col.sh"
  echo "  ${projectdir}/../rf1-ug/code/BIDSto3col.sh"
  exit 1
fi

mkdir -p "$baseout"

for run in 1 2 3; do
  input="${bidsdir}/sub-${sub}/func/sub-${sub}_task-${task}_run-${run}_events.tsv"
  output="${baseout}/sub-${sub}/${task}"
  mkdir -p "$output"

  if [ -e "$input" ]; then
    echo "Converting ${input}"
    bash "$converter" "$input" "${output}/run-${run}"
  else
    echo "SKIP: cannot locate ${input}"
  fi
done
