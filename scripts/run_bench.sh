#!/usr/bin/env bash
# HF 基线测量入口。参数固定，结果落成 JSON，便于前后对比。
#
#   TAG=hf-baseline bash scripts/run_bench.sh
#   PROMPT_LENS=128,512,2048 DECODE_STEPS=128 BATCH=1 bash scripts/run_bench.sh
#
# 注意：所有对比实验必须在同一硬件、同一软件版本下完成。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -z "${PY:-}" ]; then
  if [ -x .venv/bin/python ]; then PY=".venv/bin/python"; else PY="python3"; fi
fi

MODEL="${MODEL:-models/Qwen2.5-0.5B-Instruct}"
PROMPT_LENS="${PROMPT_LENS:-128,512,2048}"
DECODE_STEPS="${DECODE_STEPS:-128}"
BATCH="${BATCH:-1}"
WARMUP="${WARMUP:-3}"
TAG="${TAG:-hf-baseline}"

mkdir -p bench/results

"$PY" bench/baseline_hf.py \
  --model "$MODEL" \
  --prompt-lens "$PROMPT_LENS" \
  --decode-steps "$DECODE_STEPS" \
  --batch "$BATCH" \
  --warmup "$WARMUP" \
  --tag "$TAG"

echo "[run_bench] 结果已写入 bench/results/"
