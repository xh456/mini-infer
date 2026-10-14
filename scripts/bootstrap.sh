#!/usr/bin/env bash
# =====================================================================
# mini-infer 环境一键初始化（云端 Linux GPU 实例 / 本地 WSL）
#
#   bash scripts/bootstrap.sh cuda    # 有 NVIDIA GPU 的实例
#   bash scripts/bootstrap.sh cpu     # 本地 WSL 或纯 CPU 机器
#
# 设计原则：
#   1. 幂等 —— 重复执行不会破坏已有环境
#   2. 不依赖交互 —— 可以在云实例上一次性粘贴执行
#   3. 环境信息自动落盘 —— 每次初始化都留下可追溯的记录
# =====================================================================
set -euo pipefail

MODE="${1:-cpu}"
if [ "$MODE" != "cpu" ] && [ "$MODE" != "cuda" ]; then
  echo "用法: bash scripts/bootstrap.sh [cpu|cuda]" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# HuggingFace 直连不稳，统一走镜像；需要时用环境变量覆盖
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

# 与云端镜像保持一致比"追新"重要：3.10 / 3.11 都是安全选择
PY="${PY:-python3}"

echo "==> 1/5 解释器"
echo "    $PY -> $($PY --version 2>&1)"

echo "==> 2/5 创建虚拟环境 .venv"
if [ -d .venv ]; then
  echo "    已存在，跳过创建（要重建请先 rm -rf .venv）"
elif command -v uv >/dev/null 2>&1; then
  uv venv --python "$PY" .venv
else
  "$PY" -m venv .venv
fi

VENV_PY=".venv/bin/python"
if command -v uv >/dev/null 2>&1; then
  pip_install() { uv pip install --python "$VENV_PY" "$@"; }
else
  pip_install() { "$VENV_PY" -m pip install "$@"; }
fi

echo "==> 3/5 安装依赖（mode=$MODE）"
pip_install --upgrade pip wheel

# PyTorch 的 cpu / cuda 轮子不能混装，必须显式指定 index
if [ "$MODE" = "cuda" ]; then
  TORCH_INDEX="https://download.pytorch.org/whl/cu121"
else
  TORCH_INDEX="https://download.pytorch.org/whl/cpu"
fi
pip_install "torch==2.4.1" --index-url "$TORCH_INDEX"
pip_install -r requirements/base.txt

echo "==> 4/5 记录环境信息"
mkdir -p bench/results
"$VENV_PY" scripts/env_report.py | tee "bench/results/env-$(date +%Y%m%d-%H%M%S).json"

echo "==> 5/5 拉取基线模型 + 冒烟测试"
bash scripts/fetch_model.sh
"$VENV_PY" -m pytest tests/ -q

cat <<'EOF'

bootstrap 完成。下一步：
  bash scripts/run_bench.sh      # 跑第一份 HF 基线
  python scripts/env_report.py   # 查看硬件与版本

提醒：跑完测量记得关机。每次开机的花费要记进 budget/gpu_budget.csv。
EOF
