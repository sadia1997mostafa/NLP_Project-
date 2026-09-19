# NagorikSheba Answer Showcase Cases

These cases were run after adding exact-intent answer plans. They are showcase
checks, not a new NLU benchmark, and no classifier or routing setting was
changed from their results.

## Summary

- Exact answer-plan coverage: 264/264.
- The local Qwen GGUF was available and loaded once for the run.
- Qwen is attempted only for an exact, non-emergency answer whose plan is not a
  safe clarification.
- Rejected writing falls back to the deterministic plan.
- One unsafe-sounding Police GD completion promise observed during the run was
  added to the quality gate and is now rejected.

## Cases

| # | Prompt | Observed NLU / resolved route | Plan | Qwen / fallback | Final behavior |
|---:|---|---|---|---|---|
| 1 | `NID card download korbo kivabe?` | Model `NID_PAYMENT_REFUND_RECEIPT`; evidence resolved `NID_ACCESS_DOWNLOAD` | `VERIFIED_SPECIFIC` | attempted, accepted | Natural Bangla answer explains account/download path and preserves the existing-registration condition. |
| 2 | `আমার NID OTP আসছে না` | Model and resolved `NID_SMART_GENERAL_PROBLEM` | `SAFE_CLARIFICATION` | not attempted | Asks which step/message is failing and warns not to share OTP/password/ID. The unchanged NLU route is noted as incorrect. |
| 3 | `জন্ম নিবন্ধন verify করব কীভাবে?` | Model `BR_REGISTRATION_PROCESS`; evidence resolved `BR_VERIFICATION_RECORD` | `VERIFIED_SPECIFIC` | attempted, rejected; deterministic fallback | Directs the user to the official Birth Registration verification page without adding facts. |
| 4 | `জন্ম নিবন্ধনের OTP একদম আসছে না` | `BR_REGISTRATION_OTP_NOT_RECEIVED` | `VERIFIED_GENERAL` | attempted, rejected; deterministic fallback | Directly identifies the missing-OTP step, states that verified troubleshooting details are unavailable, and asks whether delivery or acceptance is failing. |
| 5 | `passport status check korbo kivabe?` | Model `PASSPORT_GENERAL_NEW_VS_REISSUE`; evidence resolved `PASSPORT_APPLICATION_STATUS` | `VERIFIED_SPECIFIC` | attempted, accepted | Natural Bangla/Banglish answer gives the approved Status Check, application-ID and birth-date steps. |
| 6 | `আমার passport application অনেকদিন pending, কী করব?` | `PASSPORT_APPLICATION_DELAY` | `SAFE_CLARIFICATION` | not attempted | States that no cause or completion date is verified and asks what status/error is shown without requesting the actual reference ID. |
| 7 | `e-TIN certificate download korbo kivabe?` | Model `TAX_TIN_ONLINE_REGISTRATION`; evidence resolved `TAX_RETURN_COPY_DOWNLOAD` | `VERIFIED_SPECIFIC` | attempted, rejected; deterministic fallback | Returned the verified tax-record download plan, but the route is not the requested TIN-certificate route; retained as an NLU/retrieval limitation. |
| 8 | `Tax return deadline kobe?` | Model/resolved `TAX_PAYMENT_FAILURE` | `VERIFIED_GENERAL` | attempted, accepted | The answer did not invent a date, but the unchanged route was wrong; recorded for later NLU review rather than repaired here. |
| 9 | `Online GD submit korbo kivabe?` | Model `POLICE_GD_SUBMISSION_RECEIPT`; evidence resolved `POLICE_GD_ONLINE_SUBMISSION` | `VERIFIED_SPECIFIC` | initial output accepted; now rejected by strengthened promise gate | Final behavior falls back to the verified sign-in, complaint-type, police-station, incident-detail and relevant-evidence plan. |
| 10 | `জরুরি বিপদে GD করব নাকি 999-এ কল করব?` | Evidence resolved `POLICE_GD_EMERGENCY_ROUTING` after Bengali emergency evidence check | `VERIFIED_SPECIFIC` | intentionally not attempted | Direct emergency-safe response says to call 999, not wait for Online GD, and that the app cannot dispatch help. |
| 11 | `learner licence er jonno ki documents lagbe?` | Model `DRIVING_LICENCE_LEARNER_COPY`; evidence resolved `DRIVING_LICENCE_LEARNER_DOCUMENTS` | `VERIFIED_SPECIFIC` | attempted, rejected; deterministic fallback | Shows the source-backed learner-document introduction and the separately rendered document checklist. |
| 12 | `Driving licence test fail korle retake কীভাবে করব?` | `DRIVING_LICENCE_TEST_RETAKE` | `SAFE_CLARIFICATION` | not attempted | States that current retake booking, fee and timing rules are not verified and asks which test/result step applies. |

