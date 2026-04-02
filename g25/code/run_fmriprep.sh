#!/usr/bin/env bash

set -euo pipefail

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
projectdir="$(dirname "$scriptdir")"
scriptname="${scriptdir}/fmriprep.sh"

subjects=()

if [ "$#" -gt 0 ]; then
  subjects=("$@")
elif [ -n "${SUBJECT_FILE:-}" ] && [ -f "${SUBJECT_FILE}" ]; then
  while IFS= read -r sub; do
    [ -n "$sub" ] || continue
    subjects+=("$sub")
  done < "${SUBJECT_FILE}"
elif [ -f "${scriptdir}/sublist-new.txt" ]; then
  while IFS= read -r sub; do
    [ -n "$sub" ] || continue
    subjects+=("$sub")
  done < "${scriptdir}/sublist-new.txt"
else
  while IFS= read -r subdir; do
    subjects+=("${subdir##*/sub-}")
  done < <(find "${projectdir}/bids" -maxdepth 1 -type d -name 'sub-*' | sort)
fi

if [ "${#subjects[@]}" -eq 0 ]; then
  echo "ERROR: No subjects found for fMRIPrep."
  exit 1
fi

for sub in "${subjects[@]}"; do
  bash "$scriptname" "$sub"
done
