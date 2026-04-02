# Group 3 Neurodesk Workflow

Canonical notebook:

- `g25/output/jupyter-notebook/g25-part-a-datalad-confounds-evs-feat-mricrogl.ipynb`

Repository layout:

- `g25/` contains the lightweight project scaffold
- `g25/bids/` includes metadata and `events.tsv` files needed by the notebook
- `g25/code/` contains the OpenNeuro download, EV conversion, confounds, and FEAT helper scripts
- `g25/templates/` contains the FEAT `.fsf` templates

Neurodesk launch steps:

1. Clone the repo.
2. Open a terminal in Neurodesk.
3. Change into the notebook directory:

```bash
cd group-3/g25/output/jupyter-notebook
```

4. Start JupyterLab:

```bash
jupyter lab g25-part-a-datalad-confounds-evs-feat-mricrogl.ipynb
```

What the notebook does:

- downloads required SST files directly from OpenNeuro
- builds motion confounds for one representative FEAT run
- converts SST `events.tsv` files to FSL 3-column EV files for all approved subjects
- runs one representative first-level FEAT model
- uses `mricrogl` from Neurodesk to render the FEAT result back into the notebook

Important notes:

- Do not commit downloaded `.nii.gz` files or generated FEAT outputs. The `g25/.gitignore` file is set up to ignore them.
- The notebook is written to run from inside the vendored `g25/` folder in this repo. Use the canonical notebook path above.
