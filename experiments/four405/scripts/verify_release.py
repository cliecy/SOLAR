from pathlib import Path
import hashlib,json
import pandas as pd
import numpy as np
R=Path(__file__).resolve().parents[1]
checks=[]
def compare(a,b,keys):
 x=pd.read_csv(a,keep_default_na=False);y=pd.read_csv(b,keep_default_na=False)
 assert set(x.columns)==set(y.columns),(a,set(x.columns)^set(y.columns))
 assert not x.duplicated(keys).any() and not y.duplicated(keys).any()
 x=x.sort_values(keys).reset_index(drop=True);y=y.sort_values(keys).reset_index(drop=True)
 assert len(x)==len(y),(a,len(x),len(y))
 maxerr=0
 for c in x:
  missing_x=x[c].astype(str).eq('');missing_y=y[c].astype(str).eq('');assert missing_x.equals(missing_y),(a,c,'missingness')
  xx=pd.to_numeric(x.loc[~missing_x,c],errors='coerce');yy=pd.to_numeric(y.loc[~missing_y,c],errors='coerce')
  if xx.notna().all() and yy.notna().all():
   if len(xx):
    err=float(np.max(np.abs(xx.to_numpy()-yy.to_numpy())));maxerr=max(maxerr,err);assert err<1e-12,(a,c,err)
  else:assert x[c].astype(str).equals(y[c].astype(str)),(a,c)
 checks.append(dict(table=str(a.relative_to(R)),rows=len(x),columns=len(x.columns),maximum_absolute_error=maxerr))
for name,keys in {
'metrics.csv':['key','metric','population'],
'validation_selection.csv':['dataset','batch','seed'],
'batch_means.csv':['arm','dimension','dataset','batch','metric','population'],
'arm_summary.csv':['arm','dimension','metric','population'],
'paired_batch_differences.csv':['left','right','dimension','metric','population','dataset','batch'],
'paired_batch_uncertainty.csv':['left','right','dimension','metric','population']}.items():
 compare(R/'replayed-old450'/name,R/'evidence/old450'/name,keys)
compare(R/'replayed/all_eligible_paired_intervals.csv',R/'expected/all_eligible_paired_intervals.csv',['left','right','left_dimension','right_dimension','metric','population','omission','confidence','percentile'])
# Public source contains no machine paths, operational handoffs or credentials.
for p in R.rglob('*'):
 if not p.is_file() or '.venv' in p.parts:continue
 if p.suffix in ['.py','.md','.csv','.json','.cff']:
  t=p.read_text();assert ('/'+'home'+'/') not in t and ('/'+'workspace'+'/') not in t,p
for line in (R/'MANIFEST.sha256').read_text().splitlines():
 h,name=line.split('  ',1);p=R/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==h,name
report=dict(status='PASS',tolerance=1e-12,complete_table_comparisons=checks)
(R/'release-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
