# Local Answer Model: Colab Runbook

This optional experiment uses no hosted model or API. The existing classifier
selects an exact curated topic; the fine-tuned model receives the masked
question and that topic's own `guidance.json` record. The app adds source links
and document lists separately. If the model is absent, fails, or returns an
obviously unsafe answer, the controlled answer remains available.

This does **not** guarantee factual accuracy. Automated checks catch some
errors (new numbers, links, identifiers, wrong language), not all invented
claims. Human review of unseen questions is required before public use.

## Dataset

`python -m scripts.export_answer_training` creates `train.jsonl` and
`dev.jsonl` from the frozen train and dev question splits. Only exact topics
covered by the reviewed corpus are included; the official TEST split is not
read. Targets are composed from `answer_facts.json`. This is a bootstrap set,
not independently written citizen QA. Currently it has 276 train and 138 dev
examples; it does not teach the model the 208 uncovered exact topics.
Train and dev can share topics and near-identical targets, so a low dev loss
does not demonstrate good answers to new citizen questions.

Keep `guidance.json` unchanged unless its official source is rechecked. Review
sample questions, conditions and target answers before training. Later, add
source-checked, independently worded QA examples in a separate dataset.

## Colab Steps

1. Open the [official Unsloth Qwen3 4B Instruct notebook](https://colab.research.google.com/github/unslothai/notebooks/blob/main/nb/Qwen3_(4B)-Instruct.ipynb). Choose **Runtime > Change runtime type > GPU**. Run only its first **installation** cell; do not run its example-dataset or training cells.
2. In a new code cell, clone this branch:

   ```python
   !git clone --branch feature/sece2e --single-branch https://github.com/sadia1997mostafa/NLP_Project-.git /content/NLP_Project-
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

4. Train QLoRA and export a quantized GGUF:

   ```python
   !python -m scripts.train_answer_colab --max-steps 60
   ```

   A GPU is required and the run may take longer than a short Colab session.
   Outputs are under `models/answer_generator/`: adapter, `metrics.json`,
   `review_samples.jsonl` (12 generated dev answers), and a `q4_k_m` GGUF.
   **Read the generated examples** for wrong facts, omitted conditions, and
   unnatural Bengali. Also test questions you write yourself, outside these
   splits. Lowering `--max-steps` is only a smoke test. If GGUF
   export fails after training, the adapter remains; do not claim local model
   integration is ready until export works.

5. Move the **single** GGUF to Drive for download to this PC:

   ```python
   from google.colab import drive
   from pathlib import Path
   import shutil
   drive.mount("/content/drive")
   gguf = next(Path("models/answer_generator").glob("**/*Q4_K_M.gguf"))
   destination = Path("/content/drive/MyDrive/nagoriksheba-answer.gguf")
   shutil.copy2(gguf, destination)
   print(destination, gguf.stat().st_size)
   ```

   Retain `metrics.json` and `review_samples.jsonl` as evaluation evidence.
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
3. In the **same PowerShell session** that starts the app, set the file path:

   ```powershell
   $env:NAGORIKSHEBA_ANSWER_GGUF = 'D:\NLP_LAB\nlp_projectfinal\NLP_Project-\models\answer_generator\nagoriksheba-answer.gguf'
   python -m uvicorn app.server:app --host 127.0.0.1 --port 8002
   ```

   Stop an existing app on port 8002 first, or choose a free port. `/api/status`
   must report `answer_generator_ready: true`.
4. Test new questions in all six services, including Bengali, Banglish,
   documents, conditional rules, unknown details, OTP masking and unrelated
   queries. Accepted model output has `answer_basis: local_finetuned_model`;
   fallback has `curated_source_facts`. Compare each with the official source
   and the controlled answer. A working GGUF does not prove reliable factual
   generation.

The model runs on CPU here and may answer slowly. Without GGUF and its optional
runtime, the existing app continues to work; it never calls a remote model.
