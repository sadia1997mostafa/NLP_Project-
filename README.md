# NagorikSheba AI

Partner B's citizen guidance app uses Prothom's frozen understanding API, a
privacy warning layer, and a small curated government-information corpus.
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
understanding fields, retrieval details, and a controlled response. Raw query
text is used only in memory for inference. The endpoint does not log request
bodies and sends `Cache-Control: no-store`.
Privacy matching covers common identifiers and explicitly labelled names and
addresses; it can miss free-form personal details, so users should still avoid
sharing unnecessary sensitive information.

The [guidance corpus](knowledge_base/README.md) currently has 14 reviewed
records, with general pointers for all six services. Most of the 264 specific
intents do not yet have dedicated guidance; those routes receive clearly
marked general information. OOD and missing records receive no fabricated
service-specific answer. If an unanchored model prediction finds only general
service guidance, the app asks for clarification rather than showing a possibly
unrelated service. Recheck official links and mutable facts before a public
demonstration.

## Verify

Run `python -m unittest discover -s tests -p 'test_*.py'`. Tests cover the
integration contract with an injected predictor, so they run without model
files. Real classifier inference and latency must be checked again after
`models/final/` is supplied. With those files present, run
`python -m scripts.smoke_live` for a short real-model check across the six
services, privacy masking, an unrelated query, and repeated warm inference.
It uses manually written queries and does not rerun the frozen held-out TEST.
