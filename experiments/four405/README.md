# SOLAR: controlled label geometry and reference mapping

SOLAR uses fixed orthogonal label anchors to study how label geometry changes single-cell reference mapping. This package reconstructs four follow-up comparisons from 405 completed records and preserves the original 450-run benchmark. It retains matched128 geometry controls, best-checkpoint SCLSC with gene/PCA40 inputs, unique-anchor local regularization and whole-type-out rejection.

The controls separate label separation, annotation and local structure: matched128 does not establish an annotation advantage; best-checkpoint SCLSC has stronger label silhouette; local regularization yields larger joint than query structure gains; unknown rejection depends strongly on omitted biology and confidence score.

## Quick start

Python 3.12 and a CPU are sufficient. Use this directory inside the SOLAR
repository so the preserved controls share the top-level campaign implementation:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python replay.py --root .
.venv/bin/python scripts/replay_old450.py --inputs evidence/old450 --output replayed-old450
.venv/bin/python scripts/verify_release.py
```

The first command writes `replayed/` and validates all405 records, all arm summaries and the original222 paired intervals at absolute tolerance1e-12. It also reconstructs420 endpoint-specific contrasts, including local metrics with six eligible batches and B-cell unknown metrics with two. The second reconstructs the historical450 benchmark and validation-only selection. The third compares complete reconstructed tables, identities, missingness and numerical cells against the included references.

Explore the compact [results tables](evidence/new405/arm_summary.csv), [unknown rejection table](evidence/unknown90/summary.csv), [protocol](docs/protocol.md) and [reproduction details](docs/reproduction.md). Canonical software repository: https://github.com/cliecy/SOLAR .

## Citation and license

See `CITATION.cff` and `LICENSE`. This companion release contains aggregate scientific measurements without per-cell expression or identifiers. It supports deterministic saved-score analysis; raw expression, model checkpoints, model inference and training require the separate research assets and are not invoked by these commands.
