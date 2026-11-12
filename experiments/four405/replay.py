#!/usr/bin/env python3
"""Independent saved-score replay. Requires numpy,pandas; no training/inference."""
from pathlib import Path
import argparse, hashlib, itertools, json
import numpy as np
import pandas as pd
PANEL=['arm','dimension','dataset','batch','metric','population','omission','confidence','percentile']
SUMMARY=['arm','dimension','metric','population','omission','confidence','percentile']
def interval(groups):
    distributions=[]
    for ds in sorted(groups):
        v=groups[ds]
        distributions.append(np.array([np.mean(t) for t in itertools.product(v,repeat=len(v))]))
    # Independently form Cartesian product rather than calling the original routine.
    draws=np.array([np.mean(t) for t in itertools.product(*distributions)])
    lo,hi=np.quantile(draws,[.025,.975],method='linear')
    return float(np.mean([np.mean(v) for v in groups.values()])),float(lo),float(hi),len(draws)
def replay(root, output=None):
    out=output or root/'replayed';out.mkdir(parents=True, exist_ok=True)
    base=root/'evidence'/'new405'
    raw=pd.read_csv(base/'all_records.csv',keep_default_na=False)
    ledger=pd.read_csv(base/'records405.csv',keep_default_na=False)
    assert len(ledger)==ledger.key.nunique()==405
    assert ledger.complete.all() and sum(ledger.experiment=='closed_label')==315 and sum(ledger.experiment=='unknown')==90
    assert sum(ledger.neural)==375 and sum(~ledger.neural)==30
    keys=set(ledger.key);new=raw[raw.key.isin(keys)];old=raw[~raw.key.isin(keys)]
    assert len(new)==12510 and new.key.nunique()==405 and old.key.nunique()==450
    original=pd.read_csv(root/'evidence'/'old450'/'metrics.csv',keep_default_na=False)
    original=original[original.arm!='validation_selected']
    assert original.key.nunique()==450 and len(original)==len(old)==15300
    checkcols=['key','metric','population','status','value']
    aa=old[checkcols].sort_values(checkcols[:3]).reset_index(drop=True)
    bb=original[checkcols].sort_values(checkcols[:3]).reset_index(drop=True)
    assert aa[checkcols[:4]].equals(bb[checkcols[:4]])
    computed=aa.status=='computed';assert np.allclose(aa.loc[computed,'value'].astype(float),bb.loc[computed,'value'].astype(float),atol=1e-14,rtol=0)
    rows=[]
    for vals,g in raw.groupby(PANEL,dropna=False,sort=True):
        assert not g.seed.duplicated().any()
        good=g[g.status=='computed']
        if set(good.seed)==set(range(40,45)) and len(good)==5:
            rows.append(dict(zip(PANEL,vals),value=float(good.value.astype(float).mean()),seeds=5))
    bm=pd.DataFrame(rows);bm.to_csv(out/'batch_means.csv',index=False)
    saved=pd.read_csv(base/'batch_means.csv',keep_default_na=False)
    merge=bm.merge(saved,on=PANEL,suffixes=('_replay','_saved'),validate='one_to_one')
    assert len(merge)==len(bm)==len(saved)
    e_batch=float(np.max(np.abs(merge.value_replay-merge.value_saved)));assert e_batch<1e-12
    sums=[]
    for vals,g in bm.groupby(SUMMARY,dropna=False,sort=True):
        sums.append(dict(zip(SUMMARY,vals),value=float(g.groupby('dataset').value.mean().mean()),datasets=g.dataset.nunique(),batches=len(g),fits=len(g)*5))
    summary=pd.DataFrame(sums);summary.to_csv(out/'arm_summary.csv',index=False)
    saved=pd.read_csv(base/'arm_summary.csv',keep_default_na=False)
    m=summary.merge(saved,on=SUMMARY,suffixes=('_replay','_saved'),validate='one_to_one');assert len(m)==len(summary)==len(saved)
    e_sum=float(np.max(np.abs(m.value_replay-m.value_saved)));assert e_sum<1e-12
    pairs=pd.read_csv(base/'paired_batches.csv',keep_default_na=False)
    # Rebuild ALL contrasts, including partial endpoint panels, from raw-run means.
    lookup={tuple(row[k] for k in PANEL):float(row['value']) for row in bm.to_dict('records')}
    for idx,t in pairs.iterrows():
        values=[]
        for side in ['left','right']:
            p={k:t[k] for k in ['dataset','batch','metric','population','omission','confidence','percentile']}
            p.update(arm=t[side],dimension=t[side+'_dimension'])
            values.append(lookup[tuple(p[k] for k in PANEL)])
        assert abs(values[0]-t.left_value)<1e-12 and abs(values[1]-t.right_value)<1e-12
        assert abs(values[0]-values[1]-t.difference)<1e-12
        pairs.loc[idx,'left_value']=values[0];pairs.loc[idx,'right_value']=values[1];pairs.loc[idx,'difference']=values[0]-values[1]
    paired=pd.read_csv(base/'paired_exact_bootstrap.csv',keep_default_na=False)
    dims=['left','right','left_dimension','right_dimension','metric','population','omission','confidence','percentile']
    ci=[];maxerr=0
    for r in paired.to_dict('records'):
        mask=np.ones(len(pairs),dtype=bool)
        for k in dims:mask &= pairs[k].values==r[k]
        g=pairs[mask];assert len(g)==r['batches']
        # Bind every paired value back to independently recomputed per-run means.
        panel={k:r[k] for k in ['metric','population','omission','confidence','percentile']}
        for t in g.to_dict('records'):
            recovered=[]
            for side in ['left','right']:
                mm=np.ones(len(bm),dtype=bool)
                for k,v in dict(panel,arm=r[side],dimension=r[side+'_dimension'],dataset=t['dataset'],batch=t['batch']).items():
                    mm &= bm[k].values==v
                matched=bm[mm];assert len(matched)==1
                recovered.append(float(matched.iloc[0].value))
            assert abs(recovered[0]-t['left_value'])<1e-12 and abs(recovered[1]-t['right_value'])<1e-12
            assert abs(recovered[0]-recovered[1]-t['difference'])<1e-12
        assert np.allclose(g.left_value-g.right_value,g.difference,atol=1e-14,rtol=0)
        groups={ds:t.difference.tolist() for ds,t in g.groupby('dataset',sort=True)}
        delta,lo,hi,n=interval(groups)
        err=max(abs(delta-r['delta']),abs(lo-r['lower']),abs(hi-r['upper']));maxerr=max(maxerr,err)
        assert err<1e-12 and n==r['bootstrap_draws']
        ci.append(dict(**{k:r[k] for k in dims},delta=delta,lower=lo,upper=hi,batches=len(g),datasets=len(groups),draws=n))
    assert len(ci)==222
    pd.DataFrame(ci).to_csv(out/'paired_exact_bootstrap.csv',index=False)
    # Explicitly retain endpoint-specific panels that the original complete-nine-batch gate excludes.
    extras=[]
    for vals,g in pairs.groupby(dims,dropna=False,sort=True):
        if g.empty:continue
        groups={ds:t.difference.tolist() for ds,t in g.groupby('dataset',sort=True)}
        delta,lo,hi,n=interval(groups)
        extras.append(dict(zip(dims,vals),delta=delta,lower=lo,upper=hi,datasets=len(groups),batches=len(g),draws=n,scope='endpoint-specific descriptive paired bootstrap; no multiplicity adjustment'))
    pd.DataFrame(extras).to_csv(out/'all_eligible_paired_intervals.csv',index=False)
    # Unknown summary independently from the all-record rows, retaining undefined endpoints.
    u=summary[summary.omission!='']; u.to_csv(out/'unknown_long_summary.csv',index=False)
    # Hash the exact artifacts replayed.
    hashes={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'evidence').rglob('*')) if p.is_file()}
    report=dict(status='PASS',ledger_unique=405,closed_label=315,unknown=90,neural=375,pca=30,new_metric_rows=12510,old_unique=450,old_metric_rows=15300,original_paired_intervals_replayed=222,all_endpoint_specific_intervals=len(extras),max_batch_error=e_batch,max_summary_error=e_sum,max_interval_error=maxerr,tolerance=1e-12,limitations=['saved-score numerical replay, not model inference or retraining','Model inference, embedding rescoring and training are separate from this saved-score replay.'],sha256=hashes)
    (out/'verification.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--output',type=Path);a=p.parse_args();replay(a.root,a.output)
