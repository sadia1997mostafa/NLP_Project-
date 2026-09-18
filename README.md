# NagorikSheba AI

Partner B's citizen guidance app uses Prothom's frozen understanding API, a
privacy warning layer, and a curated government-information corpus.
It supports NID, birth registration, passport, tax, online GD, and driving
licence queries. This is a showcase prototype, not a production or real-world
validated service.

## Run locally

1. Use a Python environment with a supported PyTorch build and install
   `python -m pip install -r requirements-app.txt`.
2. Obtain Prothom's `models/final/` directory, including the tokenizer and 13
   active classifier directories. Model files are Git ignored and are **not**
   included in this repository. Keep the directory at the repository root.
3. Run `python -m src.models.verify_final_models` to check the classifier
   artifacts.
4. Start one persistent process:

   ```powershell
   python -m uvicorn app.server:app --host 127.0.0.1 --port 8000 --no-access-log
   ```

5. Open `http://127.0.0.1:8000/`.

The server imports `predict_understanding` once and retains Prothom's model
cache across requests. `GET /api/status` reports whether the model files are
present and records the runtime, results, and app commit IDs. Set
`NAGORIKSHEBA_APP_COMMIT` when packaging without `.git`.

## API and guidance

`POST /api/analyze` accepts JSON such as `{"text": "How do I apply for a passport?"}`.
The response includes privacy detection, a masked `safe_text`, Prothom's
understanding fields, retrieval details, and a controlled response. The app
checks an explicit service name and compares the question with curated topic
titles/IDs before showing a specific answer. This corpus-side check can correct
some wrong model routes; the original model route remains visible as
`model_service`/`model_query_topic_id` when corrected. Weak, conflicting, or
unsupported matches fall back to a parent/service overview or clarification.
The visitor can change the topic. `GET /api/guidance` lists curated choices;
`POST /api/guidance` accepts `service`, `parent_topic_id`, and `query_topic_id`
from one listed choice, plus an optional `language` of `en` or `bn`. Raw query
text is used only in memory for inference. The endpoint does not log request
bodies and sends `Cache-Control: no-store`.
Privacy matching covers common identifiers, OTPs/passwords, and explicitly
labelled names and addresses, including some Banglish fields. It can still miss
free-form personal details. Avoid sharing unnecessary sensitive information.

The [guidance corpus](knowledge_base/README.md) has 67 reviewed records from
22 official source URLs: 56 exact topics, five parent topics, and general
pointers for all six services. Document lists retain applicability conditions
and appear with the answer. The other 208 specific intents do not have dedicated
guidance; visitors can choose an overview or available parent record for
general guidance. Exact retrieval means a matching record exists, not that
the model understood the question correctly. The answer builder composes
English or Bengali guidance from a bilingual, source-scoped fact plan for each
covered route, rather than copying the corpus paragraph. It keeps document
conditions and official citations. This is controlled generation, not an
open-ended model, and topic titles and document names may remain in English.
Model confidence and the corpus matching gates are not validated on real
citizen traffic. OOD, weak service evidence and missing records receive no
fabricated specific answer.
Recheck official links and mutable facts before a public demonstration.

## Verify

Run `python -m unittest discover -s tests -p 'test_*.py'`. Tests cover the
integration contract with an injected predictor, so they run without model
files. Real classifier inference and latency must be checked again after
`models/final/` is supplied. With those files present, run
`python -m scripts.smoke_live` for a short real-model check across the six
services, Bengali queries, privacy masking, an unrelated query, two observed
intent mistakes, explicit topic selection, and repeated warm inference.
It uses manually written queries and does not rerun the frozen held-out TEST.

Run `python -m scripts.audit_corpus` for coverage and review-age checks;
add `--json` for the complete list of uncovered topic IDs. Run
`node --test tests/test_guidance_ui.cjs` for checklist rendering-state tests.
