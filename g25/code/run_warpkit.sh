#!/bin/bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
scriptname=${scriptdir}/warpkit.sh

# Set number of parallel processes
NCORES=60

for sub in `cat ${scriptdir}/sublist-new.txt`; do

    # Wait if we've reached the maximum number of parallel processes
    while [ $(ps -ef | grep -v grep | grep "warpkit.sh" | wc -l) -ge $NCORES ]; do
        sleep 5s
    done

    # Run the script in the background
    bash $scriptname $sub &
    echo "running $scriptname for $sub"
    sleep 1s

done

# Wait for all background jobs to complete
wait

echo "All subjects processed"
