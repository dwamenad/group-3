#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Set number of parallel processes
NCORES=40

# these define the subject number (sub) and session id (ses)
#for sub in 10418 10462 10541 10617 10649 10691 10898; do
for sub in `cat ${scriptdir}/sublist-new.txt`; do
#for sub in 10106; do

    # Wait if we've reached the maximum number of parallel processes
    while [ $(ps -ef | grep -v grep | grep "prepdata.sh" | wc -l) -ge $NCORES ]; do
        sleep 5s
    done

    # Run the script in the background
    script=${scriptdir}/prepdata.sh
    bash $script $sub &
    sleep 1s

done

# Wait for all background jobs to complete
wait

rm -rf ../bids/sub-*/func/*part-*_events.*

echo "All subjects processed"
