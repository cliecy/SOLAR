# Reproduce the reported analyses

The release reconstructs numerical analyses from frozen per-run scores. It covers
the final 450-fit campaign tables (the manuscript's added matched-control analyses),
the historical baseline/dimension/anchor comparisons, historical paired uncertainty
and historical quantitative Figures 2–4 and S2–S5. The matched-tradeoffs figure (Figure 3 of the revised manuscript) is rebuilt by
`scripts/make_fig3_matched_tradeoffs.py` from the campaign and follow-up summaries.
The original manuscript and supplement are separately distributed documents.

## One environment and verification command

Use the README commands with CPython 3.12. `requirements-replay.txt` pins the complete
installed replay environment. For the encoder, `requirements-model.txt` extends the
same pins with the tested CPU model dependencies, including compatible AnnData/Zarr
versions. Install it with pip, then install the package with `--no-deps` as shown in
the README. `python scripts/verify_release.py --output rebuilt`
runs every release reconstruction below and compares every CSV row, identity,
missing value and numeric field with its frozen reference, at absolute tolerance
`1e-12`, zero relative tolerance. A changed row population fails verification.
`MANIFEST.sha256` binds every release file except itself.

| Output | Entry point | Bundled inputs | Frozen comparison |
|---|---|---|---|
| 450-fit batch means, endpoint coverage, summaries, paired differences and intervals, reference-validation selection | `scripts/replay_campaign.py --output rebuilt/campaign450` | `data/campaign450/{metrics,run_ledger,validation_candidates}.csv` | Seven regenerated CSVs against `data/campaign450/` |
| Historical method, dimension and anchor comparisons, dataset and overall summaries, leave-one-dataset-out results | `scripts/build_experiment_v1_2_tables.py --input-dir data/heldout --output-dir rebuilt/historical` | `data/heldout/{runs,metrics}.csv` | All seven `data/heldout/tables/*.csv` |
| Historical paired batch uncertainty | `scripts/replay_historical_uncertainty.py --output rebuilt/historical_uncertainty` | `data/heldout/{runs,metrics}.csv` | Both `data/historical_uncertainty/*.csv` |
| Manuscript number ledgers, historical and revision | `scripts/verify_paper_numbers.py --report rebuilt/historical_claims.csv` | `paper/`, historical score records, `data/campaign450`, `data/historical_uncertainty`, `experiments/four405`, configs and source contracts | Printed precision and explicit discrepancy ledger |
| Matched-tradeoffs figure (revised manuscript Figure 3) | `scripts/make_fig3_matched_tradeoffs.py --output-dir rebuilt/figures` | `experiments/four405/evidence/new405/arm_summary.csv`, `data/campaign450/arm_summary.csv` | Plotted values are the ledger-checked Table 4, S11 and S14 means |
| 405-record follow-up and preserved controls | `experiments/four405/replay.py` and its `scripts/replay_old450.py` and `scripts/verify_release.py`, invoked by the top-level verifier | `experiments/four405/evidence/` | Batch means, summaries, 222 complete-panel intervals, 420 endpoint-specific intervals and seven full-table comparisons |
| Historical quantitative figures | `scripts/build_paper_figures.py --output-dir rebuilt/figures` | Historical score records and Villani predictions | Numerical values checked by the historical ledger; PDF/PNG rendering is exercised, not compared pixelwise |

The four historical ledgers contain 5,207 entries whose locations follow the
original submission's layout. `paper/claims_revision.csv` adds 3,375 entries from
the revised manuscript: Tables 4 and 5, Tables S10–S16 and the revised prose,
evaluated against `data/campaign450`, `data/historical_uncertainty` and
`experiments/four405`. All 8,582 entries match and `paper/known_discrepancies.csv`
is empty. `scripts/build_revision_ledger.py` records how the revision ledger was
derived from external LaTeX sources. Table rows are parsed from their labeled
bodies; prose templates are bound to numeric tokens within the named section,
with token boundaries checked. A changed per-section/table claim count fails
before writing the ledger. Source comparison is optional and requires the author's
external manuscript files; no manuscript is distributed with the code.

## Populations, controls and uncertainty

The campaign contains 450 fitted models: eight arms at 30D and Gaussian/learnable
arms at 128D, each across nine batches and seeds 40–44. Dataset/batch identities are
explicit in the replay module. A further 45 selected-arm records reuse existing
fits; they are not additional trainings. The input contains 34 metric/population
panels per fit, with unavailable endpoints retained explicitly. Only complete sets
of five computed seed values form a batch mean. The 319 available arm/endpoint
summaries retain their actual dataset, batch and fit coverage.

Selection maximizes saved reference-validation macro-F1 across all eight matched
30D arms for each batch/seed, breaking ties in protocol arm order. The reference
partition hash must agree across candidates. Selection was added after initial
query scores had been inspected. Although query values do not enter the selector,
this remains development evidence on a previously exposed benchmark. All arms and
negative selected-method results remain in the release. Selection is replayed from
saved validation scores; validation embeddings and neighbor predictions are not
recomputed here. Known-reference acceptance calibration does not validate unknown
cell-type detection.

Paired uncertainty uses exact ordered within-dataset batch resampling, with seeds
averaged first and datasets weighted equally. Intervals are descriptive,
unadjusted and conditional on these datasets; references overlap across held-out
batches. The campaign has 464 contrast/endpoint intervals. A one-batch endpoint
has a degenerate interval, explicitly identified in its record. Historical
uncertainty adds 22 contrasts and 153 batch differences, including scANVI and
SCLSC. Missing outcomes are never replaced by zero.

## Dependencies and implementation

`replay_campaign.py` retains the original `paired_interval` function and batch
aggregation computation from the completed campaign, while replacing raw artifact
loading with bundled score records. `replay_historical_uncertainty.py` preserves
the historical resampling computation and uses relative inputs and output flags.
These modules import only the replay environment. They do not import training,
GPU scheduling, external scoring workers or private workspace files.

`configs/historical_source_contracts.json` contains exact source excerpts used by
the historical hyperparameter verifier. It replaces otherwise unused large
execution pipelines; these excerpts are static provenance, not executable scoring
implementations. Scientific config fields remain; machine launch settings are
omitted. Historical score records retain portable scientific and artifact identifiers.

The original SOLAR API and tested model computations remain available. The
hierarchy/local objective is extracted into `SOLAR.benchmark.reviewer_extensions`;
it takes explicit output and component-log arguments and modifies the process's
training hook. Install once per fresh process. The hierarchy uses internal-training
class centers with Gram matrix `0.5 I + 0.5 C C^T`; local preservation uses a
within-label neighbor KL penalty weighted `0.1`. The original campaign bound
embedding width explicitly because variant settings can override `TrainConfig`.
These source implementations are provided for inspection and reuse. The release
verification does not fit any model or rerun official scIB scoring.

## Data and expensive reconstruction

Processed input files, immutable checksums and source URLs are recorded in
`configs/scib_datasets.yaml` (scIB Figshare record 12420968, version 8, CC BY 4.0).
The existing repository's `v1.0` release provides historical result and model
attachments, including splits, genes, embeddings and checkpoints. See
https://github.com/cliecy/SOLAR/releases/tag/v1.0.
The historical upstream SCLSC revision is
`yaozhong/SCLSC@2e827dfebb793dffb548fd297e5c4e70fa40692f` and is not redistributed.

Full campaign fitting requires the checksum-bound source expression data, frozen
splits/features, GPU training environment and original run artifacts; fresh
embedding scoring additionally needs the legacy scIB backend and R dependencies.
These costly stages were not executed during packaging. The compact release does
not ship the 450 checkpoints/embeddings or promise full training reconstruction
from the quick start. All original experiment, raw score, source and manuscript
records are preserved outside this isolated release branch. No new experiments,
training or changes to the scientific population were performed.
