"""Frozen-score replay extracted from the 450-fit campaign aggregator.

No fitting, embedding rescoring, remote execution or machine paths are required.
"""
import argparse
import csv
import hashlib
import itertools
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

ORDER = ['repeated', 'unique', 'none', 'gaussian', 'learnable', 'hierarchy', 'local', 'hierarchy_local']
BATCHES = {'pancreas': ['fluidigmc1', 'inDrop2', 'inDrop3'],
           'immune_cell_human': ['10X', 'Oetjen_A', 'Villani'],
           'lung_atlas': ['3', '4', 'B1']}

def read(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))

def write_csv(path, rows):
    if not rows:
        path.write_text('')
        return
    with path.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def paired_interval(groups):
    # Ordered exhaustive batch bootstrap, pairing arms and keeping dataset weights equal.
    dsmeans = np.array([np.mean(v) for v in groups.values()])
    distributions = [np.array([np.mean(x) for x in itertools.product(v, repeat=len(v))])
                     for v in groups.values()]
    draws = np.array([0.0])
    for values in distributions:
        draws = (draws[:, None] + values).ravel()
    draws /= len(distributions)
    lo, hi = np.quantile(draws, [.025, .975], method='linear')
    loo = [np.mean(np.delete(dsmeans, i)) for i in range(len(dsmeans))] if len(dsmeans) > 1 else []
    return dict(delta=float(dsmeans.mean()), lower=float(lo), upper=float(hi),
                datasets=len(groups), batches=sum(map(len, groups.values())),
                positive_batches=sum(x > 0 for v in groups.values() for x in v),
                interval_resolution='degenerate_single_batch_per_dataset' if all(len(v) == 1 for v in groups.values()) else 'batch_resampling',
                bootstrap_draws=len(draws), leave_dataset_out_min=float(min(loo)) if loo else '',
                leave_dataset_out_max=float(max(loo)) if loo else '')

