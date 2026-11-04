#!/usr/bin/env python3
"""Finite matched SOLAR experiment; smoke evaluates reference validation only."""
from pathlib import Path
import argparse, copy, hashlib, json, os, sys, time
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import f1_score, balanced_accuracy_score
from SOLAR import SOLARModel
from SOLAR.benchmark import variants
from SOLAR.benchmark.adapter import TrainConfig, PreprocessConfig, run_inductive
from scib_benchmark.solar_adapter import register_orthogonal_uniq
from scib_benchmark.data import read_split, read_gene_list, load_reference_query
import SOLAR.api as api

ARMS = ['repeated','unique','none','gaussian','learnable','hierarchy','local','hierarchy_local']
def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')

def install_extension(arm):
    original=api.run_epochs
    def extended(model, device, criterion, optimizer, train_loader, val_loader, *args, **kwargs):
        if arm in ('hierarchy','hierarchy_local'):
            # Dataset indices are the actual seeded DataLoader partition.
            ds=train_loader.dataset
            items=[ds[i] for i in range(len(ds))]
            names=sorted(model.anchor_encoder.class_to_idx,key=model.anchor_encoder.class_to_idx.get)
            centers=[]
            for name in names:
                values=[torch.as_tensor(x[0],dtype=torch.float32) for x in items if str(x[2])==name]
                if not values: raise ValueError('Missing internal-train class '+name)
                centers.append(torch.stack(values).mean(0))
            c=F.normalize(torch.stack(centers),dim=1)
            gram=.5*torch.eye(len(c))+.5*c@c.T
            eigen,u=torch.linalg.eigh(gram)
            a=u@torch.diag(eigen.clamp_min(0).sqrt())
            a=F.pad(a,(0,model.embedding_dim-len(c))).to(device)
            model.anchor_encoder.anchors.copy_(a)
        np.save(output/'initial_anchors.npy',model.encode_text(names if arm in ('hierarchy','hierarchy_local') else sorted(model.anchor_encoder.class_to_idx)).detach().cpu().numpy()) if model.has_text_branch else None
        if arm in ('local','hierarchy_local'):
            base_forward=model.forward
            cache={}
            def forward(expressions,text_anchors,device=None):
                z,t=base_forward(expressions,text_anchors,device)
                cache.update(x=expressions,z=z,labels=text_anchors)
                return z,t
            model.forward=forward
            base_criterion=criterion
            class Objective(torch.nn.Module):
                def forward(self,features,labels):
                    primary=base_criterion(features,labels=labels)
                    x,z,names=cache['x'],cache['z'],cache['labels']
                    terms=[]
                    for name in set(names):
                        idx=[i for i,n in enumerate(names) if n==name]
                        if len(idx)<3: continue
                        xx=x[idx];zz=z[idx]
                        d=torch.cdist(xx,xx).square().detach()
                        d.fill_diagonal_(float('inf'))
                        dd,nn=d.topk(min(15,len(idx)-1),largest=False)
                        scale=dd.median().clamp_min(1e-8)
                        target=torch.softmax(-dd/scale,dim=1)
                        distance=(1-(zz[:,None,:]*zz[nn]).sum(-1))
                        terms.append(F.kl_div(F.log_softmax(-distance/.07,dim=1),target,reduction='batchmean'))
                    local=torch.stack(terms).mean() if terms else primary*0
                    components.append({'training':bool(model.training),'supcon':float(primary.detach()),'local':float(local.detach())})
                    return primary+.1*local
            criterion=Objective()
        result=original(model,device,criterion,optimizer,train_loader,val_loader,*args,**kwargs)
        return result
    api.run_epochs=extended

