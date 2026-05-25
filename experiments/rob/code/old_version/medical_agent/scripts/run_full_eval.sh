#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Default to the fairest XML-only benchmark. Override with:
#   DATASET_DIR=rob_core_dataset scripts/run_full_eval.sh
DATASET_DIR="${DATASET_DIR:-rob_article_only_dataset}"
MODE="${MODE:-direct}"
MODEL="${MODEL:-gpt-5-mini}"
CONCURRENCY="${CONCURRENCY:-4}"
TIMEOUT="${TIMEOUT:-180}"
RETRY_TIMEOUT="${RETRY_TIMEOUT:-180}"
MAX_RETRIES="${MAX_RETRIES:-1}"
DOMAIN_CONTEXT_MAX_CHARS="${DOMAIN_CONTEXT_MAX_CHARS:-100000}"
RETRY_DOMAIN_CONTEXT_MAX_CHARS="${RETRY_DOMAIN_CONTEXT_MAX_CHARS:-8000}"
MAX_TOKENS="${MAX_TOKENS:-4096}"
REASONING_EFFORT="${REASONING_EFFORT:-minimal}"
OUTPUT_DIR="${OUTPUT_DIR:-eval_runs/full_eval}"
CALIBRATION="${CALIBRATION:-0}"
CLEAN_FIRST="${CLEAN_FIRST:-0}"
DRY_RUN="${DRY_RUN:-0}"

if [[ "$CLEAN_FIRST" == "1" ]]; then
  python src/clean_dataset.py --report-dir eval_runs/dataset_cleaning_latest
fi

if [[ ! -d "$DATASET_DIR" ]]; then
  echo "Dataset directory not found: $DATASET_DIR" >&2
  echo "Run CLEAN_FIRST=1 scripts/run_full_eval.sh or python src/clean_dataset.py first." >&2
  exit 1
fi

LIMIT="$(find "$DATASET_DIR" -maxdepth 1 -name '*.json' | wc -l | tr -d ' ')"
if [[ "$LIMIT" == "0" ]]; then
  echo "No JSON files found in $DATASET_DIR" >&2
  exit 1
fi
LIMIT=50
echo "Running full RoB eval"
echo "  dataset:     $DATASET_DIR"
echo "  studies:     $LIMIT"
echo "  mode:        $MODE"
echo "  model:       $MODEL"
echo "  concurrency: $CONCURRENCY"
echo "  calibration: $CALIBRATION"
echo "  output dir:  $OUTPUT_DIR/<timestamp>"

CMD=(
  python src/batch_eval.py
  --dataset-dir "$DATASET_DIR" \
  --limit "$LIMIT" \
  --mode "$MODE" \
  --model "$MODEL" \
  --timeout "$TIMEOUT" \
  --retry-timeout "$RETRY_TIMEOUT" \
  --domain-context-max-chars "$DOMAIN_CONTEXT_MAX_CHARS" \
  --retry-domain-context-max-chars "$RETRY_DOMAIN_CONTEXT_MAX_CHARS" \
  --max-tokens "$MAX_TOKENS" \
  --reasoning-effort "$REASONING_EFFORT" \
  --max-retries "$MAX_RETRIES" \
  --concurrency "$CONCURRENCY" \
  --output-dir "$OUTPUT_DIR" \
  --no-support-filter
)

if [[ "$CALIBRATION" == "1" ]]; then
  CMD+=(--calibration)
else
  CMD+=(--no-calibration)
fi

printf '  command:'
printf ' %q' "${CMD[@]}"
printf '\n'

if [[ "$DRY_RUN" == "1" ]]; then
  echo "DRY_RUN=1, not starting API calls."
  exit 0
fi

"${CMD[@]}"
