#!/bin/bash

# ensure paths are correct irrespective from where user runs the script
scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
maindir="$(dirname "$scriptdir")"

# setting inputs and common variables
sub=$1
type=$2
TASK=$3 # edit if necessary
sm=5 # edit if necessary
MAINOUTPUT=${maindir}/derivatives/fsl/sub-${sub}
model=1  # output model always stays as 1
NCOPES=28

# find valid runs
valid_runs=()

for run in 1 2 3; do
    featdir="${MAINOUTPUT}/L1_task-trust_model-1_type-${type}_run-${run}_sm-${sm}.feat"
    [ -e "${featdir}/stats/cope1.nii.gz" ] && valid_runs+=("${featdir}")
done

nruns=${#valid_runs[@]}

# exit if no runs
[ "$nruns" -eq 0 ] && {
    echo "Error: No valid runs found for sub-${sub}, type-${type}"
    exit 1
}

echo "Detected $nruns valid runs for sub-${sub}, type-${type}"

# assign inputs sequentially
INPUT1="${valid_runs[0]}"
INPUT2="${valid_runs[1]}"
INPUT3="${valid_runs[2]}"


# ppi has more contrasts than act (phys), so need a different L2 template
if [ "${type}" == "act" ]; then
    ITEMPLATE=${maindir}/templates/L2_task-trust_model-${model}_nruns-${nruns}_type-act.fsf
    NCOPES=${NCOPES}
else
    ITEMPLATE=${maindir}/templates/L2_task-trust_model-${model}_nruns-${nruns}_type-ppi.fsf
    let NCOPES=${NCOPES}+1 # add 1 since we tend to only have one extra contrast for PPI
fi

# check for existing output and re-do if missing/incomplete
OUTPUT=${MAINOUTPUT}/L2_task-trust_model-${model}_type-${type}_sm-${sm}

if [ -e ${OUTPUT}.gfeat/cope${NCOPES}.feat/cluster_mask_zstat1.nii.gz ]; then # check last (act) or penultimate (ppi) cope
    echo "skipping existing output"
else
    echo "re-doing: ${OUTPUT}" >> re-runL2.log
    rm -rf ${OUTPUT}.gfeat

    # set output template and run template-specific analyses
    OTEMPLATE=${MAINOUTPUT}/L2_task-trust_model-${model}_type-${type}.fsf
    
    # Build sed command based on number of runs
    if [ $nruns -eq 2 ]; then
        sed -e 's@OUTPUT@'$OUTPUT'@g' \
        -e 's@INPUT1@'$INPUT1'@g' \
        -e 's@INPUT2@'$INPUT2'@g' \
        <$ITEMPLATE> $OTEMPLATE
    else  # nruns == 3
        sed -e 's@OUTPUT@'$OUTPUT'@g' \
        -e 's@INPUT1@'$INPUT1'@g' \
        -e 's@INPUT2@'$INPUT2'@g' \
        -e 's@INPUT3@'$INPUT3'@g' \
        <$ITEMPLATE> $OTEMPLATE
    fi
    
    feat $OTEMPLATE

    # delete unused files
    for cope in `seq ${NCOPES}`; do
        rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/res4d.nii.gz
        rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/corrections.nii.gz
        rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/stats/threshac1.nii.gz
        #rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/filtered_func_data.nii.gz
        rm -rf ${OUTPUT}.gfeat/cope${cope}.feat/var_filtered_func_data.nii.gz
    done
fi
