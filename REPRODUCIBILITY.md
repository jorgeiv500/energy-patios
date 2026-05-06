# Reproducibility Package

This repository is intended to support the Energy manuscript:

> Rooftop-aware optimization of electric bus depot charging, photovoltaic generation, and battery storage under grid-capacity constraints: Evidence from Bogota's large-scale e-bus system

## Repository Roles

Use GitHub as the working repository and Zenodo or Mendeley Data as the citable archived snapshot.

- GitHub: live code, scripts, issue tracking, README, release notes, and reviewer navigation.
- Zenodo or Mendeley Data: immutable versioned archive with DOI for citation in the manuscript.

## Included In The Public Repository

- `src/`: reusable Python package code.
- `scripts/`: data download, preprocessing, and experiment scripts.
- `docs/`: data inventory, experimental design, route-depot assignment method, and solver protocol.
- `data/processed/*.csv` and `data/processed/*.geojson`: lightweight derived inputs needed to reproduce the reported experiment, where redistribution is permitted.
- `results/tables/`: reference CSV outputs used to verify that the experiment was reproduced.
- `requirements.txt` and `pyproject.toml`: Python dependency and package metadata.

## Not Redistributed

The repository should not redistribute large or third-party raw files unless their license explicitly permits it. The following are intentionally excluded by `.gitignore`:

- `data/raw/`
- large IDECA/Catastro geospatial packages;
- downloaded PDFs and HTML pages from third-party providers;
- manuscript source/PDFs, editorial figures, response material, and submission files;
- metadata from literature searches, chat summaries, or editorial triage;
- temporary LaTeX build byproducts.

Raw data sources are listed in `docs/data_inventory.md`. Users should download those files from the original providers when licenses or size restrictions apply.

## Reproduction Commands

Install dependencies:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

Audit the included reproducibility inputs and reference outputs:

```bash
python scripts/check_data.py
```

Optional: rebuild processed experiment inputs after downloading the original raw sources:

```bash
python scripts/download_data.py
python scripts/check_data.py --raw
python scripts/build_experiment_inputs.py
```

Run the optimized scenario matrix:

```bash
python scripts/run_full_experiment.py --solver appsi_highs --capacity-mode optimized
```

Verify outputs against the reference CSV files in `results/tables/`.

## Release Procedure For GitHub + DOI

1. Confirm that the GitHub URL in `CITATION.cff`, `.zenodo.json`, and `README.md` points to the final repository.
2. Confirm the code license and data redistribution policy.
3. Commit the release-ready repository.
4. Create a GitHub release named `v1.0.0-energy-submission`.
5. Archive the GitHub release with Zenodo, or upload the release archive to Mendeley Data.
6. Copy the DOI minted by Zenodo or Mendeley Data.
7. Add the final DOI to `CITATION.cff` and to the manuscript data-availability statement kept outside this repository.

## Recommended Manuscript Data Availability Statement

Before manuscript submission, use:

- GitHub repository URL: `https://github.com/jorgeiv500/energy-patios`
- Zenodo version DOI: `https://doi.org/10.5281/zenodo.20045572`
- Zenodo concept DOI: `https://doi.org/10.5281/zenodo.20045571`

The DOI should identify the exact release used for the submitted manuscript, not the moving default branch.
