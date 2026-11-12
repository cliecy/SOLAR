#!/usr/bin/env python3
"""Rebuild every contracted numerical table and compare with frozen records."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from replay_campaign import replay

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = 1e-12


def compare(actual, expected):
    """Compare full CSV populations, identities, missingness and numerical cells."""
    with actual.open(newline='') as handle:
        a = list(csv.DictReader(handle))
    with expected.open(newline='') as handle:
        b = list(csv.DictReader(handle))
    assert len(a) == len(b), (actual.name, len(a), len(b))
    assert a and set(a[0]) == set(b[0]), actual.name
    # Producers may reorder columns/rows; stable identity is every nonnumeric field
    # plus the explicit scientific identity columns.
    identity = [k for k in ['key', 'run_id', 'arm', 'left', 'right', 'dimension', 'dataset', 'batch',
        'seed', 'metric', 'population', 'selected_key', 'contrast', 'block', 'comparison', 'method',
        'dataset_id', 'heldout_batch', 'excluded_dataset', 'lhs_method', 'lhs_dimension',
        'rhs_method', 'rhs_dimension'] if k in a[0]]
    def key(r): return tuple(r[k] for k in identity)
    assert len({key(r) for r in a}) == len(a), (actual.name, 'duplicate identity')
    assert {key(r) for r in a} == {key(r) for r in b}, actual.name
    bmap = {key(r): r for r in b}
    maximum = 0.0
    for row in a:
        other = bmap[key(row)]
        for k, value in row.items():
            target = other[k]
            try:
                x, y = float(value), float(target)
            except ValueError:
                assert value == target, (actual.name, key(row), k)
            else:
                if math.isnan(x) or math.isnan(y):
                    assert math.isnan(x) and math.isnan(y), (actual.name, key(row), k)
                else:
                    assert math.isfinite(x) and math.isfinite(y)
                    error = abs(x-y); maximum = max(maximum, error)
                    assert error <= TOLERANCE, (actual.name, key(row), k, error)
    return {'file': str(expected.relative_to(ROOT)), 'rows': len(a), 'max_absolute_error': maximum}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('rebuilt'))
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    for line in (ROOT / 'MANIFEST.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    campaign = ROOT / 'data/campaign450'
    complete = json.loads((campaign / 'COMPLETE.json').read_text())
    for name, digest in complete['derived_sha256'].items():
        assert hashlib.sha256((campaign / name).read_bytes()).hexdigest() == digest, name
    scope = replay(campaign, args.output / 'campaign450')
    checks = []
    for name in ['metrics.csv', 'validation_selection.csv', 'batch_means.csv', 'endpoint_coverage.csv',
                 'arm_summary.csv', 'paired_batch_differences.csv', 'paired_batch_uncertainty.csv']:
        checks.append(compare(args.output / 'campaign450' / name, campaign / name))
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_experiment_v1_2_tables.py'),
        '--input-dir', str(ROOT / 'data/heldout'), '--output-dir', str(args.output / 'historical')], check=True)
    for frozen in sorted((ROOT / 'data/heldout/tables').glob('*.csv')):
        checks.append(compare(args.output / 'historical/tables' / frozen.name, frozen))
    subprocess.run([sys.executable, str(ROOT / 'scripts/replay_historical_uncertainty.py'),
        '--output', str(args.output / 'historical_uncertainty')], check=True)
    for frozen in sorted((ROOT / 'data/historical_uncertainty').glob('*.csv')):
        checks.append(compare(args.output / 'historical_uncertainty' / frozen.name, frozen))
    subprocess.run([sys.executable, str(ROOT / 'scripts/verify_paper_numbers.py'),
        '--report', str(args.output / 'historical_claims.csv')], check=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/build_paper_figures.py'),
        '--output-dir', str(args.output / 'figures')], check=True)
    followup = ROOT / 'experiments/four405'
    subprocess.run([sys.executable, str(followup / 'replay.py'), '--root', str(followup),
                    '--output', str(args.output / 'four405/replayed')], check=True)
    subprocess.run([sys.executable, str(followup / 'scripts/replay_old450.py'),
                    '--inputs', str(followup / 'evidence/old450'),
                    '--output', str(args.output / 'four405/old450')], check=True)
    subprocess.run([sys.executable, str(followup / 'scripts/verify_release.py'),
                    '--replayed', str(args.output / 'four405/replayed'),
                    '--old450', str(args.output / 'four405/old450'),
                    '--report', str(args.output / 'four405/verification.json')], check=True)
    subprocess.run([sys.executable, str(ROOT / 'scripts/make_fig3_matched_tradeoffs.py'),
                    '--output-dir', str(args.output / 'figures')], check=True)
    followup_report = json.loads((args.output / 'four405/replayed/verification.json').read_text())
    followup_checks = json.loads((args.output / 'four405/verification.json').read_text())
    report = dict(status='PASS', reproduction_level='saved-score reconstruction and quantitative figures',
                  tolerance_absolute=TOLERANCE, campaign=scope, tables=checks,
                  followup=followup_report, followup_tables=followup_checks['complete_table_comparisons'])
    (args.output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
