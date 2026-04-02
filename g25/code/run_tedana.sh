#!/bin/bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
scriptname=${scriptdir}/tedana.sh

for sub in `cat ${scriptdir}/sublist-new.txt`; do
	
	NCORES=15
	while [ $(pgrep -fa tedana | wc -l) -ge $NCORES ]; do
    	sleep 5s
	done

	

	bash $scriptname $sub &
	sleep 1s

done
