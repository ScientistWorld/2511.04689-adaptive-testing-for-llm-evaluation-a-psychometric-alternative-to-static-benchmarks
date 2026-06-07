# Verification Report

## Initial Assessment

The workspace started at `core_claim_plus` with a completed ATLAS reproduction on five benchmark response matrices. The implementation runs the paper's adaptive testing algorithm, the evaluator reads method artifacts rather than rerunning the method, and the existing scores demonstrate the core reduced-item ability-estimation claim plus additional benchmark coverage.

## Issues Found

- Minor: Public experiment IDs and target headings used `adaptive`, and `briefing/evaluation.md` described the fixed baseline as `non-adaptive`. Those terms exposed part of the paper's solution in files intended to be method-agnostic for from-scratch agents.
- Minor: `scoring/DIRECTION.md` named adaptive item selection directly. The allowed direction should describe reduced-item psychometric evaluation without prescribing the paper's mechanism.

No critical issues were found. The evaluator is independent of `method/`, the download script has a verified public URL, and scored metrics include both benefit and constraint quantities.

## Fixes Applied

- Renamed scored experiments from `*_adaptive_ability` to `*_reduced_item_ability` across `reference.json`, `scores.json`, train/test score files, evaluator code, and scoring documentation.
- Reworded the method-agnostic evaluation and direction documents to use neutral reduced-item terminology.
- Regenerated `scoring/scores.json`, `scoring/scores_train.json`, and `scoring/scores_test.json` from the existing method and baseline artifacts.
- Verified `scripts/download.sh` URL resolution with `curl -I -L --max-time 15`; the GitHub URL redirects to a raw ZIP with HTTP 200.
- Ran `python validate.py --compare`, `bash -n scripts/*.sh`, and Python bytecode compilation for the method, baseline, and evaluator code.

## Final Judgment

The workspace is ready to serve as a research gym. From-scratch agents can use the problem, data, scoring docs, and evaluation files without being shown the solution mechanics. Improve-mode agents have a working ATLAS implementation and meaningful baseline scores to beat. The scoring captures both benefit metrics and constraints: ability error, item count, information efficiency, accuracy preservation, item overlap, and exposure.

- Milestone: core_claim_plus
- Ready for gym use: yes
- Confidence: high
- Key limitation: reproduction uses a bounded 750-model slice per benchmark because larger CPU-only reruns exceeded the observed scheduler window.
