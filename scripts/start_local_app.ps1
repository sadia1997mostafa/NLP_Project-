$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv-answer\Scripts\python.exe"
$modelDir = Join-Path $root "models\answer_generator"

if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Missing .venv-answer. Create it with: uv venv .venv-answer --python 3.12"
}

$models = @(Get-ChildItem -LiteralPath $modelDir -Filter "*.gguf" -File -ErrorAction SilentlyContinue)
if (-not $env:NAGORIKSHEBA_ANSWER_GGUF -and $models.Count -ne 1) {
    throw "Place exactly one GGUF in models\answer_generator or set NAGORIKSHEBA_ANSWER_GGUF."
}

Set-Location -LiteralPath $root
& $python -m uvicorn app.server:app --host 127.0.0.1 --port 8002 --no-access-log
