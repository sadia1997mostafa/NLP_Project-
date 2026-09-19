# Privacy regression corpus

`privacy_cases.jsonl` is a synthetic, non-secret regression set for the
rule-based privacy masker. It covers labelled government identifiers, generic
identifiers, contact details, credentials, explicit personal fields, Bangla
digits, English, Bangla and Banglish variants. Negative cases protect ordinary
fees, years, emergency numbers and service questions from over-masking.

Each row records the exact protected text and ordered privacy types expected at
the API boundary. Add a positive and a nearby negative case whenever a rule is
extended. The corpus evaluates deterministic masking; it is not answer-model or
Partner A classifier training data and must never contain real personal data.

Run:

```powershell
python -m unittest tests.test_privacy_detection
```

Pattern matching cannot guarantee detection of every free-form personal fact.
The UI and documentation must continue to tell users not to submit unnecessary
sensitive information.
