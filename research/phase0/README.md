# NagorikSafe Phase 0

Phase 0 freezes the reproducible five-class NID starting point. Read
`PHASE0_REPRODUCIBILITY_FREEZE.md` first.

- Protocol: `NID-5CLASS-PHASE0-V1`
- Protocol artifacts: this directory
- Baseline results: `results/`
- Artifact ledger: `phase0_artifact_manifest.csv`
- Verification: `verify_phase0_freeze.py`

Run verification from the repository root:

```bat
"D:\Files\Academic\4-1\NLP\nlp\Scripts\python.exe" research\phase0\verify_phase0_freeze.py
```

The raw source is private and stored outside Git in the sibling
`NLP_Project-_private` directory. The remembered 96.36% IID and 82.64% shifted
Macro-F1 values remain unverified historical references.
