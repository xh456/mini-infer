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

echo "==> 1/6 系统依赖自检"
# 这一步是被实测补上的：全新 Ubuntu 22.04 上 `python3 -m venv` 会因为缺少
# ensurepip 而失败（系统没装 python3-venv 包）。本地 WSL 没暴露这个问题，
# 因为那里先前跑过 wsl-setup.sh 已经装好了工具链——干净的机器才会暴露假设。
if [ "${SKIP_APT:-0}" != "1" ] && command -v apt-get >/dev/null 2>&1; then
  if [ "$(id -u)" = "0" ]; then APT="apt-get"; else APT="sudo apt-get"; fi

  pkgs=()
  if ! "$PY" -c "import ensurepip" >/dev/null 2>&1; then
    pkgs+=(python3-venv python3-pip)
  fi
  # 后面手写 C++ / SIMD 算子要用到，一次装好，省得再开一次机
  pkgs+=(python3-dev build-essential)

  echo "    安装或确认：${pkgs[*]}"
  if ! DEBIAN_FRONTEND=noninteractive $APT install -y -qq "${pkgs[@]}" >/dev/null 2>&1; then
    echo "    直接安装失败，先更新索引再试一次"
    $APT update -qq >/dev/null 2>&1 || true
    DEBIAN_FRONTEND=noninteractive $APT install -y -qq "${pkgs[@]}" >/dev/null 2>&1 || true
  fi
fi

if ! "$PY" -c "import ensurepip" >/dev/null 2>&1; then
  echo "    错误：$PY 缺少 ensurepip，无法创建虚拟环境。" >&2
  echo "    请先执行：apt-get install -y python3-venv python3-pip" >&2
  exit 3
fi
echo "    通过"

echo "==> 2/6 解释器"
echo "    $PY -> $($PY --version 2>&1)"

echo "==> 3/6 创建虚拟环境 .venv"

# 判定 .venv 是否真的可用：不仅要存在，还要有可用的安装器。
# 上次中断可能留下"有 python 但没有 pip"的残骸，只看目录是否存在会让后续莫名失败。
venv_usable() {
  [ -x .venv/bin/python ] || return 1
  .venv/bin/python -c "import sys" >/dev/null 2>&1 || return 1
  .venv/bin/python -m pip --version >/dev/null 2>&1 && return 0
  command -v uv >/dev/null 2>&1 && return 0
  return 1
}

if venv_usable; then
  echo "    已存在且可用，跳过创建"
else
  if [ -d .venv ]; then
    echo "    检测到不可用的 .venv（可能上次创建中断），删除后重建"
    rm -rf .venv
  fi
  if command -v uv >/dev/null 2>&1; then
    uv venv --python "$PY" .venv
  else
    "$PY" -m venv .venv
  fi
fi

VENV_PY=".venv/bin/python"
if command -v uv >/dev/null 2>&1; then
  pip_install() { uv pip install --python "$VENV_PY" "$@"; }
else
  pip_install() { "$VENV_PY" -m pip install "$@"; }
fi

echo "==> 4/6 安装依赖（mode=$MODE）"
pip_install --upgrade pip wheel

# PyTorch 的 cpu / cuda 轮子不能混装，必须显式指定来源。
# download.pytorch.org 在国内会被连接重置，所以先探测可达性，不通就自动切国内镜像。
# 注意两者的差别：官方是 PEP 503 索引（用 --index-url），
# 国内镜像多为平铺目录（用 --find-links，且版本号要带 +cpu 后缀）。
if [ "$MODE" = "cuda" ]; then
  TORCH_INDEX="https://download.pytorch.org/whl/cu121"
  TORCH_MIRROR_FLAT="${TORCH_MIRROR_FLAT:-https://mirrors.aliyun.com/pytorch-wheels/cu121}"
  TORCH_MIRROR_SPEC="torch==2.4.1+cu121"
else
  TORCH_INDEX="https://download.pytorch.org/whl/cpu"
  TORCH_MIRROR_FLAT="${TORCH_MIRROR_FLAT:-https://mirrors.aliyun.com/pytorch-wheels/cpu}"
  TORCH_MIRROR_SPEC="torch==2.4.1+cpu"
fi

# 其余依赖的来源：国内可设 PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
PIP_EXTRA=()
if [ -n "${PIP_INDEX:-}" ]; then
  PIP_EXTRA=(-i "$PIP_INDEX")
  echo "    pip index = $PIP_INDEX"
fi

echo "    探测官方 PyTorch index：$TORCH_INDEX"
if curl -sSfI --max-time 8 "$TORCH_INDEX" >/dev/null 2>&1; then
  echo "    官方可达，使用官方 index"
  pip_install "torch==2.4.1" --index-url "$TORCH_INDEX"
else
  echo "    官方不可达，切换国内镜像：$TORCH_MIRROR_FLAT"
  pip_install "$TORCH_MIRROR_SPEC" --find-links "$TORCH_MIRROR_FLAT" "${PIP_EXTRA[@]}"
fi

pip_install -r requirements/base.txt "${PIP_EXTRA[@]}"

echo "==> 5/6 记录环境信息"
mkdir -p bench/results
"$VENV_PY" scripts/env_report.py | tee "bench/results/env-$(date +%Y%m%d-%H%M%S).json"

echo "==> 6/6 拉取基线模型 + 冒烟测试"
bash scripts/fetch_model.sh
"$VENV_PY" -m pytest tests/ -q

cat <<'EOF'

bootstrap 完成。下一步：
  bash scripts/run_bench.sh      # 跑第一份 HF 基线
  python scripts/env_report.py   # 查看硬件与版本

提醒：跑完测量记得关机。每次开机的花费要记进 budget/gpu_budget.csv。
EOF
