"""Exact dataset-stratified paired bootstrap of released batch means; no model fitting."""
from pathlib import Path
import csv, itertools, statistics, json, hashlib
import argparse
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, default=Path('rebuilt/historical_uncertainty'))
args = parser.parse_args()
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data/heldout'
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
metrics = list(csv.DictReader((DATA/'metrics.csv').open()))
runs = list(csv.DictReader((DATA/'runs.csv').open()))

def batch(method, dim, metric, population):
    groups = {}
    for r in metrics:
        if (r['method'],r['dimension'],r['metric'],r['population']) == (method,str(dim),metric,population):
            groups.setdefault((r['dataset_id'],r['heldout_batch']), []).append(r)
    out = {}
    for key, rows in groups.items():
        expected = 1 if method == 'unintegrated_pca_matched' else 5
        valid = [r for r in rows if r['status']=='computed' and r['comparison_eligible'].lower()=='true' and r['value'] not in ('','nan')]
        if len(valid)==len(rows)==expected:
            out[key] = statistics.mean(float(r['value']) for r in valid)
    return out

def quantile(values, p):
    h=(len(values)-1)*p; i=int(h); f=h-i
    return values[i]*(1-f)+values[min(i+1,len(values)-1)]*f

specs=[]
for name,other in [('PCA', 'unintegrated_pca_matched'),('scANVI','frozen_reference_scanvi'),('SCLSC','sclsc_refonly')]:
    for metric,pop in [('macro_f1','query'),('labelASW','joint'),('trustworthiness','query'),('pseudotime_smoothness','joint')]:
        specs.append(('SOLAR30 - '+name,('solar_orthogonal',30),(other,30),metric,pop))
for name,other in [('none','solar_none'),('unique','solar_orthogonal_uniq')]:
    for metric,pop in [('macro_f1','query'),('labelASW','joint'),('iLISI','joint'),('trustworthiness','query'),('pseudotime_smoothness','joint')]:
        specs.append(('Repeated128 - '+name,('solar_orthogonal',128),(other,128),metric,pop))
summary=[]; pairs=[]
for name,left,right,metric,pop in specs:
    a=batch(*left,metric,pop); b=batch(*right,metric,pop)
    groups={}
    for key in sorted(a.keys() & b.keys()):
        diff=a[key]-b[key]
        groups.setdefault(key[0],[]).append(diff)
        pairs.append(dict(contrast=name,metric=metric,population=pop,dataset=key[0],batch=key[1],left=a[key],right=b[key],difference=diff))
    assert groups and all(len(v)==3 for v in groups.values()), (name,metric,groups)
    dsmeans=[statistics.mean(v) for v in groups.values()]
    resamples=[[statistics.mean(s) for s in itertools.product(v,repeat=len(v))] for v in groups.values()]
    boots=sorted(statistics.mean(s) for s in itertools.product(*resamples))
    loo=[statistics.mean(dsmeans[:i]+dsmeans[i+1:]) for i in range(len(dsmeans))] if len(dsmeans)>1 else []
    summary.append(dict(contrast=name,metric=metric,population=pop,delta=statistics.mean(dsmeans),lower=quantile(boots,.025),upper=quantile(boots,.975),datasets=len(groups),batches=sum(map(len,groups.values())),positive_batches=sum(v>0 for vs in groups.values() for v in vs),bootstrap_draws=len(boots),leave_dataset_out_min=min(loo) if loo else '',leave_dataset_out_max=max(loo) if loo else ''))
for filename,rows in [('paired_batch_differences.csv',pairs),('paired_batch_uncertainty.csv',summary)]:
    with (OUT/filename).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'contrasts': len(summary), 'batch_differences': len(pairs), 'status': 'recomputed'}))
