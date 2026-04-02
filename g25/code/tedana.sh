#!/bin/bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
toolsdir=/ZPOOL/data/tools

rm -f $scriptdir/missing-tedanaInput.log

sub=$1

prepdir=$maindir/derivatives/fmriprep/sub-${sub}/func
[[ ! -d "$prepdir" ]] && exit 0

for task in trust SST adview; do
    for run in {1..3}; do

        # prepare inputs and outputs
        echo1=${prepdir}/sub-${sub}_task-${task}_run-${run}_echo-1_part-mag_desc-preproc_bold.nii.gz
        echo2=${prepdir}/sub-${sub}_task-${task}_run-${run}_echo-2_part-mag_desc-preproc_bold.nii.gz
        echo3=${prepdir}/sub-${sub}_task-${task}_run-${run}_echo-3_part-mag_desc-preproc_bold.nii.gz
        echo4=${prepdir}/sub-${sub}_task-${task}_run-${run}_echo-4_part-mag_desc-preproc_bold.nii.gz
        
        outdir=${maindir}/derivatives/tedana/sub-${sub}

        # Check for the presence of all echo files
        if [ ! -e $echo1 ] || [ ! -e $echo2 ] || [ ! -e $echo3 ] || [ ! -e $echo4 ]; then
            echo "Missing one or more files for sub-${sub}, task-${task}, run-${run}" >> $scriptdir/missing-tedanaInput.log
            echo "#Skipping sub-${sub}, task-${task}, run-${run}"
            continue
        fi

        mkdir -p $outdir
        
        # Initialize echo time variables
        echotime1=""
        echotime2=""
        echotime3=""
        echotime4=""

        # Extract echo times from the first script output
        for echo in 1 2 3 4; do
            json_file=$(find "$maindir/bids" -name "sub-${sub}_task-${task}_run-${run}_echo-${echo}_part-mag_bold.json")
            if [ -n "$json_file" ]; then
                echo_time=$(grep -o '"EchoTime": [0-9.]*' "$json_file" | cut -d' ' -f2 | tr -d '\r')
                eval "echotime${echo}=${echo_time}"
            else
                echo "missing JSON for echo-${echo} for sub-${sub}, task-${task}, run-${run}"
                echo "missing JSON for echo-${echo} for sub-${sub}, task-${task}, run-${run}" >> $scriptdir/missing-tedanaInput.log
            fi
        done

        # Run tedana in background for each run
            tedana -d $echo1 $echo2 $echo3 $echo4 \
            -e $echotime1 $echotime2 $echotime3 $echotime4 \
            --out-dir $outdir \
            --prefix sub-${sub}_task-${task}_run-${run} \
            --convention bids \
            --fittype curvefit \
            --overwrite &

        # clean up and save space
        # rm -rf ${outdir}/sub-${sub}_task-${task}_run-${run}_*.nii.gz

    done
done
