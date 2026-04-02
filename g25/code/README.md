# G25 Code README

 All information below described the preprocessing and analysis of data discussed in the readme of the root directory. The following information assumes the user has some familiarity with `bash`, `python`, and general coding principles. All scripts below preceeded with `run_` are accompanied by standalone scripts (e.g. `run_prepdata.sh + prepdata.sh`).vb        

```
<project-root>/
  bids/                 # BIDS-formatted dataset
  derivatives/          # fMRIPrep, MRIQC, etc.
  masks/                # ROI masks used for extraction (e.g., VS/NAcc)
  code/                 # (this folder) scripts in this README
```

 If you copy these scripts to a new environment, your first step is to update the `maindir`/`projectdir` variables and (if needed) module loads.

## Dependencies
```
Dependencies

├── Python / pip (install via `python -m pip install`)
│   └── tedana
│   └── natsort
│
├── Containers (Singularity)
│   └── heudiconv_latest.sif
│   └── fmriprep-24.1.1.sif
│   └── mriqc-24.0.2.simg
│   └── warpkit.sif
│
├── Neuroimaging Software (System-Level)
│   └── FSL
│
└── Environment Management
    └── Anaconda
```

## “What do I run, and in what order?”

A typical end-to-end workflow looks like this:

1. **Get raw data into usable BIDS**
   - `run_prepdata.sh` batch converts subject DICOMs to nifti using dcm2niix and heudiconv
   - `run_warpkit.sh` launches WarpKit through a singluarity container to create derived fieldmaps
   - `bids-addUnits.py` and `bids-sidecars.py` are necessary for getting `.json` sidecards into BIDS format after generating derived fieldmaps (fmriprep will not use the correct fieldmaps without this step) 

2. **Quality control**
   - `run_mriqc.sh` launches MRIQC for `bold` runs through a Singularity container
   - (Optional metrics export) `mriqc-exclusions.py`

3. **Preprocess with fMRIPrep**
   - `run_fmriprep.sh` launches `fmriprep.sh` across a subject list
   - `fmriprep.sh` now supports local path overrides and `DRY_RUN=1` preflight checks so you can validate the command even when the container runtime is unavailable

5. **Multi-echo denoising with tedana (multi-echo runs)**
   - `run_tedana.sh` launches tedana through python
   - Then generate FSL-ready confounds:
     - `genTedanaconfounds.py` (adds tedana rejected components → TSV)

6. **Extract FEAT-ready confounds from fMRIPrep**
   - `extract_fmriprep_confounds.py` selects a FEAT-friendly subset of nuisance regressors from `desc-confounds_timeseries.tsv`
   - Writes outputs to `derivatives/fsl/confounds_fmriprep/`

7. **Generate FSL EV files from BIDS events**
   - `convertAdView_BIDS.py`, `convertTrust_BIDS.m`, and `convertSST_BIDS.py` convert raw behavioral data into the BIDS events files
   - `run_gen3colfiles.sh` generates three column files to be used in FSL analyses
   - `gen3colfiles.sh` now writes to `derivatives/fsl/EVfiles/` in the local project and looks for `BIDSto3col.sh` in a few project-local locations
   - You can override the converter path explicitly with `BIDSTO3COL_SCRIPT=/full/path/to/BIDSto3col.sh bash code/gen3colfiles.sh 11039 SST`

7. **Run FSL FEAT statistics**
   - Level 1 (run-level): `L1stats-"task".sh` scripts
   - Level 2 (run aggregations): `L2stats-"task".sh`
   - Level 3 (group-level tests): `L3stats.sh` (submitted via `run_L3stats.sh`)

8. **Portable OpenNeuro SST runner for Neurodesk**
   - `run_openneuro_sst_pipeline.py` downloads the approved `ds007486` SST files directly from OpenNeuro, generates FSL 3-column EV files, computes motion-confound outputs from `mcflirt`, and runs first-level FEAT.
   - The script is written to be shareable across teammates:
     - it infers the project root from `code/`
     - it downloads only the requested subjects and runs
     - it looks up FSL tools on `PATH`
     - it stages FEAT in a temporary no-space directory, then copies the finished `.feat` directory back into `g25/derivatives/fsl/`
   - Typical commands:
   ```bash
   python code/run_openneuro_sst_pipeline.py --subjects sub-11039 --runs 1
   python code/run_openneuro_sst_pipeline.py --subjects sub-10562 sub-10665 sub-11028 sub-11039 sub-11450 --runs 1 2 3
   python code/run_openneuro_sst_pipeline.py --subjects sub-10562 --runs 1 --skip-feat
   ```
   - Behavior note:
     - when `--skip-feat` is set, the script downloads only the required SST `events.tsv` files and generates EV files without pulling the larger BOLD and T1 inputs
     - this is the recommended mode for the all-subject EV conversion demo in Neurodesk
   - Outputs:
     - downloaded files: `bids/sub-<id>/anat` and `bids/sub-<id>/func`
     - EV files: `derivatives/fsl/EVfiles/sub-<id>/SST/`
     - motion confounds: `derivatives/fsl/confounds_openneuro/sub-<id>/`
     - FEAT results: `derivatives/fsl/sub-<id>/*.feat`
     - run summary: `output/openneuro_sst_firstlevel_summary.tsv`
   - Requirements:
     - Python 3
     - FSL on `PATH` (`feat`, `mcflirt`, `fslnvols`)
     - outbound network access to OpenNeuro
     - enough disk for the requested subjects and runs

## Conventions used across scripts

### Subject/session lists
- `sublist-new.txt` - one column consisting of new/most recent subjects to be processed
- `sublist-all.txt` - one column consisting of all subjects to be processed
- `sublist-control.txt` - one column consisting of all subjects in control group
- `sublist-gambler.txt` - one column consisting of all subjects in gambler group


## Notes for new users of this code base

- **Hard-coded paths are common.** Search for `maindir=`, `projectdir=`, `bidsdir=`, and `/ZPOOL/data/projects/` and update to your environment.
- **Software dependencies:** scripts assume availability of **FSL**, **ANTs** (for `antsApplyTransforms`), and container runtimes (**Singularity/Apptainer**). Python scripts typically require `numpy`, `pandas`, `nibabel`, `matplotlib`, as well as `tedana` and `natsort`.
- **Run location matters:** many scripts infer the project root as the parent of `code/`. Run them from `code/` unless the script explicitly states otherwise.

## Scripts that were not covered above

- `heuristics.py`- this file is used in `prepdata.sh` during the conversion of DCMs to nifti files.
