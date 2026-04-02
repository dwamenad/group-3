#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# the "type" variable below is setting a path inside the main script
for type in "act"; do
	for sub in `cat ${scriptdir}/sublist-test.txt`; do
	for task in "trust"; do

	# Manages the number of jobs and cores
  	SCRIPTNAME=${maindir}/code/L2stats-${task}.sh
  	NCORES=20

  	while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
    		sleep 1s
  	done

  	bash $SCRIPTNAME $sub $type $task &
  	sleep 1s

	done
done
done
