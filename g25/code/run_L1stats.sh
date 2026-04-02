#!/bin/bash

# Ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
basedir="$(dirname "$scriptdir")"

for ppi in 0; do
	for sub in `cat ${basedir}/code/sublist-new.txt`; do
		for run in 1 2 3; do
		for task in "SST" "trust"; do

			# Manages the number of jobs and cores
			SCRIPTNAME=${basedir}/code/L1stats-${task}.sh
			NCORES=20
			while [ $(ps -ef | grep -v grep | grep $SCRIPTNAME | wc -l) -ge $NCORES ]; do
				sleep 5s
			done

		bash $SCRIPTNAME $sub $run $ppi &
		sleep 1s

		done	  	
	done
done
done
