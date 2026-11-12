#!/usr/bin/env python3
"""Build ``paper/claims_revision.csv`` from the revised manuscript sources.

    python scripts/build_revision_ledger.py --main-tex bmc_main.tex --si-tex additional_file.tex \
        --si-tables-tex reviewer_campaign_tables.tex --si-paired-tex paired_batch_table.tex

The LaTeX sources are not distributed with this repository; this script records
how the revision ledger was derived from them. Every row pairs a printed string,
copied from the LaTeX source, with the frozen record that must reproduce it
(``kind``/``spec`` are evaluated by ``verify_paper_numbers.py``). Table rows are
parsed from the table bodies; prose templates are bound to complete numeric tokens
within their declared section. Missing tokens, ambiguous sections and changed claim
populations fail before writing. Full manuscript files are external optional inputs.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Printed configuration names -> frozen arm keys.
ARMS = {
    "Orthogonal repeated": "repeated", "Orthogonal unique": "unique", "No anchors": "none",
    "Gaussian": "gaussian", "Learnable": "learnable", "Reference geometry": "hierarchy",
    "Local preservation": "local", "Combined": "hierarchy_local", "Validation-selected": "validation_selected",
    "Orthogonal unique + local preservation": "unique_local",
    "Local preservation, weight 0.03": "local003", "Local preservation, weight 0.3": "local03",
    "Orthogonal unique + Local preservation (0.1)": "unique_local",
    "Orthogonal repeated + Local preservation (0.03)": "local003",
    "Orthogonal repeated + Local preservation (0.1)": "local",
    "Orthogonal repeated + Local preservation (0.3)": "local03",
    "Unique + Local (0.1)": "unique_local", "Repeated + Local (0.1)": "local",
    "Repeated + Local (0.03)": "local003", "Repeated + Local (0.3)": "local03",
}
# Arms that exist only in the follow-up records (everything else is read from the 450-fit campaign).
FOLLOWUP_ONLY = {"unique_local", "local003", "local03", "sclsc_best_genes", "sclsc_best_pca40"}
FOLLOWUP_128 = {"repeated", "unique"}
METRICS = {
    "ARI": "ARI_cluster/label", "Label ASW": "ASW_label", "Batch ASW": "ASW_label/batch",
    "NMI": "NMI_cluster/label", "PCR batch correction": "PCR_batch", "Balanced accuracy": "balanced_accuracy",
    "cLISI": "cLISI", "Cell-cycle conservation": "cell_cycle_conservation", "Graph connectivity": "graph_conn",
    "iLISI": "iLISI", "Isolated-label F1": "isolated_label_F1", "Isolated-label silhouette": "isolated_label_silhouette",
    "kBET": "kBET", "Macro-F1": "macro_f1", "Pseudotime smoothness": "pseudotime_smoothness",
    "Trajectory conservation": "trajectory", "Trustworthiness": "trustworthiness",
    "Raw donor silhouette": "within_label_silhouette__donor",
    "Raw patient-group silhouette": "within_label_silhouette__patientGroup",
    "Raw sample-ID silhouette": "within_label_silhouette__sample_ID",
    "Raw study silhouette": "within_label_silhouette__study",
}
POPULATIONS = {"R": "reference", "Q": "query", "J": "joint"}
HISTORICAL_CONTRASTS = {
    "SOLAR 30D minus PCA": "SOLAR30 - PCA", "SOLAR 30D minus scANVI": "SOLAR30 - scANVI",
    "SOLAR 30D minus SCLSC": "SOLAR30 - SCLSC", "Repeated minus no anchors": "Repeated128 - none",
    "Repeated minus unique": "Repeated128 - unique",
}
HISTORICAL_METRICS = {"ASW_label": "labelASW"}  # key used by the historical uncertainty records
UNKNOWN_TYPES = {"B-cell family": "Bcells", "CD16+ monocytes": "CD16"}
UNKNOWN_METHODS = {"SOLAR": "solar", "scANVI": "scanvi", "Matched PCA": "pca"}
UNKNOWN_SCORES = {"distance": "negative_weighted15nn_distance", "anchor cosine": "max_training_anchor_cosine",
                  "probability": "max_class_probability", "class probability": "max_class_probability"}
UNKNOWN_FIELDS = ("auroc", "unknown_recall", "known_query_macro_f1", "known_false_rejection")
SCLSC_ROWS = {
    "SOLAR, PCA40 input, best checkpoint": ("arm", "four405", "repeated"),
    "SCLSC, official stopping rule, gene input": ("summary", None, "sclsc_refonly"),
    "SCLSC, best checkpoint, gene input": ("arm", "four405", "sclsc_best_genes"),
    "SCLSC, best checkpoint, PCA40 input": ("arm", "four405", "sclsc_best_pca40"),
}


def clean(cell: str) -> str:
    cell = cell.strip().replace("$", "")
    cell = re.sub(r"\\textbf\{([^}]*)\}", r"\1", cell)
    return cell.strip()


def endpoint(text: str) -> tuple[str, str]:
    text = re.sub(r"\^\{\\dagger\}", "", text.replace("$", "")).strip()
    name, population = [part.strip() for part in text.split(" / ")]
    return METRICS[name], POPULATIONS[population]


def interval_cell(text: str) -> tuple[str, str, str]:
    match = re.match(r"^(.+?) \[(.+?), (.+?)\]$", clean(text))
    if not match:
        raise ValueError(f"not an interval cell: {text!r}")
    return tuple(part.strip() for part in match.groups())


def body(tex: str, label: str) -> list[str]:
    """Lines of the table body that carries the given label."""
    start = tex.index("\\label{%s}" % label)
    end = min(i for i in (tex.find("\\end{longtable}", start), tex.find("\\end{tabular*}", start)) if i > 0)
    return tex[start:end].splitlines()


def arm_source(arm: str, dim: int) -> str:
    if arm in FOLLOWUP_ONLY or (dim == 128 and arm in FOLLOWUP_128):
        return "four405"
    return "campaign450"


class Ledger:
    def __init__(self):
        self.rows = []

    def add(self, doc, location, printed, kind, spec):
        printed = clean(str(printed))
        self.rows.append({"doc": doc, "location": location, "printed": printed, "kind": kind,
                          "spec": json.dumps(spec, sort_keys=True)})

    def arm(self, doc, location, printed, arm, dim, metric, population, stat="mean", source=None):
        self.add(doc, location, printed, "arm", {"source": source or arm_source(arm, dim), "arm": arm, "dim": dim,
                                                  "metric": metric, "population": population, "stat": stat})

    def interval(self, doc, location, printed, source, left, right, dim, metric, population, stat, negate=False):
        spec = {"source": source, "left": left, "right": right, "dim": dim, "metric": metric,
                "population": population, "stat": stat}
        if negate:
            spec["negate"] = True
        self.add(doc, location, printed, "interval", spec)

    def interval_cells(self, doc, location, cell, source, left, right, dim, metric, population, negate=False):
        for stat, printed in zip(("delta", "lower", "upper"), interval_cell(cell)):
            self.interval(doc, location, printed, source, left, right, dim, metric, population, stat, negate)

    def unknown(self, doc, location, printed, arm, omission, confidence, stat, percentile=5):
        self.add(doc, location, printed, "unknown", {"arm": arm, "omission": omission, "confidence": confidence,
                                                      "percentile": percentile, "stat": stat})

    def unknown_interval(self, doc, location, printed, left, right, omission, metric, stat, percentile=5):
        self.add(doc, location, printed, "unknown_interval", {"left": left, "right": right, "omission": omission,
                                                               "percentile": percentile, "metric": metric, "stat": stat})


def table4(ledger: Ledger, main: str) -> None:
    for line in body(main, "tab:reviewer-main"):
        match = re.match(r"^(?P<name>[^&\\]+?) & (?P<dim>30|128) & (?P<value>[^&]+?) \\\\", line)
        if match:
            dim = int(match["dim"])
            ledger.arm("main", "Table 4", match["value"], ARMS[match["name"].strip()], dim, "macro_f1", "query")


def table5(ledger: Ledger, main: str) -> None:
    current = None
    for line in body(main, "tab:ood"):
        match = re.match(r"^(?P<type>[^&]*?) ?& (?P<method>SOLAR|scANVI|Matched PCA), (?P<score>[a-z ]+?) & "
                         r"(?P<a>[^&]+?) & (?P<r>[^&]+?) & (?P<f>[^&]+?) & (?P<frr>[^&]+?) \\\\", line)
        if not match:
            continue
        current = UNKNOWN_TYPES.get(match["type"].strip(), current)
        arm, score = UNKNOWN_METHODS[match["method"]], UNKNOWN_SCORES[match["score"].strip()]
        for stat, printed in zip(UNKNOWN_FIELDS, (match["a"], match["r"], match["f"], match["frr"])):
            ledger.unknown("main", "Table 5", printed, arm, current, score, stat)


def table_s11(ledger: Ledger, si: str) -> None:
    columns = (("macro_f1", "query"), ("ASW_label", "joint"), ("trustworthiness", "joint"), ("pseudotime_smoothness", "joint"))
    for line in body(si, "tab:tradeoff450"):
        match = re.match(r"^(?P<name>[^&\\]+?) & (?P<c>.+?) \\\\$", line)
        if not match or match["name"].startswith("Configuration"):
            continue
        cells = [clean(c) for c in match["c"].split(" & ")]
        for (metric, population), printed in zip(columns, cells):
            ledger.arm("si", "Table S11", printed, ARMS[match["name"].strip()], 30, metric, population, source="campaign450")


def tables_s12_s13(ledger: Ledger, tables: str) -> None:
    arms_part = tables[tables.index("\\label{tab:reviewer-arms}"):tables.index("\\label{tab:reviewer-pairs}")]
    pairs_part = tables[tables.index("\\label{tab:reviewer-pairs}"):]
    block = None
    for line in arms_part.splitlines():
        header = re.search(r"\\textbf\{(.+?); (30|128) dimensions\}", line)
        if header:
            block = (ARMS[header.group(1)], int(header.group(2)))
            continue
        match = re.match(r"^(?P<ep>[^&]+?) & (?P<mean>[^&]+?) & (?P<d>\d+) & (?P<b>\d+) \\\\", line)
        if match and block:
            metric, population = endpoint(match["ep"])
            arm, dim = block
            ledger.arm("si", "Table S12", match["mean"], arm, dim, metric, population, source="campaign450")
            ledger.arm("si", "Table S12", match["d"], arm, dim, metric, population, "datasets", source="campaign450")
            ledger.arm("si", "Table S12", match["b"], arm, dim, metric, population, "batches", source="campaign450")
    block = None
    for line in pairs_part.splitlines():
        header = re.search(r"\\textbf\{(.+?) minus (.+?); (30|128) dimensions\}", line)
        if header:
            block = (ARMS[header.group(1)], ARMS[header.group(2)], int(header.group(3)))
            continue
        match = re.match(r"^(?P<ep>[^&]+?) & (?P<d>[^&]+?) & (?P<l>[^&]+?) & (?P<u>[^&]+?) & (?P<b>\d+) \\\\", line)
        if match and block:
            metric, population = endpoint(match["ep"])
            left, right, dim = block
            for stat, printed in zip(("delta", "lower", "upper"), (match["d"], match["l"], match["u"])):
                ledger.interval("si", "Table S13", printed, "campaign450", left, right, dim, metric, population, stat)
            ledger.interval("si", "Table S13", match["b"], "campaign450", left, right, dim, metric, population, "batches")


def table_s14(ledger: Ledger, si: str) -> None:
    dim, mode = None, None
    for line in body(si, "tab:s14"):
        header = re.search(r"\\textbf\{(30|128) dimensions[^}]*?: (means|paired differences)", line)
        if header:
            dim, mode = int(header.group(1)), header.group(2)
            continue
        match = re.match(r"^(?P<name>[^&]+?) & (?P<ep>[^&]+?) & (?P<value>[^&]+?) \\\\", line)
        if not match or dim is None:
            continue
        metric, population = endpoint(match["ep"])
        if mode == "means":
            ledger.arm("si", "Table S14", match["value"], ARMS[match["name"].strip()], dim, metric, population, source="four405")
        else:
            left, right = [ARMS[part.strip()] for part in match["name"].split(" minus ")]
            ledger.interval_cells("si", "Table S14", match["value"], "four405", left, right, dim, metric, population)


def table_s15(ledger: Ledger, si: str) -> None:
    for line in body(si, "tab:s15"):
        match = re.match(r"^(?P<type>B-cell family|CD16\+ monocytes) & (?P<method>SOLAR|scANVI|Matched PCA), (?P<score>[a-z ]+?) & "
                         r"(?P<a>[^&]+?) & (?P<r>[^&]+?) & (?P<f>[^&]+?) & (?P<frr>[^&]+?) & (?P<batches>[^&]+?) \\\\", line)
        if not match:
            continue
        omission, arm, score = UNKNOWN_TYPES[match["type"]], UNKNOWN_METHODS[match["method"]], UNKNOWN_SCORES[match["score"].strip()]
        for stat, printed in zip(UNKNOWN_FIELDS, (match["a"], match["r"], match["f"], match["frr"])):
            ledger.unknown("si", "Table S15", printed, arm, omission, score, stat)
        ledger.add("si", "Table S15", match["batches"], "unknown", {"omission": omission, "percentile": 5, "stat": "batches_pair"})


def table_s16(ledger: Ledger, si: str) -> None:
    mode = "means"
    for line in body(si, "tab:s16"):
        if "SOLAR minus variant" in line:
            mode = "differences"
            continue
        match = re.match(r"^(?P<name>[^&]+?) & (?P<ep>[^&]+?) & (?P<value>[^&]+?) \\\\", line)
        if not match or match["name"].strip() not in SCLSC_ROWS:
            continue
        metric, population = endpoint(match["ep"])
        kind, source, arm = SCLSC_ROWS[match["name"].strip()]
        if mode == "means":
            if kind == "summary":
                ledger.add("si", "Table S16", match["value"], "summary", {"dim": 30, "method": arm, "metric": metric,
                                                                           "population": population, "stat": "mean"})
            else:
                ledger.arm("si", "Table S16", match["value"], arm, 30, metric, population, source=source)
        else:
            ledger.interval_cells("si", "Table S16", match["value"], "four405", arm, "repeated", 30, metric, population, negate=True)


def table_s10(ledger: Ledger, paired: str) -> None:
    for line in paired.splitlines():
        match = re.match(r"^(?P<contrast>[^&\\]+?) & (?P<ep>[^&]+?) & (?P<cell>[^&]+?) & (?P<b>\d+) & (?P<pos>\d+) \\\\", line)
        if not match:
            continue
        metric, population = endpoint(match["ep"])
        metric = HISTORICAL_METRICS.get(metric, metric)
        contrast = HISTORICAL_CONTRASTS[match["contrast"].strip()]
        ledger.interval_cells("si", "Table S10", match["cell"], "historical", contrast, "", 0, metric, population)
        ledger.interval("si", "Table S10", match["b"], "historical", contrast, "", 0, metric, population, "batches")
        ledger.interval("si", "Table S10", match["pos"], "historical", contrast, "", 0, metric, population, "positive")


def prose(ledger: Ledger) -> None:
    """Numbers printed in the revised prose. (doc, location, printed, kind/spec)."""
    a, i, u, ui = ledger.arm, ledger.interval, ledger.unknown, ledger.unknown_interval
    C450, F405 = "campaign450", "four405"
    for loc in ("Abstract", "3.6 Anchor geometry and local preservation"):
        ledger.add("main", loc, "675", "count", {"check": "matched_fits"})
    a("main", "Abstract", "0.818", "gaussian", 30, "macro_f1", "query")
    L = "4.3 Matched controls"
    a("main", L, "0.818", "gaussian", 30, "macro_f1", "query")
    a("main", L, "0.811", "repeated", 30, "macro_f1", "query")
    for stat, printed in (("delta", "0.007"), ("lower", "0.002"), ("upper", "0.012"), ("lodo_min", "-0.003"), ("lodo_max", "0.012")):
        i("main", L, printed, C450, "gaussian", "repeated", 30, "macro_f1", "query", stat)
    a("main", L, "0.805", "learnable", 30, "macro_f1", "query")
    for arm, printed in (("repeated", "0.812"), ("unique", "0.813"), ("gaussian", "0.811"), ("learnable", "0.808")):
        a("main", L, printed, arm, 128, "macro_f1", "query", source=F405)
    for stat, printed in (("delta", "0.001"), ("lower", "-0.001"), ("upper", "0.003")):
        i("main", L, printed, F405, "repeated", "gaussian", 128, "macro_f1", "query", stat)
    for stat, printed in (("delta", "0.005"), ("lower", "-0.003"), ("upper", "0.010")):
        i("main", L, printed, F405, "repeated", "learnable", 128, "macro_f1", "query", stat)
    a("main", L, "0.951", "unique", 128, "trustworthiness", "joint", source=F405)
    a("main", L, "0.933", "repeated", 128, "trustworthiness", "joint", source=F405)
    a("main", L, "0.844", "unique", 128, "ASW_label", "joint", source=F405)
    a("main", L, "0.869", "repeated", 128, "ASW_label", "joint", source=F405)
    a("main", L, "0.806", "none", 30, "macro_f1", "query")
    a("main", L, "0.860", "unique", 30, "ASW_label", "joint"); a("main", L, "0.873", "repeated", 30, "ASW_label", "joint")
    a("main", L, "1.360", "unique", 30, "iLISI", "joint"); a("main", L, "1.743", "repeated", 30, "iLISI", "joint")
    a("main", L, "0.940", "unique", 30, "trustworthiness", "query"); a("main", L, "0.936", "repeated", 30, "trustworthiness", "query")
    a("main", L, "0.866", "unique", 30, "pseudotime_smoothness", "joint"); a("main", L, "0.860", "repeated", 30, "pseudotime_smoothness", "joint")
    i("main", L, "0.008", C450, "local", "repeated", 30, "trustworthiness", "joint", "delta")
    i("main", L, "0.009", C450, "local", "repeated", 30, "pseudotime_smoothness", "joint", "delta")
    i("main", L, "0.006", C450, "hierarchy_local", "repeated", 30, "trustworthiness", "joint", "delta")
    i("main", L, "0.007", C450, "hierarchy_local", "repeated", 30, "pseudotime_smoothness", "joint", "delta")
    i("main", L, "0.003", C450, "hierarchy", "repeated", 30, "trustworthiness", "joint", "magnitude")
    i("main", L, "0.005", C450, "hierarchy", "repeated", 30, "pseudotime_smoothness", "joint", "magnitude")
    a("main", L, "0.810", "local", 30, "macro_f1", "query"); a("main", L, "0.815", "hierarchy_local", 30, "macro_f1", "query")
    a("main", L, "0.927", "unique", 30, "trustworthiness", "joint", source=F405)
    a("main", L, "0.932", "unique_local", 30, "trustworthiness", "joint")
    for stat, printed in (("delta", "0.005"), ("lower", "0.004"), ("upper", "0.006")):
        i("main", L, printed, F405, "unique_local", "unique", 30, "trustworthiness", "joint", stat)
    a("main", L, "0.866", "unique", 30, "pseudotime_smoothness", "joint", source=F405)
    a("main", L, "0.872", "unique_local", 30, "pseudotime_smoothness", "joint")
    for stat, printed in (("lower", "0.004"), ("upper", "0.009")):
        i("main", L, printed, F405, "unique_local", "unique", 30, "pseudotime_smoothness", "joint", stat)
    a("main", L, "0.810", "unique_local", 30, "macro_f1", "query"); a("main", L, "0.811", "unique", 30, "macro_f1", "query", source=F405)
    for stat, printed in (("delta", "-0.001"), ("lower", "-0.002"), ("upper", "-0.001")):
        i("main", L, printed, F405, "unique_local", "unique", 30, "ASW_label", "joint", stat)
    for arm, printed in (("local003", "0.915"), ("local", "0.920"), ("local03", "0.931")):
        a("main", L, printed, arm, 30, "trustworthiness", "joint", source=F405)
    for arm, printed in (("local003", "0.864"), ("local", "0.869"), ("local03", "0.877")):
        a("main", L, printed, arm, 30, "pseudotime_smoothness", "joint", source=F405)
    a("main", L, "0.810", "local03", 30, "macro_f1", "query"); a("main", L, "0.811", "local003", 30, "macro_f1", "query")
    a("main", L, "0.873", "local003", 30, "ASW_label", "joint"); a("main", L, "0.867", "local03", 30, "ASW_label", "joint")
    i("main", L, "0.004", F405, "unique_local", "repeated", 30, "trustworthiness", "query", "delta")
    a("main", L, "0.810", "validation_selected", 30, "macro_f1", "query"); a("main", L, "0.867", "validation_selected", 30, "ASW_label", "joint")
    L = "4.5 SCLSC comparison"
    a("main", L, "0.786", "sclsc_best_genes", 30, "macro_f1", "query"); a("main", L, "0.787", "sclsc_best_pca40", 30, "macro_f1", "query")
    ledger.add("main", L, "0.815", "summary", {"dim": 30, "method": "sclsc_refonly", "metric": "macro_f1", "population": "query", "stat": "mean"})
    a("main", L, "0.903", "sclsc_best_genes", 30, "trustworthiness", "query"); a("main", L, "0.921", "sclsc_best_pca40", 30, "trustworthiness", "query")
    a("main", L, "0.811", "sclsc_best_genes", 30, "pseudotime_smoothness", "joint"); a("main", L, "0.847", "sclsc_best_pca40", 30, "pseudotime_smoothness", "joint")
    a("main", L, "0.936", "repeated", 30, "trustworthiness", "query", source=F405); a("main", L, "0.860", "repeated", 30, "pseudotime_smoothness", "joint", source=F405)
    a("main", L, "0.946", "sclsc_best_genes", 30, "ASW_label", "joint"); a("main", L, "0.890", "sclsc_best_pca40", 30, "ASW_label", "joint")
    for stat, printed in (("delta", "0.015"), ("lower", "0.009"), ("upper", "0.021")):
        i("main", L, printed, F405, "sclsc_best_pca40", "repeated", 30, "trustworthiness", "query", stat, negate=True)
    for stat, printed in (("delta", "0.014"), ("lower", "0.006"), ("upper", "0.020")):
        i("main", L, printed, F405, "sclsc_best_pca40", "repeated", 30, "pseudotime_smoothness", "joint", stat, negate=True)
    L = "4.6 Unknown-type rejection"
    D, COS = "negative_weighted15nn_distance", "max_training_anchor_cosine"
    for arm, printed in (("solar", "0.955"), ("scanvi", "0.961"), ("pca", "0.601")):
        u("main", L, printed, arm, "Bcells", D, "auroc")
    for arm, printed in (("solar", "0.909"), ("scanvi", "0.375"), ("pca", "0.112")):
        u("main", L, printed, arm, "Bcells", D, "unknown_recall")
    for arm, printed in (("solar", "0.455"), ("scanvi", "0.838"), ("pca", "0.941")):
        u("main", L, printed, arm, "CD16", D, "auroc")
    u("main", L, "0.177", "solar", "CD16", D, "unknown_recall")
    for stat, printed in (("delta", "-0.383"), ("lower", "-0.533"), ("upper", "-0.266")):
        ui("main", L, printed, "solar", "scanvi", "CD16", "auroc", stat)
    u("main", L, "0.867", "solar", "Bcells", COS, "auroc"); u("main", L, "0.452", "solar", "CD16", COS, "auroc")
    u("main", L, "0.307", "solar", "CD16", D, "known_false_rejection"); u("main", L, "0.431", "pca", "CD16", D, "known_false_rejection")
    u("main", L, "0.42", "pca", "CD16", D, "known_query_macro_f1"); u("main", L, "0.55", "solar", "CD16", D, "known_query_macro_f1")
    # Additional file 1 prose
    ledger.add("si", "SI 2.3", "675", "count", {"check": "matched_fits"})
    i("si", "SI 2.8", "-0.003", C450, "gaussian", "repeated", 30, "macro_f1", "query", "lodo_min")
    i("si", "SI 2.8", "+0.012", C450, "gaussian", "repeated", 30, "macro_f1", "query", "lodo_max")
    L = "SI 4 Anchor geometry"
    a("si", L, "0.810", "validation_selected", 30, "macro_f1", "query")
    i("si", L, "-0.001", C450, "validation_selected", "repeated", 30, "macro_f1", "query", "delta")
    a("si", L, "0.808", "learnable", 128, "macro_f1", "query", source=F405); a("si", L, "0.813", "unique", 128, "macro_f1", "query", source=F405)
    a("si", L, "0.810", "local03", 30, "macro_f1", "query"); a("si", L, "0.811", "local003", 30, "macro_f1", "query")
    L = "SI 5 Unknown-type rejection"
    for stat, printed in (("delta", "-0.383"), ("lower", "-0.533"), ("upper", "-0.266")):
        ui("si", L, printed, "solar", "scanvi", "CD16", "auroc", stat)
    for stat, printed in (("delta", "-0.710"), ("lower", "-0.799"), ("upper", "-0.637")):
        ui("si", L, printed, "solar", "scanvi", "CD16", "unknown_recall", stat)
    ui("si", L, "-0.006", "solar", "scanvi", "Bcells", "auroc", "difference")
    u("si", L, "0.31", "solar", "CD16", D, "known_false_rejection"); u("si", L, "0.43", "pca", "CD16", D, "known_false_rejection")


def source_section(text: str, location: str) -> tuple[str, int]:
    """Return one named prose section, excluding subsequent headings and tables."""
    if location == 'Abstract':
        match = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', text, re.S)
        if not match:
            raise ValueError('missing abstract environment')
        return match.group(1), text.count('\n', 0, match.start(1)) + 1
    titles = {
        '3.6 Anchor geometry and local preservation': 'anchor geometry',
        '4.3 Matched controls': 'matched control',
        '4.5 SCLSC comparison': 'sclsc',
        '4.6 Unknown-type rejection': 'unknown',
        'SI 2.3': 'anchor geometry',
        'SI 2.8': 'uncertainty',
        'SI 4 Anchor geometry': 'anchor geometry',
        'SI 5 Unknown-type rejection': 'unknown',
    }
    needle = titles[location]
    headings = list(re.finditer(r'\\(?:sub)*section\*?\{([^{}]*)\}', text))
    candidates = [n for n, m in enumerate(headings) if needle in clean(m.group(1)).lower()]
    # Number prefixes refer to the declared section; duplicate titles are ambiguous.
    prefix = location.removeprefix('SI ').split()[0]
    numbered = [n for n in candidates if clean(headings[n].group(1)).startswith(prefix)]
    candidates = numbered or candidates
    if len(candidates) != 1:
        raise ValueError(f'{location}: expected one section, found {len(candidates)}')
    n = candidates[0]
    start = headings[n].end()
    end = headings[n + 1].start() if n + 1 < len(headings) else len(text)
    section = text[start:end]
    section = re.sub(r'\\begin\{(?:table\*?|longtable)\}.*?\\end\{(?:table\*?|longtable)\}', '', section, flags=re.S)
    return section, text.count('\n', 0, start) + 1


def extract_prose(rows: list[dict], sources: dict[str, str]) -> list[dict]:
    """Bind semantic templates to numeric tokens within their declared sections.

    Templates specify expected printed precision, not recalculated experimental values.
    A changed or missing token fails closed instead of borrowing a value elsewhere.
    """
    locations = []
    for row in rows:
        section, first_line = source_section(sources[row['doc']], row['location'])
        normalized = section.replace('$', '')
        match = re.search(r'(?<![\d.])' + re.escape(row['printed']) + r'(?![\d.])', normalized)
        if not match:
            raise ValueError(f"{row['doc']} {row['location']}: missing numeric token {row['printed']}")
        row['printed'] = match.group(0)
        locations.append(dict(doc=row['doc'], location=row['location'], printed=row['printed'],
                              section_first_line=first_line,
                              section_line_offset=normalized.count('\n', 0, match.start()),
                              context=normalized[max(0, match.start()-100):match.end()+100]))
    return locations


def check_expected_counts(rows: list[dict], reference: Path) -> None:
    from collections import Counter
    with reference.open(newline='') as handle:
        frozen = list(csv.DictReader(handle))
    expected = Counter((r['doc'], r['location']) for r in frozen)
    actual = Counter((r['doc'], r['location']) for r in rows)
    if actual != expected:
        raise ValueError(f'claim population changed: expected {dict(expected)}, got {dict(actual)}')
    if frozen and 'spec' in frozen[0]:
        identity = lambda r: (r['doc'], r['location'], r['kind'], json.dumps(json.loads(r['spec']), sort_keys=True))
        if Counter(map(identity, rows)) != Counter(map(identity, frozen)):
            raise ValueError('claim identities changed despite matching counts')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--main-tex", type=Path, required=True)
    parser.add_argument("--si-tex", type=Path, required=True)
    parser.add_argument("--si-tables-tex", type=Path, required=True)
    parser.add_argument("--si-paired-tex", type=Path, required=True)
    parser.add_argument('--locations', type=Path, help='Optional private JSON receipt with prose source contexts')
    parser.add_argument("--output", type=Path, default=ROOT / "paper" / "claims_revision.csv")
    args = parser.parse_args()
    main_tex, si_tex = args.main_tex.read_text(), args.si_tex.read_text()
    tables_tex, paired_tex = args.si_tables_tex.read_text(), args.si_paired_tex.read_text()

    ledger = Ledger()
    prose(ledger)
    locations = extract_prose(ledger.rows, {'main': main_tex, 'si': si_tex})
    # Normalize harmless math delimiters and spacing before table parsing.
    main_tex, si_tex, tables_tex, paired_tex = [
        '\n'.join(re.sub(r'\s*&\s*', ' & ', line.strip().replace('$', '')) for line in text.splitlines())
        for text in (main_tex, si_tex, tables_tex, paired_tex)]
    table4(ledger, main_tex)
    table5(ledger, main_tex)
    table_s10(ledger, paired_tex)
    table_s11(ledger, si_tex)
    tables_s12_s13(ledger, tables_tex)
    table_s14(ledger, si_tex)
    table_s15(ledger, si_tex)
    table_s16(ledger, si_tex)
    check_expected_counts(ledger.rows, ROOT / 'paper/claims_revision.csv')

    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["claim_id", "doc", "location", "printed", "kind", "spec"])
        writer.writeheader()
        for n, row in enumerate(ledger.rows, 1):
            writer.writerow({"claim_id": f"rev-{n:04d}", **row})
    if args.locations:
        args.locations.write_text(json.dumps(locations, indent=2) + '\n')
    by_location = {}
    for row in ledger.rows:
        by_location[row["location"]] = by_location.get(row["location"], 0) + 1
    for location, count in by_location.items():
        print(f"{location:42s} {count:5d}")
    print(f"wrote {len(ledger.rows)} claims to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
