#!/usr/bin/env python3
"""Finite single-GPU launcher; no waiting loop and no concurrent GPU sharing."""
from pathlib import Path
import argparse,subprocess,os,json,sys,time
p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--data',required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--gpu',required=True);p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=1);a=p.parse_args()
root=Path(__file__).resolve().parent
jobs=[]
for ds,batches in {'pancreas':['fluidigmc1','inDrop2','inDrop3'],'immune_cell_human':['10X','Oetjen_A','Villani'],'lung_atlas':['3','4','B1']}.items():
 for b in batches:
  for seed in range(40,45):
   for arm in ['repeated','unique','none','gaussian','learnable','hierarchy','local','hierarchy_local']:
    jobs.append((ds,b,seed,30,arm))
   for arm in ['gaussian','learnable']: jobs.append((ds,b,seed,128,arm))
assert len(jobs)==450
selected=jobs[a.shard::a.shards]
a.output.mkdir(parents=True,exist_ok=True)
env={**os.environ,'CUDA_DEVICE_ORDER':'PCI_BUS_ID','CUDA_VISIBLE_DEVICES':a.gpu,'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2'}
def save(x): (a.output/f'shard_{a.shard}_status.json').write_text(json.dumps(x,indent=2)+'\n')
# Query by physical device index; reject any existing compute app, regardless owner.
probe=subprocess.run(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],capture_output=True,text=True,check=True)
if probe.stdout.strip():
 save({'state':'blocked_gpu_occupied','pids':probe.stdout.strip(),'time':time.time()});sys.exit(75)
for ds,b,seed,dim,arm in selected:
 key=f'{arm}__d{dim}__{ds}__{b}__s{seed}';out=a.output/key
 if (out/'scoring_complete.json').exists():
  status=json.loads((out/'scoring_complete.json').read_text())
  if status['state']=='completed': continue
 save({'state':'running','key':key,'time':time.time(),'pid':os.getpid(),'total_shard':len(selected)})
 if not (out/'training_complete.json').exists():
  if out.exists(): raise RuntimeError('Incomplete previous output requires explicit investigation: '+str(out))
  cmd=[sys.executable,str(root/'run.py'),'--bundle',a.bundle,'--data',a.data,'--output',str(out),'--dataset',ds,'--batch',b,'--arm',arm,'--seed',str(seed),'--dimension',str(dim)]
  with (a.output/(key+'.log')).open('w') as log: code=subprocess.call(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if code: save({'state':'failed','stage':'training','key':key,'exit':code,'time':time.time()});sys.exit(code)
 with (a.output/(key+'.score.log')).open('w') as log: code=subprocess.call([sys.executable,str(root/'score.py'),str(out)],env=env,stdout=log,stderr=subprocess.STDOUT)
 if code: save({'state':'failed','stage':'annotation_scoring','key':key,'exit':code,'time':time.time()});sys.exit(code)
save({'state':'annotation_complete_official_scib_pending','time':time.time(),'total_shard':len(selected)})
