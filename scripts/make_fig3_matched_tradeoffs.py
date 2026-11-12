#!/usr/bin/env python3
"""Rebuild an additional matched-tradeoffs overview from Table 4 means.

    python scripts/make_fig3_matched_tradeoffs.py [--output-dir rebuilt/figures]

Inputs default to experiments/four405/evidence/new405/arm_summary.csv and
data/campaign450/arm_summary.csv. Three panels of dataset-equal means for the 30-dimensional configurations:
query macro-F1 (nine batches), joint trustworthiness (six immune/lung batches)
and joint pseudotime smoothness (three immune batches). Rows follow Table 4 of
the manuscript; the three rows below the separator are the configurations
added during revision. Validation-selected is read from the 450-fit summary,
all other arms from the 405-record follow-up summary (identical for shared arms).
"""
from __future__ import annotations
import argparse
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

ROWS = [  # (label, arm key, colour, marker)
    ("Orthogonal repeated", "repeated", "#222222", "o"),
    ("Orthogonal unique", "unique", "#6e6e6e", "o"),
    ("No anchors", "none", "#b0b0b0", "o"),
    ("Gaussian", "gaussian", "#0072B2", "o"),
    ("Learnable", "learnable", "#56B4E9", "o"),
    ("Reference geometry", "hierarchy", "#D55E00", "o"),
    ("Local preservation", "local", "#009E73", "o"),
    ("Combined", "hierarchy_local", "#CC79A7", "o"),
    ("Validation-selected", "validation_selected", "#B8860B", "o"),
    ("Orthogonal unique + local preservation", "unique_local", "#009E73", "s"),
    ("Local preservation, weight 0.03", "local003", "#7FCDB1", "v"),
    ("Local preservation, weight 0.3", "local03", "#005C43", "^"),
]
SEPARATOR_AFTER = 9  # rows above are the original matched set
PANELS = [
    ("Query annotation\n3 datasets / 9 batches", "macro_f1", "query"),
    ("Joint trustworthiness\n2 datasets / 6 batches", "trustworthiness", "joint"),
    ("Joint pseudotime smoothness\n1 dataset / 3 batches", "pseudotime_smoothness", "joint"),
]


def value(frame: pd.DataFrame, arm: str, metric: str, population: str) -> float:
    q = frame[(frame.arm == arm) & (frame.dimension == 30) & (frame.metric == metric) & (frame.population == population)]
    if "omission" in q.columns:
        q = q[q.omission.isna()]
    if len(q) != 1:
        raise SystemExit(f"expected one row for {arm}/{metric}/{population}, found {len(q)}")
    return float(q.value.iloc[0])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--new405", type=Path, default=ROOT / "experiments" / "four405" / "evidence" / "new405" / "arm_summary.csv")
    ap.add_argument("--campaign450", type=Path, default=ROOT / "data" / "campaign450" / "arm_summary.csv")
    ap.add_argument("--output-dir", type=Path, default=ROOT / "rebuilt" / "figures")
    a = ap.parse_args()
    new, old = pd.read_csv(a.new405), pd.read_csv(a.campaign450)
    records = []
    for label, arm, colour, marker in ROWS:
        src = old if arm == "validation_selected" else new
        for title, metric, population in PANELS:
            records.append({"configuration": label, "arm": arm, "metric": metric, "population": population,
                            "value": value(src, arm, metric, population)})
    data = pd.DataFrame(records)

    plt.rcParams.update({"font.size": 10, "axes.titlesize": 10.5, "axes.labelsize": 10})
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.9), sharey=True)
    y = list(range(len(ROWS)))
    for ax, (title, metric, population) in zip(axes, PANELS):
        sub = data[(data.metric == metric) & (data.population == population)].set_index("arm")
        ref = sub.loc["repeated", "value"]
        ax.axvline(ref, color="#9a9a9a", ls=(0, (1.5, 2.5)), lw=1.0, zorder=0)
        ax.axhline(SEPARATOR_AFTER - 0.5, color="#c8c8c8", lw=0.8, zorder=0)
        for yi, (label, arm, colour, marker) in zip(y, ROWS):
            ax.scatter(sub.loc[arm, "value"], yi, s=58, color=colour, marker=marker,
                       edgecolor="white", linewidth=0.6, zorder=3)
        lo, hi = sub.value.min(), sub.value.max()
        pad = 0.08 * (hi - lo)
        ax.set_xlim(lo - pad, hi + pad)
        ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, steps=[1, 2, 4, 5, 10]))
        ax.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.3f"))
        ax.grid(axis="x", color="#e6e6e6", lw=0.8, zorder=0)
        ax.set_title(title)
        ax.set_xlabel("Dataset-equal mean")
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_yticks(y, [r[0] for r in ROWS])
    axes[0].invert_yaxis()
    fig.tight_layout(w_pad=1.6)
    a.output_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.output_dir / "matched_tradeoffs_overview.pdf", bbox_inches="tight")
    fig.savefig(a.output_dir / "matched_tradeoffs_overview.png", dpi=200, bbox_inches="tight")
    data.to_csv(a.output_dir / "matched_tradeoffs_overview.csv", index=False)
    print(data.pivot(index="configuration", columns="metric", values="value").loc[[r[0] for r in ROWS]].round(4).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
