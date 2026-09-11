# Tax Semantic Taxonomy Audit

Service: `TAX`

Result: `PASS_WITH_PILOT_REVIEW_FLAGS`

## Parent review

The six parents separate taxpayer identity/TIN lifecycle, return filing,
online-account access, payment/ledger, status/documents and general support.
This is a citizen-intent hierarchy rather than a copy of portal navigation.

## High-risk boundaries

- TIN eligibility asks whether taxpayer registration applies; return
  obligation asks whether a return must be filed.
- Online e-TIN registration creates a taxpayer identity; e-Return account
  registration creates access to the filing service.
- Return process is general; online submission explicitly concerns the
  electronic workflow.
- Payment amount/calculation, method, confirmation, failure and ledger update
  are distinct requested outcomes.
- Return verification checks a filed record; acknowledgement proves
  submission; return-copy access retrieves the submitted document.
- e-TIN certificate and income-tax certificate remain distinct documents.
- General guidance cannot absorb unsupported, legal-advice or OOD queries.

## Pilot-review flags

Explicit pilot attention is required for TIN eligibility/cancellation,
return obligation/amendment, OTP/access problems, payment-ledger update,
tax-certificate access and broad service guidance. These are coherent enough
to test but must not be treated as unquestionable production labels.

No leaf contains a tax rate, threshold, deadline date, fee, office address or
current provider. The hierarchy is acceptable for a controlled four-seed
pilot. The global shared contract remains unfrozen.
