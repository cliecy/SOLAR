#!/usr/bin/env python3
"""Resume original raw assets and verify authoritative SHA256 identities."""
import argparse,json,subprocess,hashlib
from pathlib import Path
import yaml
p=argparse.ArgumentParser();p.add_argument('destination',type=Path);a=p.parse_args();a.destination.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[2]
results={}
for key,item in yaml.safe_load((root/'configs/scib_datasets.yaml').read_text())['datasets'].items():
 target=a.destination/item['filename']
 def digest():
  with target.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
 if target.exists() and target.stat().st_size==item['expected_size_bytes']:
  assert digest()==item['checksum_sha256'];results[key]='verified_existing';continue
 code=subprocess.call(['curl','-fL','-C','-','--retry','3','--connect-timeout','20','--max-time','3600',item['file_url'],'-o',str(target)])
 if code: raise RuntimeError(f'{key} download exit{code}')
 assert target.stat().st_size==item['expected_size_bytes'] and digest()==item['checksum_sha256']
 results[key]='downloaded_verified'
 (a.destination/'raw_identity.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
