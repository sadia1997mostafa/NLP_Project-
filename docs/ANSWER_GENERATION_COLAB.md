# Local Answer Model: Colab Runbook

This optional experiment uses no hosted model or API. The existing classifier
selects an exact curated topic; the fine-tuned model receives the masked
question and that topic's reviewed facts in the required answer language. The
app adds source links and document lists separately. If the model is absent,
fails, or returns an
obviously unsafe answer, the controlled answer remains available.

This does **not** guarantee factual accuracy. Automated checks catch some
errors (new numbers, links, identifiers, wrong language), not all invented
claims. Human review of unseen questions is required before public use.

## Dataset

`python -m scripts.export_answer_training` creates `train.jsonl` and
`dev.jsonl` from the frozen train and dev question splits. It covers all 264
intent IDs without reading the official TEST split: 56 plans are
`VERIFIED_SPECIFIC`, 123 are `VERIFIED_GENERAL`, and 85 are
`SAFE_CLARIFICATION`. Bounded plans teach the model to admit when exact fees,
deadlines, documents, eligibility rules or troubleshooting steps are not
verified; they do not turn a general service link into specific evidence.

The export has 2,112 train examples (six split questions plus two
language-controlled canonical questions per intent) and 792 dev examples
(three per intent). Targets contain a direct answer followed, when approved,
by numbered steps, document lists, cautions and one clarification question.
The application attaches the validated `.gov.bd` source link separately so the
model is never trained to invent or reproduce URLs. Train and dev share topics
and often share target facts, so a low dev loss does not demonstrate reliable
answers to genuinely new citizen questions.

Keep `guidance.json` unchanged unless its official source is rechecked. Review
sample questions, conditions and target answers before training. Later, add
source-checked, independently worded QA examples in a separate dataset.

## Colab Steps

1. Open the [official Unsloth Qwen3 4B Instruct notebook](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Qwen3_(4B)-Instruct.ipynb). Choose **Runtime > Change runtime type > GPU**. Run only its first **installation** cell; do not run its example-dataset or training cells.
2. In a new code cell, clone the answer-generation v3 branch:

   ```python
   !git clone --branch feature/answer-generation-v3 --single-branch https://github.com/sadia1997mostafa/NLP_Project-.git /content/NLP_Project-
   %cd /content/NLP_Project-
   ```

3. Export and inspect the dataset:

   ```python
   !python -m scripts.export_answer_training
   import json
   from pathlib import Path
   first = json.loads(Path("data/answer_generation/train.jsonl").read_text(encoding="utf-8").splitlines()[0])
   print(json.dumps(first, ensure_ascii=False, indent=2))
   ```

4. Train the all-intent v3 QLoRA recipe into a fresh directory. The default
   264 optimizer steps are one balanced pass over the 2,112 examples with an
   effective batch size of eight:

   ```python
   !python -m scripts.train_answer_colab --max-steps 264 --output-dir models/answer_generator_v3
   ```

   A GPU is required and the run may take longer than a short Colab session.
   Outputs are under `models/answer_generator_v3/`: adapter, `metrics.json`,
   `review_samples.jsonl` (18 fixed unseen challenge answers), `review_summary.json`,
   and a `Q4_K_M` GGUF. The script requires at least 15 of 18 generated samples
   to pass structural safety checks before spending time on GGUF conversion.
   **Read the generated examples** for wrong facts, omitted conditions, and
   unnatural Bengali. Also test questions you write yourself, outside these
   splits. Lowering `--max-steps` below 264 is only a smoke test and does not
   expose the optimizer to the complete balanced training set. If GGUF
   export fails after training, the adapter remains; do not claim local model
   integration is ready until export works.

5. Download the **single** GGUF directly to this PC:

   ```python
   from google.colab import files
   from pathlib import Path
   gguf = next(Path("models/answer_generator_v3").glob("**/*Q4_K_M.gguf"))
   print(gguf, round(gguf.stat().st_size / 1024**3, 2), "GB")
   files.download(str(gguf))
   ```

   Also download `metrics.json`, `review_summary.json`, and
   `review_samples.jsonl` as evaluation evidence.
   Do not commit model weights or private data to Git.

## Local Steps

1. Download the GGUF into the ignored `models/answer_generator/` directory.
2. In the app's Python environment, install optional in-process
   [llama-cpp-python](https://github.com/abetlen/llama-cpp-python). Its project
   documents a CPU wheel index:

   ```powershell
   python -m pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
   ```

   A prebuilt wheel may not exist for this machine's Python 3.14. If this
   fails, use a compatible Python environment with the app dependencies and a
   supported wheel; a source build requires a C++ toolchain.
3. If exactly one `.gguf` exists in `models/answer_generator/`, the app finds it
   automatically. Start the prepared local environment with:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start_local_app.ps1
   ```

   Set `NAGORIKSHEBA_ANSWER_GGUF` first only when choosing among multiple model
   files. Stop an existing app on port 8002 first. `/api/status` must report
   `answer_generator_ready: true`.
4. Test new questions in all six services, including Bengali, Banglish,
   documents, conditional rules, unknown details, OTP masking and unrelated
   queries. Accepted model output has `answer_basis: local_finetuned_model`;
   fallback has `curated_source_facts`. Compare each with the official source
   and the controlled answer. A working GGUF does not prove reliable factual
   generation.

The model runs on CPU here and may answer slowly. Without GGUF and its optional
runtime, the existing app continues to work; it never calls a remote model.

## Held-out Test

`data/evaluation/answer_generation_test.jsonl` contains one manually authored,
privacy-clean question for every covered exact topic. These 56 questions are
not read by the training exporter and automated tests reject any exact overlap
with answer-model TRAIN or DEV.

Run the structural leakage and coverage checks without loading the model:

```powershell
python -m scripts.evaluate_answer_test --validate-only
```

With the local GGUF ready, run the complete routing and generation evaluation:

```powershell
python -m scripts.evaluate_answer_test
```

The detailed report is written to
`models/evaluation/answer_generation_test_results.json`. Passing requires the
expected service, exact topic, output language, answer state, answer basis,
privacy state and official source for each case. The emergency-routing case
expects the controlled safety answer; the other cases expect accepted local
Qwen wording. Read generation acceptance separately from exact-topic routing:
the former evaluates Qwen against the expected record, while the latter tests
whether the upstream pipeline selected that record without being told.
