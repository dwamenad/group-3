#!/bin/bash

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"
toolsdir=/ZPOOL/data/tools

TEMPLATEFLOW_DIR=$toolsdir/templateflow
MPLCONFIGDIR_DIR=$toolsdir/mplconfigdir
export SINGULARITYENV_TEMPLATEFLOW_HOME=/opt/templateflow
export SINGULARITYENV_MPLCONFIGDIR=/opt/mplconfigdir

sub=$1

for task in "trust" "SST" "adview"; do
    for run in 1 2 3; do

        outdir=$maindir/derivatives/warpkit/sub-${sub}
        if [ ! -d $outdir ]; then
            mkdir -p $outdir
        fi

        fmapdir=$maindir/bids/sub-${sub}/fmap
        if [ ! -d $fmapdir ]; then
            mkdir -p $fmapdir
        fi

        indir=${maindir}/bids/sub-${sub}/func

        if [ ! -e $indir/sub-${sub}_task-${task}_run-${run}_echo-1_part-mag_bold.json ]; then
            echo "NO DATA: sub-${sub}_task-${task}_run-${run}_echo-1_part-mag_bold.json"
            echo "NO DATA: sub-${sub}_task-${task}_run-${run}_echo-1_part-mag_bold.json" >> $scriptdir/missingFiles-warpkit.log
            continue
        fi

        # don't re-do existing output
        if [ -e $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${task}_run-${run}_fieldmap.nii.gz ]; then
            echo "EXISTS (skipping): sub-${sub}/fmap/sub-${sub}_acq-${task}_run-${run}_fieldmap.nii.gz"
            continue
        fi

        # delete default gre fmaps (phasediff)
        if [ -e $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-bold_phasediff.nii.gz ]; then
            rm -rf $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-bold*
        fi

        singularity run --cleanenv \
        -B $indir:/base \
        -B $outdir:/out \
        $toolsdir/warpkit.sif \
        --magnitude /base/sub-${sub}_task-${task}_run-${run}_echo-1_part-mag_bold.nii.gz \
        /base/sub-${sub}_task-${task}_run-${run}_echo-2_part-mag_bold.nii.gz \
        /base/sub-${sub}_task-${task}_run-${run}_echo-3_part-mag_bold.nii.gz \
        /base/sub-${sub}_task-${task}_run-${run}_echo-4_part-mag_bold.nii.gz \
        --phase /base/sub-${sub}_task-${task}_run-${run}_echo-1_part-phase_bold.nii.gz \
        /base/sub-${sub}_task-${task}_run-${run}_echo-2_part-phase_bold.nii.gz \
        /base/sub-${sub}_task-${task}_run-${run}_echo-3_part-phase_bold.nii.gz \
        /base/sub-${sub}_task-${task}_run-${run}_echo-4_part-phase_bold.nii.gz \
        --metadata /base/sub-${sub}_task-${task}_run-${run}_echo-1_part-phase_bold.json \
        /base/sub-${sub}_task-${task}_run-${run}_echo-2_part-phase_bold.json \
        /base/sub-${sub}_task-${task}_run-${run}_echo-3_part-phase_bold.json \
        /base/sub-${sub}_task-${task}_run-${run}_echo-4_part-phase_bold.json \
        --out_prefix /out/sub-${sub}_task-${task}_run-${run}

    done
done

# Post-processing for this subject (after all jobs complete)
for task in "trust" "SST" "adview"; do
    for run in 1 2 3; do
        outdir=$maindir/derivatives/warpkit/sub-${sub}
        indir=${maindir}/bids/sub-${sub}/func
        
        # Check if the warpkit output exists before processing
        if [ -e $outdir/sub-${sub}_task-${task}_run-${run}_fieldmaps.nii ]; then
            # extract first volume as fieldmap and copy to fmap dir
            fslroi $outdir/sub-${sub}_task-${task}_run-${run}_fieldmaps.nii $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${task}_run-${run}_fieldmap 0 1
            fslroi $indir/sub-${sub}_task-${task}_run-${run}_echo-1_part-mag_bold.nii.gz $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${task}_run-${run}_magnitude 0 1

            # placeholders for json files
            cp $indir/sub-${sub}_task-${task}_run-${run}_echo-1_part-mag_bold.json $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${task}_run-${run}_magnitude.json
            cp $indir/sub-${sub}_task-${task}_run-${run}_echo-1_part-phase_bold.json $maindir/bids/sub-${sub}/fmap/sub-${sub}_acq-${task}_run-${run}_fieldmap.json

            # trash the rest
            rm -rf $outdir/sub-${sub}_task-${task}_run-${run}_displacementmaps.nii
            rm -rf $outdir/sub-${sub}_task-${task}_run-${run}_fieldmaps_native.nii
        fi
    done
done
