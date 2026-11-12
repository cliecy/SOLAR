"""Compare the follow-up replay and frozen 450-fit controls."""
from pathlib import Path
import argparse
import hashlib
import json
import pandas as pd
import numpy as np

R = Path(__file__).resolve().parents[1]


def compare(a, b, keys):
    x = pd.read_csv(a, keep_default_na=False)
    y = pd.read_csv(b, keep_default_na=False)
    assert set(x.columns) == set(y.columns), (a, 'columns')
    assert not x.duplicated(keys).any() and not y.duplicated(keys).any(), (a, 'duplicates')
    x = x.sort_values(keys).reset_index(drop=True)
    y = y.sort_values(keys).reset_index(drop=True)
    assert len(x) == len(y), (a, len(x), len(y))
    maximum = 0.0
    for c in x:
        missing_x = x[c].astype(str).eq('')
        missing_y = y[c].astype(str).eq('')
        assert missing_x.equals(missing_y), (a, c, 'missingness')
        xx = pd.to_numeric(x.loc[~missing_x, c], errors='coerce')
        yy = pd.to_numeric(y.loc[~missing_y, c], errors='coerce')
        if xx.notna().all() and yy.notna().all():
            if len(xx):
                assert np.isfinite(xx).all() and np.isfinite(yy).all(), (a, c, 'nonfinite')
                error = float(np.max(np.abs(xx.to_numpy() - yy.to_numpy())))
                maximum = max(maximum, error)
                assert error <= 1e-12, (a, c, error)
        else:
            assert x[c].astype(str).equals(y[c].astype(str)), (a, c)
    return dict(table=str(b.relative_to(R)), rows=len(x), columns=len(x.columns), maximum_absolute_error=maximum)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--replayed', type=Path, default=R / 'replayed')
    parser.add_argument('--old450', type=Path, default=R / 'replayed-old450')
    parser.add_argument('--report', type=Path, default=R / 'release-verification.json')
    args = parser.parse_args()
    checks = []
    for name, keys in {
        'metrics.csv': ['key', 'metric', 'population'],
        'validation_selection.csv': ['dataset', 'batch', 'seed'],
        'batch_means.csv': ['arm', 'dimension', 'dataset', 'batch', 'metric', 'population'],
        'arm_summary.csv': ['arm', 'dimension', 'metric', 'population'],
        'paired_batch_differences.csv': ['left', 'right', 'dimension', 'metric', 'population', 'dataset', 'batch'],
        'paired_batch_uncertainty.csv': ['left', 'right', 'dimension', 'metric', 'population'],
    }.items():
        checks.append(compare(args.old450 / name, R / 'evidence/old450' / name, keys))
    checks.append(compare(args.replayed / 'all_eligible_paired_intervals.csv',
                          R / 'expected/all_eligible_paired_intervals.csv',
                          ['left', 'right', 'left_dimension', 'right_dimension', 'metric', 'population',
                           'omission', 'confidence', 'percentile']))
    for line in (R / 'MANIFEST.sha256').read_text().splitlines():
        digest, name = line.split('  ', 1)
        assert hashlib.sha256((R / name).read_bytes()).hexdigest() == digest, name
    report = dict(status='PASS', tolerance=1e-12, complete_table_comparisons=checks)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
