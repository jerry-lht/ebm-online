# OpenAI API Configuration

Phase 8 uses the official `openai` Python package. Keep real credentials out of
tracked files.

## Preferred Setup

Set the API key in the shell before a real run:

```bash
export OPENAI_API_KEY="sk-..."
```

Then run the LLM CLI with an explicit model id:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.run_llm \
  --provider openai \
  --model-id MODEL_ID \
  --examples results/data/test.examples.jsonl \
  --output-dir results/preds/llm/openai_zero_shot \
  --prompt-mode zero-shot-text
```

## Optional YAML Setup

Copy the example file and fill only local secrets:

```bash
cp code/config/llm_providers.example.yaml code/config/llm_providers.yaml
```

Use either `api_key_env: "OPENAI_API_KEY"` or a local-only `api_key` value in
`code/config/llm_providers.yaml`. Do not commit the real file if it contains a
secret.

`api_key_env` means "read the API key from this environment variable". If you
write the key directly in this local YAML file, you can omit `api_key_env`.

You can also store the model id in this local config:

```yaml
providers:
  openai:
    api_key: "sk-..."
    model_id: "MODEL_ID"
    model_version: null
    base_url: "https://api.openai.com/v1"
    api_mode: "responses"
    timeout_seconds: 120
defaults:
  provider: "openai"
  temperature: 0
  timeout_seconds: 120
```

For third-party OpenAI-compatible providers, the runner now defaults to
`chat_completions` unless the `base_url` contains `api.openai.com`. You can
override this explicitly:

```yaml
providers:
  openai:
    api_key: "..."
    model_id: "deepseek-v4-pro"
    base_url: "https://api.deepseek.com"
    api_mode: "chat_completions"
    timeout_seconds: 120
```

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.run_llm \
  --provider openai \
  --provider-config code/config/llm_providers.yaml \
  --examples results/data/test.examples.jsonl \
  --output-dir results/preds/llm/openai_zero_shot \
  --prompt-mode zero-shot-text
```

The runner uses `16` concurrent workers by default. Override this with
`--workers N` if your provider rate limit or machine resources require it.
Use `--show-progress` to print per-document progress to stderr.
Use `--resume` to continue from an existing `raw.jsonl` and skip finished
`doc_id` values.
The runner now appends each completed response directly to `raw.jsonl`, writes
failed documents to `errors.jsonl`, and retries each document `2` times by
default. Override retries with `--max-retries N`.
For prompt comparisons, the runner also supports `zero-shot-text-v2` and
`few-shot-text-v2`, which keep the prompt short but add explicit P/I/O
definitions.

## Phase 8 Output Flow

The runner writes raw per-document responses:

```text
results/preds/llm/openai_zero_shot/raw.jsonl
```

Validate and evaluate with the existing Phase 6 and Phase 5 CLIs for the
official span track, then run the text/content evaluator:

```bash
PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.validate_llm_predictions \
  --examples results/data/test.examples.jsonl \
  --raw results/preds/llm/openai_zero_shot/raw.jsonl \
  --valid-output results/preds/llm/openai_zero_shot/validated.spans.jsonl \
  --quality-output results/metrics/openai_zero_shot.quality.json \
  --method openai_llm \
  --setting zero_shot_text \
  --split test

PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.evaluate_predictions \
  --gold results/data/test.examples.jsonl \
  --pred results/preds/llm/openai_zero_shot/validated.spans.jsonl \
  --pred-format spans \
  --output results/metrics/openai_zero_shot.metrics.json \
  --method openai_llm \
  --setting zero_shot_text \
  --split test

PYTHONPATH=code /F00120250029/lixiang_share/liuhongtao_share/EBM-Online/.venv/bin/python -m pico.cli.evaluate_text_predictions \
  --gold results/data/test.examples.jsonl \
  --raw results/preds/llm/openai_zero_shot/raw.jsonl \
  --output results/metrics/openai_zero_shot.text_metrics.json \
  --method openai_llm \
  --setting zero_shot_text \
  --split test
```

Use `--dry-run --limit 2` first to inspect prompts without using the API.
