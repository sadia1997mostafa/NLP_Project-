# Phase 0 Reproducibility Freeze

## 1. Phase objective

Phase 0 establishes a small, auditable, reproducible starting point for the
NagorikSafe NID robustness research. It freezes the recovered source identity,
five-label ontology, minimal preprocessing, leakage-safe IID split, evaluation
contract, and first reproducible classical baseline.

## 2. Historical evidence status

The 1,454-row source and its five coarse labels were recovered and frozen. The
remembered 96.36% IID Macro-F1 and 82.64% shifted Macro-F1 were not independently
reproducible: their historical split, preprocessing, model/checkpoint,
predictions, and shifted evaluation set were unavailable. The remembered
13.72-point gap is therefore an unverified historical reference, not a result
of the canonical protocol.

## 3. Canonical Phase 0 protocol

`NID-5CLASS-PHASE0-V1` contains 1,454 rows and five labels: NID Information
Correction (267), New NID Registration (448), Lost/Stolen NID (236), NID Online
Problem (305), and Smart ID Card (198).

Preprocessing converts input to string, applies Unicode NFC, collapses
consecutive whitespace, and strips outer whitespace. It does not lowercase,
transliterate, delete punctuation/numbers, stem, remove stopwords, or augment.

The deterministic seed-42 split groups identical normalized-text hashes so an
exact duplicate group cannot cross splits. Counts are TRAIN 1,017, DEV 219,
and TEST 218; cross-split normalized-text overlap is zero.

- Source raw SHA-256: `6de6ba4f342602b99254b97ad830161405baf817eb38cadee2a56980fc5e7faa`
- Canonical content SHA-256: `156d0a6a5f1f15773cc2adf286fc7e9f1c7d5f68fe8f332757a7435bc0c68811`
- Split manifest SHA-256: `4d6356191e1813e9f1ec6345614d2e0a003d134a26521bc7a702ce8a72ef11f1`

## 4. Baseline

`TFIDF-LOGREG-V1` (`EXP-P0-BASELINE-001`) fits word unigram/bigram TF-IDF and
balanced logistic regression on TRAIN only. DEV and TEST are transform-only;
TEST was evaluated once.

| Split | Accuracy | Macro precision | Macro recall | Macro-F1 |
|---|---:|---:|---:|---:|
| DEV | 93.6073% | 94.1029% | 93.5876% | **93.7334%** |
| TEST | 92.2018% | 91.8029% | 92.4760% | **92.0171%** |

This is the first reproducible baseline under the canonical protocol, not a
reconstruction of the historical 96.36% result.

## 5. Error observations

DEV contains 14 errors and TEST contains 17. The largest DEV confusion is
Lost/Stolen NID to NID Information Correction (3). The largest TEST confusion
is New NID Registration to Lost/Stolen NID (4), followed by Lost/Stolen NID to
NID Information Correction (3). Two normalized duplicate groups carry
conflicting labels; each remains wholly within one split and was not repaired.

## 6. Privacy / source-quality notes

The conservative heuristic scan found zero NID-number-like, phone-like,
email-like, passport-like, or clear DOB-identifier matches. This does not prove
that free-form text is free of sensitive content.

Two unnamed trailing columns are populated in the same 17 rows. Aggregate
inspection found ASCII alphabetic text and no numeric-only or identifier-like
pattern. They are unused by query/label selection, split assignment features,
and baseline model input, but require owner review before public release. The
raw source remains private in the sibling `NLP_Project-_private` directory and
outside Git.

## 7. Reproducibility commands

A. Freeze/data utility help and protocol regeneration options:

```bat
"D:\Files\Academic\4-1\NLP\nlp\Scripts\python.exe" research\phase0\freeze_nid_5class.py --help
```

B. Verify the complete frozen Phase 0 state without model execution:

```bat
"D:\Files\Academic\4-1\NLP\nlp\Scripts\python.exe" research\phase0\verify_phase0_freeze.py
```

C. **Use only when intentionally reproducing the experiment:**

```bat
"D:\Files\Academic\4-1\NLP\nlp\Scripts\python.exe" research\phase0\run_nid_5class_baseline.py
```

The baseline reproduction command was not executed during Phase 0 closure.

## 8. Artifact inventory

The authoritative ledger is `research/phase0/phase0_artifact_manifest.csv`.
It records path, size, SHA-256, provenance task, Git status, and content-safety
metadata. The ledger omits its own recursive hash and lists the source as an
external private artifact.

## 9. What Phase 0 established

Phase 0 scientifically freezes source identity, raw and canonical hashes,
label IDs/counts, minimal normalization, exact-duplicate grouping, deterministic
IID membership, evaluation rules, fixed baseline configuration, official
DEV/TEST outputs, and aggregate errors. These artifacts are independently
checkable without stored model binaries.

## 10. What Phase 0 did NOT establish

Phase 0 did not reproduce either historical score, recover a valid shifted
benchmark, compare Transformers, test cross-script robustness, calibrate or
apply conformal methods, run a privacy-masking experiment, or transfer the
method to Birth Registration.

## 11. Phase 1 entry conditions

Phase 1 may begin because the canonical source, labels, preprocessing, split,
baseline, fixed TEST result, and verification artifacts exist. Phase 1 must
construct new leakage-resistant challenge sets rather than reverse-engineering
the missing historical 82.64% dataset.

## 12. Phase 0 closure

**COMPLETE WITH DOCUMENTED HISTORICAL LIMITATION**
