# Four controlled follow-up experiments

All405 new records are complete:315closed-label and90whole-type-out records, comprising375 neural fits and30PCA preprocessing fits. They add12510 metric rows. The original450 runs remain separate immutable comparators; selected-arm aliases do not count as extra training. Five seeds40–44 average within batch, then batches within dataset and datasets equally. Intervals are descriptive95% exhaustive paired batch bootstrap without multiplicity correction. The benchmark was previously exposed; no query-driven threshold tuning was used.

## Matched128 anchor geometry

| Anchor128 | Query macro-F1 | Joint label ASW |
|---|---:|---:|
| Repeated orthogonal | .812396 | .869076 |
| Unique orthogonal | .813036 | .844354 |
| Gaussian | .811270 | .868465 |
| Learnable | .807721 | .864098 |

Nine batches, five seeds each. Repeated minus Gaussian F1 is+.001125[−.000902,+.003366]; repeated minus learnable is+.004675[−.002591,+.010428]. Unique minus repeated is+.000640[−.004631,+.005203]. Annotation gains are not established. Unique minus repeated label ASW is−.024722[−.025704,−.023655], demonstrating that geometry and annotation effects differ.

## SCLSC best checkpoint and PCA40 input

The minimum-reference-validation-loss state is restored, with pinned upstream architecture/objective retained. Gene and PCA40 inputs are distinct configurations, each45new fits. These changes align checkpoint selection and one input representation without making the architectures or objectives identical.

| Method | Query F1 | Balanced accuracy | Joint label ASW | Query trustworthiness | Joint pseudotime smoothness |
|---|---:|---:|---:|---:|---:|
| SOLAR repeated30 | .811108 | .837411 | .873408 | .936415 | .860418 |
| SCLSC best genes | .786269 | .847187 | .946182 | .902886 | .811229 |
| SCLSC best PCA40 | .786689 | .844263 | .889896 | .921375 | .846808 |

SCLSC minus SOLAR F1: genes−.024840[−.052501,+.004906], PCA40−.024419[−.068015,+.021333]. Label ASW: genes+.072775[+.069084,+.076386], PCA40+.016489[+.013392,+.019564]. Balanced-accuracy point estimates favor SCLSC, while intervals cross zero. Query trustworthiness differences are−.033529[−.041603,−.025394] and−.015040[−.020607,−.009473]. Joint smoothness differences are−.049189[−.053446,−.044915] and−.013609[−.020275,−.005689]. Annotation/ASW cover nine batches, trustworthiness six from two datasets, smoothness three from one dataset. Query smoothness has only one eligible batch and cannot establish cross-batch reliability.

## Unique anchors and local regularization

| Arm30 | Query F1 | Joint ASW | Joint trustworthiness | Query trustworthiness |
|---|---:|---:|---:|---:|
| repeated | .811108 | .873408 | .912417 | .936415 |
| unique | .811308 | .860054 | .926909 | .939541 |
| unique+local0.1 | .809989 | .858757 | .931722 | .940191 |
| repeated+local0.03 | .811274 | .873045 | .914836 | .936510 |
| repeated+local0.1 | .809937 | .870791 | .920466 | .937349 |
| repeated+local0.3 | .809946 | .867454 | .931459 | .939189 |

Unique+local minus unique trustworthiness: joint+.004813[+.003825,+.005932], reference+.005477[+.004128,+.006606], query+.000650[+.000412,+.001032]. The larger joint/reference gains must not be described as comprehensive query repair. F1 difference−.001319[−.003667,+.000951] does not establish annotation improvement; ASW difference−.001297[−.001778,−.000870] shows the separation cost. Against repeated+local0.1, unique+local joint/query trust gains are+.011255[+.007885,+.013571] and+.002842[+.001497,+.004368], while F1 difference+.000052[−.003185,+.003019] crosses zero. Unique+local minus unique joint smoothness is+.006402[+.003869,+.009208] across three batches; query+.001889 is one-batch descriptive only. Larger repeated local weights improve trustworthiness point estimates while reducing separation and providing no established annotation gain. All weights remain reported.

## Whole-type-out rejection

B-cell omission deletes the union of CD10+ and CD20+ B labels; CD16 omits exact CD16+ Monocytes. Omitted reference cells are removed before HVG selection/PCA/internal splitting. All held-out query cells remain. Training-only neighbors and disjoint reference-validation quantiles1/5/10% prevent query threshold tuning. Native classifiers use maximum training-anchor cosine (SOLAR) or maximum class probability (scANVI); common distance uses distance-weighted15NN. They are separate confidence/classification families.

B-cell unknown counts:1546/134/0 across10X/Oetjen_A/Villani. Unknown recall/AUROC therefore cover two batches, known endpoints three. CD16 counts364/61/172, covering three. Undefined outcomes remain undefined.

At the reference-validation5% quantile:

| Omission | Method/score | AUROC | Unknown recall | Known F1 | Known false rejection |
|---|---|---:|---:|---:|---:|
| B | SOLAR common distance | .955066 | .909407 | .545018 | .378563 |
| B | scANVI common distance | .961088 | .375066 | .545180 | .350285 |
| B | PCA common distance | .601047 | .111951 | .492406 | .360494 |
| B | SOLAR native cosine | .867063 | .534912 | .681621 | .192849 |
| B | scANVI native probability | .925676 | .604265 | .780798 | .064335 |
| CD16 | SOLAR common distance | .455346 | .176862 | .552660 | .307275 |
| CD16 | scANVI common distance | .838202 | .887164 | .493416 | .372862 |
| CD16 | PCA common distance | .940989 | .996349 | .424195 | .431325 |
| CD16 | SOLAR native cosine | .451856 | .031468 | .729384 | .125407 |
| CD16 | scANVI native probability | .613194 | .101318 | .787237 | .050902 |

Known F1 counts rejected known cells as errors; AUROC is unknown-positive using negative confidence. A5% reference quantile does not guarantee5% query false rejection. B-cell common-distance discrimination is strong for SOLAR and scANVI, but thresholds transfer differently. SOLAR performs poorly on CD16; common-distance SOLAR minus scANVI AUROC is−.382855[−.532872,−.266248] and recall−.710302[−.799281,−.636979]. PCA CD16 near-perfect recall accompanies43.13% known rejection. Native SOLAR confidence does not establish a general rejection advantage. All1/5/10% results remain in the CSVs.

## Reproduction and statistical coverage

[The self-contained companion](../experiments/four405/README.md) independently rebuilds all405 saved-record summaries and checks original222 complete-panel intervals at1e-12. The original aggregator restricted intervals to complete nine-batch panels, so local six-batch and B-unknown two-batch intervals were absent. `all_eligible_paired_intervals.csv` reconstructs420 endpoint-specific contrasts from per-run values without imputing absent biology. Single-batch pseudotime intervals are degenerate and descriptive only. Historical450 reconstruction separately checks464 intervals,45selection groups and every complete table.

These are saved-score numerical reconstructions. The compact bundle does not execute model inference, official embedding rescoring or training; it does not contain raw expression or per-cell confidence arrays. This scope is distinct from the earlier independent90run/1800endpoint unknown audit.
