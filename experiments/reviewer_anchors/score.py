#!/usr/bin/env python3
"""New-process reload + independently checked distance-weighted15NN scoring."""
from pathlib import Path
import sys,json,argparse
import numpy as np,pandas as pd,anndata as ad
from scipy import sparse
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import f1_score,balanced_accuracy_score
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from SOLAR import SOLARModel
p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();r=a.run
status=json.loads((r/'training_complete.json').read_text())
z=np.load(r/'reload_input.npz',allow_pickle=False)
model=SOLARModel.load(r/'model',device='cpu')
x=ad.AnnData(X=z['x'],obs=pd.DataFrame(index=z['barcodes']),var=pd.DataFrame(index=z['var_names']))
pca=np.load(r/'pca_preprocessor.npz')
xx=(x.X-pca['mean'])@pca['components'].T
xr=ad.AnnData(X=np.asarray(xx,dtype=np.float32),obs=x.obs.copy())
pred=model.transform(xr)
np.testing.assert_allclose(pred,z['expected'],rtol=1e-4,atol=1e-5)
split=pd.read_csv(r/'outer_split.csv',dtype=str);e=np.load(r/'embedding.npz',allow_pickle=False)
ref=split[split.role=='reference'];q=split[split.role=='query']
assert np.array_equal(ref.barcode.to_numpy(),e['reference_barcodes'])
assert np.array_equal(q.barcode.to_numpy(),e['query_barcodes'])
k=KNeighborsClassifier(n_neighbors=15,weights='distance',n_jobs=1).fit(e['reference'],ref.label)
actual=k.predict(e['query']);d,idx=k.kneighbors(e['query']);classes=k.classes_
manual=[]
for dist,indices in zip(d,idx):
 weights=(dist==0).astype(float) if (dist==0).any() else 1/dist
 labels=ref.label.to_numpy()[indices]
 totals=np.array([weights[labels==label].sum() for label in classes])
 manual.append(classes[totals.argmax()])
assert np.array_equal(actual,manual)
truth=q.label.to_numpy();labels=np.unique(truth)
per=[]
for label in labels:
 tp=int(((actual==label)&(truth==label)).sum());fp=int(((actual==label)&(truth!=label)).sum());fn=int(((actual!=label)&(truth==label)).sum())
 per.append({'label':label,'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,'recall':tp/(tp+fn)})
f1=float(f1_score(truth,actual,labels=labels,average='macro',zero_division=0));ba=float(balanced_accuracy_score(truth,actual))
assert abs(f1-np.mean([v['f1'] for v in per]))<1e-12
assert abs(ba-np.mean([v['recall'] for v in per]))<1e-12
pd.DataFrame({'barcode':q.barcode,'truth':truth,'prediction':actual}).to_csv(r/'predictions.csv',index=False)
report={'state':'completed','scope':'reference_only_technical_smoke' if status['smoke'] else 'formal_heldout_batch','macro_f1':f1,'balanced_accuracy':ba,'n_query':len(q),'independent_neighbor_vote_agrees':True,'independent_confusion_metrics_agree':True,'new_process_reload_agrees':True,'per_label':per}
(r/'scoring_complete.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
