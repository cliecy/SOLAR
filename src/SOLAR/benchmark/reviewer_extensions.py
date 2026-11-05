"""Reference-derived hierarchy and local objectives used in the 450-fit campaign.

Extracted without changing the computation. Call once per fresh process before
run_inductive; output is a Path for initial anchors and components is a list.
The extension modifies SOLAR.api.run_epochs for that process.
"""
import numpy as np
import torch
import torch.nn.functional as F
import SOLAR.api as api

def install_extension(arm, output, components):
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