## High-value verified-specific plans

The following 42 common routes now expose structured direct answers, steps,
documents, warnings and sources through the exact plan layer:

- NID: `NID_REGISTRATION_ONLINE_APPLICATION`, `NID_CORRECTION_DOB`,
  `NID_REPLACEMENT_ONLINE_APPLICATION`, `NID_ONLINE_ACCOUNT_REGISTRATION`,
  `NID_ONLINE_LOGIN`, `NID_ONLINE_PASSWORD_RESET`, `NID_ACCESS_DOWNLOAD`,
  `NID_FEES_SERVICE_SPECIFIC`.
- Birth Registration: `BR_REGISTRATION_ONLINE_APPLICATION`,
  `BR_REGISTRATION_LOCATION_SELECTION`, `BR_REGISTRATION_OTP_VERIFICATION`,
  `BR_CORRECTION_PROCESS`, `BR_CORRECTION_PARENT_BRN_MAPPING`,
  `BR_APPLICATION_STATUS`, `BR_CERTIFICATE_REPRINT`, `BR_VERIFICATION_RECORD`.
- Passport: `PASSPORT_APPLICATION_ONLINE`, `PASSPORT_APPLICATION_INFORMATION`,
  `PASSPORT_DOCUMENTS_REQUIRED`, `PASSPORT_DOCUMENTS_PREVIOUS_PASSPORT`,
  `PASSPORT_ONLINE_ACCOUNT_LOGIN`, `PASSPORT_REISSUE_LOST`,
  `PASSPORT_FEES_INFORMATION`, `PASSPORT_APPLICATION_STATUS`.
- Tax: `TAX_RETURN_ONLINE_SUBMISSION`, `TAX_RETURN_REQUIRED_DOCUMENTS`,
  `TAX_ACCOUNT_REGISTRATION`, `TAX_ACCOUNT_LOGIN`,
  `TAX_RETURN_ACKNOWLEDGEMENT`, `TAX_CERTIFICATE_ACCESS`.
- Police GD: `POLICE_GD_EMERGENCY_ROUTING`, `POLICE_GD_ONLINE_SUBMISSION`,
  `POLICE_GD_ATTACHMENTS`, `POLICE_GD_IDENTITY_REQUIREMENTS`,
  `POLICE_GD_STATUS`, `POLICE_GD_COPY_DOWNLOAD`.
- Driving Licence: `DRIVING_LICENCE_LEARNER_ELIGIBILITY`,
  `DRIVING_LICENCE_LEARNER_PROCESS`, `DRIVING_LICENCE_LEARNER_DOCUMENTS`,
  `DRIVING_LICENCE_TEST_REQUIREMENTS`, `DRIVING_LICENCE_FEE_INFORMATION`,
  `DRIVING_LICENCE_VERIFICATION`.

The 85 `SAFE_CLARIFICATION` plan IDs are the exact
`NEEDS OFFICIAL SOURCE ENRICHMENT` set. They are machine-readable in
`knowledge_base/answer_plans.json` and printed by
`python -m scripts.audit_answer_plans`.