p=argparse.ArgumentParser()
p.add_argument('--bundle',type=Path,required=True);p.add_argument('--data',type=Path,required=True)
p.add_argument('--output',type=Path,required=True);p.add_argument('--dataset',required=True)
p.add_argument('--batch',required=True);p.add_argument('--arm',choices=ARMS,required=True)
p.add_argument('--seed',type=int,required=True);p.add_argument('--dimension',type=int,choices=[30,128],default=30)
p.add_argument('--device',default='cuda');p.add_argument('--smoke',action='store_true')
a=p.parse_args();output=a.output
output.mkdir(parents=True,exist_ok=False)
components=[];started=time.time()
try:
 import yaml
 manifest=yaml.safe_load((ROOT/'configs/scib_datasets.yaml').read_text())['datasets'][a.dataset]
 data=a.data/manifest['filename'];assert sha(data)==manifest['checksum_sha256']
 base=a.bundle
 records=json.loads((base/'provenance/execution_manifest.json').read_text())['runs']
 record=next(r for r in records if r['dataset_id']==a.dataset and str(r['heldout_batch'])==a.batch and r['seed']==a.seed and r['training_method']=='solar30')
 split_path=base/record['split_path'];gene_path=base/record['features_path']
 assert sha(split_path)==record['split_sha256'] and sha(gene_path)==record['features_sha256']
 split=read_split(split_path)
 if a.smoke:
  # Retain no held-out query cells: carve a technical inference set from reference.
  ref=split[split.role=='reference'].groupby('label',group_keys=False).head(60).copy()
  ref['role']='reference';ref.loc[ref.groupby('label').tail(5).index,'role']='query'
  split=ref.reset_index(drop=True)
 reference,query=load_reference_query(data,split,read_gene_list(gene_path))
 # Model-facing query labels are removed inside run_inductive.
 register_orthogonal_uniq(variants)
 name={'repeated':'solar_orthogonal','unique':'solar_orthogonal_uniq','none':'solar_none','gaussian':'solar_geometry_gaussian','learnable':'solar_trainable'}.get(a.arm,'solar_orthogonal')
 spec=variants.VARIANTS[name]
 params=copy.deepcopy(spec.model_kwargs);params['embedding_dim']=a.dimension
 from dataclasses import replace
 variants.VARIANTS[name]=replace(spec,model_kwargs=params)
 install_extension(a.arm)
 torch.set_num_threads(2)
 torch.manual_seed(a.seed)
 if a.device=='cuda':
  assert torch.cuda.is_available()
  print('CUDA_DEVICE',torch.cuda.get_device_name(0),flush=True)
 result=run_inductive(reference,query,name,labels_key=manifest['label_key'],batch_key=manifest['batch_key'],seed=a.seed,anchor_seed=0,preprocess=PreprocessConfig(n_components=40),train=TrainConfig(embedding_dim=a.dimension,max_epochs=2 if a.smoke else 50),device=a.device)
 assert result.reference_embedding.shape==(len(reference),a.dimension)
 assert result.query_embedding.shape==(len(query),a.dimension)
 assert np.isfinite(result.reference_embedding).all() and np.isfinite(result.query_embedding).all()
 result.save(output,save_model=True)
 split.to_csv(output/'outer_split.csv',index=False)
 dump(output/'components.json',components)
 dump(output/'identity.json',{'args':vars(a)|{'bundle':str(a.bundle),'data':str(a.data),'output':str(a.output)},'dataset_sha256':sha(data),'split_sha256':sha(split_path),'features_sha256':sha(gene_path),'source_sha256':sha(__file__),'host':os.uname().nodename,'seconds':time.time()-started,'scope':'reference_only_technical_smoke' if a.smoke else 'formal_heldout_batch'})
 # Save deterministic model-facing input for independent new-process reload.
 from scipy import sparse
 x=reference.X.toarray() if sparse.issparse(reference.X) else reference.X
 np.savez_compressed(output/'reload_input.npz',x=x[:32],barcodes=reference.obs_names.to_numpy(dtype=str)[:32],var_names=reference.var_names.to_numpy(dtype=str),expected=result.reference_embedding[:32])
 dump(output/'training_complete.json',{'state':'completed','seconds':time.time()-started,'dimension':a.dimension,'n_reference':len(reference),'n_query':len(query),'smoke':a.smoke})
 print('TRAINING_COMPLETE',output,flush=True)
except Exception as e:
 dump(output/'failed.json',{'error':repr(e),'seconds':time.time()-started})
 raise
