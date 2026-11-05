# SOLAR: fixed orthogonal label anchors for single-cell reference mapping

SOLAR learns a reusable expression encoder by assigning reference cell types fixed
orthogonal directions in a supervised contrastive objective. A query is mapped
with reference-fitted preprocessing and the frozen encoder. This gives an explicit
way to study how label-anchor geometry and repetition shape cell-type separation,
annotation and local biological structure.

The benchmark combines three single-cell datasets, nine held-out batches and five
model seeds. The latest 450-fit comparison includes eight matched 30D arms plus
Gaussian and learnable anchors at 128D. Its results clarify the tradeoff:

- Fixed Gaussian anchors reach query macro-F1 **0.8184**, versus **0.8111** for
  repeated orthogonal anchors at 30D. The paired difference is **+0.0072**
  (descriptive 95% batch-bootstrap interval **[+0.0023, +0.0122]**).
- Adding local preservation to repeated orthogonal anchors raises joint
  trustworthiness from **0.9124 to 0.9205** across six applicable batches, and
  pseudotime smoothness from **0.8604 to 0.8691** across three immune batches.
  Its macro-F1 is **0.8099**: local preservation and annotation are distinct goals.
- Historical comparisons retain PCA, scVI, scANVI and SCLSC. scANVI has higher
  annotation scores than SOLAR; fixed anchors provide a controlled representation
  mechanism rather than a universal annotation advantage.

All means average seeds first, batches within each dataset second, and datasets
with equal weight. [Explore the full arm results](data/campaign450/arm_summary.csv),
[paired intervals](data/campaign450/paired_batch_uncertainty.csv) and
[historical comparisons](data/heldout/tables/overall_summary.csv).

## Quick start

Reconstruct the result tables, all 450-fit summaries and selection decisions,
paired uncertainty, and historical quantitative figures from bundled score records.
Use Python **3.12** on Linux:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-replay.txt
python scripts/verify_release.py --output rebuilt
```

The command checks file integrity, rebuilds and compares 16 numerical tables at
absolute tolerance `1e-12`, verifies the historical number ledger, and writes
`rebuilt/verification.json` and `rebuilt/figures/`. Expected campaign counts are
450 complete runs, 16,830 metric rows including the derived selected-arm rows,
45 selection groups, 319 arm/endpoint summaries and 464 paired intervals.
It needs a CPU and no expression-data or model download. Allow a few minutes,
about 1 GB of memory and 100 MB for generated outputs and figures; environment
installation requires additional space.

## Method and exploration

The encoder uses reference-selected features and PCA, two hidden layers, a normalized
output and label-aware contrastive learning. Orthogonal anchors require at least
as many output dimensions as reference classes. Repeated, unique, absent, Gaussian,
learnable, reference-derived hierarchy and local-preservation controls are retained.

- [Reproduction guide](docs/reproduction.md): commands, input identities, numerical
  contracts, selection timing, dependencies and reconstruction scope.
- [Model source](src/SOLAR/api.py), [benchmark adapter](src/SOLAR/benchmark/adapter.py)
  and [campaign extensions](src/SOLAR/benchmark/reviewer_extensions.py).
- [Scientific provenance](PROVENANCE.md) and [dataset acquisition](configs/scib_datasets.yaml).

## Citation and license

Please cite *SOLAR: Fixed orthogonal label anchors for single-cell reference
mapping* using the author metadata in [CITATION.cff](CITATION.cff).
Code is under the [MIT License](LICENSE). Processed expression datasets originate
from the scIB Figshare collection, DOI `10.6084/m9.figshare.12420968.v8`, under
CC BY 4.0. The package includes score records and the historical figure inputs;
expression matrices and upstream SCLSC source are obtained separately.
