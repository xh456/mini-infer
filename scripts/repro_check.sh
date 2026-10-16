#!/usr/bin/env bash
# 复现性验收：同一台机器背靠背连跑 N 次同参数测量，然后自动判定。
#
#   RUNS=2 bash scripts/repro_check.sh
#   RUNS=2 PROMPT_LENS=128,512,2048 DECODE_STEPS=128 bash scripts/repro_check.sh
#
# 为什么必须背靠背：CPU 持续满载会降频，相隔十分钟的两组数字不可比
# （见 docs/experiment-template.md 第 7 条）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -z "${PY:-}" ]; then
  if [ -x .venv/bin/python ]; then PY=".venv/bin/python"; else PY="python3"; fi
fi

RUNS="${RUNS:-2}"
STAMP="$(date +%Y%m%d-%H%M%S)"
TAG_PREFIX="repro-${STAMP}"

for i in $(seq 1 "$RUNS"); do
  echo "=== 第 ${i} / ${RUNS} 次 ==="
  TAG="${TAG_PREFIX}-run${i}" bash scripts/run_bench.sh
  echo
done

echo "=== 复现性判定 ==="
set +e
"$PY" scripts/repro_summary.py --tag "$TAG_PREFIX"
code=$?
set -e

echo
echo "原始结果：bench/results/${TAG_PREFIX}-run*.json"
echo "提醒：正式基线请加 REQUIRE_QUIET=1，机器不静默时拒绝出数。"
exit $code
