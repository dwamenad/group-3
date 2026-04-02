#!/usr/bin/env bash

set -euo pipefail

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

for subdir in "${basedir}"/bids/sub-*; do
  [ -d "$subdir" ] || continue
  sub="${subdir##*/sub-}"
  for task in trust SST adview; do
    bash "${scriptdir}/gen3colfiles.sh" "$sub" "$task"
  done
done