def replay(inputs, output):
    output.mkdir(parents=True, exist_ok=True)
    ledger = read(inputs / 'run_ledger.csv')
    expected = {f'{arm}__d{dim}__{ds}__{batch}__s{seed}'
                for ds, batches in BATCHES.items() for batch in batches
                for seed in range(40, 45)
                for dim, arm in [(30, x) for x in ORDER] + [(128, 'gaussian'), (128, 'learnable')]}
    assert len(ledger) == len(expected) == 450
    assert {r['key'] for r in ledger} == expected
    assert all(r['training'] == r['annotation'] == r['endpoints'] == 'True' and not r['failure'] for r in ledger)
    raw = read(inputs / 'metrics.csv')
    rows = [r for r in raw if r['arm'] != 'validation_selected']
    assert {r['key'] for r in rows} == expected
    for r in rows:
        r['dimension'] = int(r['dimension']); r['seed'] = int(r['seed'])
        r['value'] = float(r['value']) if r['status'] == 'computed' else ''
        assert r['value'] == '' or np.isfinite(r['value'])
    per_run = defaultdict(list)
    for r in rows: per_run[r['key']].append(r)
    panels = None
    for key, group in per_run.items():
        actual = {(r['metric'], r['population']) for r in group}
        assert len(group) == len(actual) == 34, key
        if panels is None: panels = actual
        assert actual == panels
    candidates = read(inputs / 'validation_candidates.csv')
    assert len(candidates) == 450
    validated = {(r['dataset'], r['batch'], int(r['seed']), r['arm']): r
                 for r in candidates if r['dimension'] == '30'}
    assert len(validated) == 360
    selections = []; selected_keys = {}
    for ds, batches in BATCHES.items():
        for batch, seed in itertools.product(batches, range(40, 45)):
            vals = [validated[(ds, batch, seed, arm)] for arm in ORDER]
            assert len({v['reference_partition_sha256'] for v in vals}) == 1
            chosen = max(vals, key=lambda v: (float(v['macro_f1']), -ORDER.index(v['arm'])))
            key = f"{chosen['arm']}__d30__{ds}__{batch}__s{seed}"
            selected_keys[(ds, batch, seed)] = key
            selections.append(dict(dataset=ds, batch=batch, seed=seed, selected_arm=chosen['arm'],
                selected_key=key, validation_macro_f1=float(chosen['macro_f1']),
                reference_partition_sha256=chosen['reference_partition_sha256']))
    assert len(selections) == 45
    selected_rows = [dict(r, arm='validation_selected', key='validation_selected::' + r['key'])
                     for r in rows if r['dimension'] == 30
                     and selected_keys.get((r['dataset'], r['batch'], r['seed'])) == r['key']]
    allrows = rows + selected_rows
    write_csv(output / 'metrics.csv', allrows)
    write_csv(output / 'validation_selection.csv', selections)
    # Batch summaries require all five distinct seeds with a computed endpoint.
    grouped = defaultdict(list)
    for r in allrows:
        grouped[(r['arm'], r['dimension'], r['dataset'], r['batch'], r['metric'], r['population'])].append(r)
    batchrows = []; coverage = []
    for key, group in sorted(grouped.items()):
        arm, dim, ds, batch, metric, pop = key
        base = dict(arm=arm, dimension=dim, dataset=ds, batch=batch, metric=metric, population=pop)
        good = [r for r in group if r['status'] == 'computed']
        coverage.append(dict(**base, available=len(group), computed=len(good),
                             statuses=json.dumps({s: sum(r['status'] == s for r in group) for s in sorted({r['status'] for r in group})})))
        assert len({r['seed'] for r in group}) == len(group)
        if len(good) == 5 and {r['seed'] for r in good} == set(range(40, 45)):
            batchrows.append(dict(**base, value=float(np.mean([r['value'] for r in good])), seeds=5))
    write_csv(output / 'batch_means.csv', batchrows); write_csv(output / 'endpoint_coverage.csv', coverage)
    maps = defaultdict(dict)
    for r in batchrows: maps[(r['arm'], r['dimension'], r['metric'], r['population'])][(r['dataset'], r['batch'])] = r['value']
    summaries = []
    for (arm, dim, metric, pop), values in sorted(maps.items()):
        groups = defaultdict(list)
        for (ds, batch), value in values.items(): groups[ds].append(value)
        summaries.append(dict(arm=arm, dimension=dim, metric=metric, population=pop,
                              value=float(np.mean([np.mean(v) for v in groups.values()])),
                              datasets=len(groups), batches=len(values), fits=len(values)*5))
    write_csv(output / 'arm_summary.csv', summaries)
    contrasts = [(x, 'repeated', 30) for x in ORDER if x != 'repeated']
    contrasts += [('validation_selected', x, 30) for x in ORDER]
    contrasts += [('learnable', 'gaussian', 128)]
    pairs, uncertainty = [], []
    for left, right, dim in contrasts:
        for metric, pop in sorted({(k[2], k[3]) for k in maps}):
            lv = maps.get((left, dim, metric, pop), {}); rv = maps.get((right, dim, metric, pop), {})
            groups = defaultdict(list)
            for ds, batch in sorted(lv.keys() & rv.keys()):
                diff = lv[(ds, batch)] - rv[(ds, batch)]; groups[ds].append(diff)
                pairs.append(dict(left=left, right=right, dimension=dim, metric=metric, population=pop,
                                  dataset=ds, batch=batch, left_value=lv[(ds, batch)], right_value=rv[(ds, batch)], difference=diff))
            if groups:
                uncertainty.append(dict(left=left, right=right, dimension=dim, metric=metric, population=pop,
                                        **paired_interval(groups)))
    write_csv(output / 'paired_batch_differences.csv', pairs)
    write_csv(output / 'paired_batch_uncertainty.csv', uncertainty)

    return dict(unique_complete_runs=len(ledger), metric_rows=len(allrows), selection_groups=len(selections),
                arm_endpoint_rows=len(summaries), paired_intervals=len(uncertainty))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=Path(__file__).resolve().parents[1] / 'data/campaign450')
    parser.add_argument('--output', type=Path, default=Path('rebuilt/campaign450'))
    args = parser.parse_args()
    print(json.dumps(replay(args.inputs, args.output), indent=2))
