# Execution handoff — reviewer anchors

## Verified stage

No formal campaign training submitted. No new held-out results or manuscript integration claimed. response/acceptance_matrix.csv in the original solar-revision directory remains authoritative and unchanged; R2.1/R2.2 still pending.

Isolated checkout: /home/gzou/.hermes/cache/scratch/solar-reviewer-experiments
Branch: feat/reviewer-anchor-controls, base a0b8c6a.
Assets: /home/gzou/.hermes/cache/scratch/solar-reviewer-assets (outside git).

Original final-results ZIP downloaded through gh release, SHA256 verified bfab354c420ff7c9954d900c5ac385b1ed8a6c8b7bd1869e5ce6d18b7d096d57. Extracted at assets/extracted. All18 frozen split/feature files verified against45 original SOLAR30 records; see input_inventory.json. Release has378 evaluation records and no Gaussian/trainable results. Full archive/private execution history beyond released package was not available locally.

Original pancreas data retrieved, size315955785, SHA25697e6dfd65553e4d10aa3ef5d904362970a75c677c31d70fabc9234191a09db8c matches config. Immune/lung download running via download_data.py; read raw/raw_identity.json and download.log, not filenames alone.

## Actual smoke

Two-core CPU technical smoke only, real pancreas outer-reference-derived cells; no held-out batch query cells. D30 repeated model completed train/save and fresh-process reload plus independently reimplemented15NN vote/F1/recall checks. Output assets/smoke-repeated-v2/{training_complete,scoring_complete}.json. 70 technical inference cells, macroF1 0.8857531357531359, balanced accuracy0.9142857142857144. These are technical reference-validation numbers and must NOT enter manuscript performance tables. First foreground smoke was terminated by tool timeout before output; empty assets/smoke-repeated retained. v2 passed.

Remaining seven arm smokes are running sequentially in a transferable local process, proc_c888a8ad957b, PID730140. Output assets/smoke-{unique,none,gaussian,learnable,hierarchy,local,hierarchy_local}, per-arm .log and .score.log. They must all pass before full launch. Download process proc_d25173cc366f, PID730575. Parent should adopt these process handles with process_manage handoff completion. Not formal GPU jobs.

CPU Python: assets/smoke-env/bin/python (torch2.15 CPU, anndata0.13.4). This is a technical smoke environment only; paper numerical/source parity not claimed. Local host used two CPU threads, not a heavy CPU campaign.

## Resource blocker

Serial direct gateway/saigo1 and gateway-j/saigo2-j probes timed out before target login. Janus itself works; Janus->gateway also timed out. Thus Saigo GPU occupancy UNKNOWN. bw2-02 GPUs both occupied by PIDs3263162/3263158; do not co-use/kill. Janus GPU1 was free when inspected but existing instructions prohibit shared Janus cards unless owner names them. No platform changes, service shutdowns, agentbus/llmhub writes performed. Do not tell user GPU jobs are submitted.

A copy of code exists on Janus at /home/gzou/solar-reviewer-experiments (not git-managed); partial assets copy/download there should not be confused with the complete local authoritative file. Janus original Python: /home/gzou/SOLaR/SOLAR-fixed-orthogonal-label-anchors-for-single-cell-reference-mapping/environments/solar/.venv/bin/python, torch2.7.1cu126. GPU use not authorized by this handoff. Remove no originals.

## Finite entrypoints

PROTOCOL.md fixes reviewer controls and method extension BEFORE heldout scoring. Eight D30 arms + Gaussian/learnable D128,9 batches,5seeds =450 formal fits. This preserves full current-source matched baseline and component isolations. All arm names are independently output; no query-based selection. Hierarchy Gram0.5I+0.5G estimated only actual internal gradient-training cells; local KL weight0.1. Unknown rejection not implemented; scope route preserved.

run.py handles one formal key or --smoke; explicit dimension overrides prevent hardcoded128 variant leakage. It saves model/PCA/internal IDs/anchors/history/identity and finite dimensionality checks. score.py reopens model in new process and compares first32 reference embeddings, independently checks distance weights and per-label metrics. launch.py is a finite serial GPU worker with --shard/--shards; rejects currently occupied GPU and stops on a failed arm. readiness.py verifies all450 expected formal key statuses in one call. Official pinned scIB/local endpoint integration still needs implementation/execution; annotation scorer is NOT a replacement for paper endpoints.

Example remote command AFTER all smokes, full data verification, CUDA environment check, free GPU and source synchronization:

```sh
CUDA_DEVICE_ORDER=PCI_BUS_ID <gpu-python> experiments/reviewer_anchors/launch.py --bundle <assets>/extracted --data <assets>/raw --output <new-output> --gpu <physical-index> --shard 0 --shards <workers>
```

Launch using remote nohup/setsid with persistent logs; record actual PID/job handles. Saigo2 physical5090 requires PCI_BUS_ID and device1; print CUDA device and read back it actually loaded. Parent owns watcher lifecycle. Run readiness once per advance, not hours-long child sleeps.

## Still required

- All remaining smoke results and throughput; fix failures before formal jobs.
- Saigo recovery or owner-directed alternative compute; retrieve/verify immune/lung sources.
- Actual450 formal training keys, official scIB/local endpoints using pinned backend and cached inputs, all cell coverage and paired batch bootstrap; independently validate existing frozen scores where reused.
- Unknown rejection feasibility assessment (separate task); optional scope extension cannot hold reviewer-required controls hostage.
- Integrate actual favorable/unfavorable results into main/SI/response, update AI disclosure, finish original reviewer matrix. Rebuild/inspect final PDFs and standalone source ZIP.
- User requests draft PR once complete; no draft PR opened prematurely. Push branch for persistent collaborative code. Never main/merge/force-push. No interim artifact delivery.
