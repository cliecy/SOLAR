#!/usr/bin/env python3
"""One readiness check; verify full campaign without a long-lived watcher."""
import argparse,json,itertools
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('output',type=Path);a=p.parse_args()
missing=[];failed=[];complete=[]
for ds,bs in {'pancreas':['fluidigmc1','inDrop2','inDrop3'],'immune_cell_human':['10X','Oetjen_A','Villani'],'lung_atlas':['3','4','B1']}.items():
 for b,seed in itertools.product(bs,range(40,45)):
  pairs=[(30,arm) for arm in ['repeated','unique','none','gaussian','learnable','hierarchy','local','hierarchy_local']]+[(128,arm) for arm in ['gaussian','learnable']]
  for dim,arm in pairs:
   key=f'{arm}__d{dim}__{ds}__{b}__s{seed}';r=a.output/key
   if (r/'failed.json').exists(): failed.append(key);continue
   if not (r/'training_complete.json').exists() or not (r/'scoring_complete.json').exists(): missing.append(key);continue
   tr=json.loads((r/'training_complete.json').read_text());sc=json.loads((r/'scoring_complete.json').read_text())
   if tr['state']!='completed' or tr['smoke'] or sc['scope']!='formal_heldout_batch' or not all(sc[k] for k in ['new_process_reload_agrees','independent_neighbor_vote_agrees','independent_confusion_metrics_agree']):failed.append(key)
   else:complete.append(key)
assert len(missing)+len(failed)+len(complete)==450
report={'required':450,'annotation_complete':len(complete),'failed':failed,'missing':missing,'official_scib':'pending_independent_backend_execution','manuscript_integrated':False}
a.output.mkdir(parents=True,exist_ok=True);(a.output/'readiness.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'required':450,'annotation_complete':len(complete),'failed':len(failed),'missing':len(missing)}))
raise SystemExit(0 if len(complete)==450 else 2)
