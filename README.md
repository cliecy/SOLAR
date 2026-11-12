# SOLAR: fixed orthogonal label anchors for single-cell reference mapping

SOLAR learns an expression encoder that maps labeled reference cells and unseen
query cells into a shared, normalized embedding. Fixed orthogonal cell-type anchors
make label geometry explicit in a supervised contrastive objective. Use it to build
reference mappings and study how annotation, cell-type separation and local
biological structure respond to anchor geometry and repetition.

The Python API accepts reference and query `AnnData` objects and returns their
embeddings, the reference-fitted PCA transform, a reusable encoder and run metadata.
Query labels are excluded from the model-facing inputs. The benchmark implementation
also provides matched anchor and objective controls.

[Python usage](#use-the-encoder) · [Scientific results](docs/four405-results.md) ·
[Reproducibility artifact](#reproducibility-artifact) · [Technical guide](docs/reproduction.md)

## Method and findings

The encoder applies two hidden layers to reference-fitted PCA features and learns
unit-normalized cell representations with label-aware contrastive learning. Each
reference class has a fixed orthogonal direction; repeated anchors enter the
contrastive pool once per labeled cell. The embedding width must be at least the
number of reference classes. Query mapping uses the frozen preprocessing and
encoder without updating model parameters.

The held-out benchmark spans three datasets, nine batches and five model seeds.
It supports a concrete representation tradeoff:

- With common 30-dimensional outputs, SOLAR reaches query macro-F1 **0.811**,
  compared with **0.774** for matched PCA and **0.838** for frozen-reference
  scANVI (Table 2). After aligning SCLSC inputs and checkpoint selection, SOLAR
  retains gains of **0.015** in query trustworthiness and **0.014** in joint
  immune pseudotime smoothness (Table S16).
- At 30 dimensions, local preservation raises joint trustworthiness from **0.9124
  to 0.9205** across six applicable batches and pseudotime smoothness from **0.8604
  to 0.8691** across three immune batches, relative to repeated orthogonal anchors.
- With unique anchors, local preservation raises joint trustworthiness from
  **0.92691 to 0.93172**; query macro-F1 changes from **0.81131 to 0.80999**.
  Structure preservation and annotation are separate objectives.
- At 128 dimensions, repeated orthogonal anchors reach query macro-F1 **0.81240**,
  compared with Gaussian **0.81127** and learnable anchors **0.80772**. Both paired
  annotation intervals include zero.

Means average seeds, batches within each dataset, then datasets equally. The
[scientific results guide](docs/four405-results.md) includes all controls, SCLSC
comparisons, unknown-type rejection, endpoint coverage and descriptive uncertainty.

## Installation

Use Python 3.12 on Linux. Clone the repository, then install:

```bash
git clone https://github.com/cliecy/SOLAR.git
cd SOLAR
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-model.txt
python -m pip install --no-deps .
python examples/smoke_test.py
```

The last command runs a small synthetic CPU demonstration with three training epochs.
It prints reference and query embedding shapes `(240, 8)` and `(80, 8)` and
`SMOKE TEST PASSED`. It checks installation and mapping; the reported scientific
results are reconstructed separately below. PyTorch and AnnData are needed for the
encoder; saved-score reconstruction uses only `requirements-replay.txt`.

## Use the encoder

Provide processed expression matrices with identical genes in the same order,
unique cell identifiers and reference cell types in `reference.obs['cell_type']`.
Choose normalization and features on the reference and apply the same transformation
to the query; `run_inductive` fits PCA on the reference only.

```python
import anndata as ad
from SOLAR.benchmark import PreprocessConfig, TrainConfig, run_inductive

reference = ad.read_h5ad('reference.h5ad')
query = ad.read_h5ad('query.h5ad')
result = run_inductive(
    reference=reference,
    query=query,
    variant='solar_orthogonal',
    labels_key='cell_type',
    preprocess=PreprocessConfig(n_components=40, source='X'),
    train=TrainConfig(embedding_dim=128),
    device='cpu',
)
query.obsm['X_solar'] = result.query_embedding
result.save('mapping', save_model=True)
```

The output contains `embedding.npz`, `pca_preprocessor.npz`, `anchors.npy`,
`run_info.json` and the model checkpoint. The [runnable synthetic example](examples/smoke_test.py)
requires no external data. [SOLARModel](src/SOLAR/api.py) exposes lower-level setup,
fit, transform, save and load methods; the [mapping adapter](src/SOLAR/benchmark/adapter.py)
handles reference/query preprocessing and metadata.

## Reproducibility artifact

The repository bundles saved score records and executable reconstruction for the
450-fit benchmark and 405-record follow-up. Install the replay environment and run:

```bash
python -m pip install -r requirements-replay.txt
python scripts/verify_release.py --output rebuilt
```

This CPU command reconstructs the scientific tables, selection decisions, paired
intervals, paper quantitative figures and an additional matched-tradeoffs overview.
It checks all **8,582** ledger entries and writes `rebuilt/verification.json`,
`rebuilt/four405/` and `rebuilt/figures/`. It needs no expression or checkpoint
download. Allow several minutes and about 1 GB RAM, plus space for the environment.

The [technical guide](docs/reproduction.md) specifies exact populations, input
identities, tolerances, figure mappings, reference-selection timing and dependencies
for model fitting and scoring. [Historical v1.0 assets](https://github.com/cliecy/SOLAR/releases/tag/v1.0)
are a frozen earlier release; this branch contains the current reconstruction source.

## Citation and license

Please cite *SOLAR: Fixed orthogonal label anchors for single-cell reference
mapping* using [CITATION.cff](CITATION.cff). Code is under the [MIT License](LICENSE).
Processed expression datasets originate from the scIB Figshare collection,
DOI [10.6084/m9.figshare.12420968.v8](https://doi.org/10.6084/m9.figshare.12420968.v8),
under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Score records and
historical figure inputs are bundled; expression matrices and upstream SCLSC
source are acquired separately. See [provenance](PROVENANCE.md) and
[dataset identities](configs/scib_datasets.yaml).
