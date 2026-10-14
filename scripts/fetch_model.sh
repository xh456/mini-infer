#!/usr/bin/env bash
# 拉取基线模型到 models/（体积大，永不入库）
#
#   MODEL_ID=Qwen/Qwen2.5-0.5B-Instruct LOCAL_DIR=models/qwen05b bash scripts/fetch_model.sh
#
# 优先 ModelScope（国内更稳），退回 HuggingFace 镜像。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
MODEL_ID="${MODEL_ID:-Qwen/Qwen2.5-0.5B-Instruct}"
LOCAL_DIR="${LOCAL_DIR:-models/Qwen2.5-0.5B-Instruct}"

# 优先用项目虚拟环境，避免误用系统 python
if [ -z "${PY:-}" ]; then
  if [ -x .venv/bin/python ]; then PY=".venv/bin/python"; else PY="python3"; fi
fi

mkdir -p "$(dirname "$LOCAL_DIR")"

if [ -f "$LOCAL_DIR/config.json" ]; then
  echo "[fetch_model] 已存在，跳过：$LOCAL_DIR"
  exit 0
fi

echo "[fetch_model] $MODEL_ID -> $LOCAL_DIR"

if "$PY" -c "import modelscope" >/dev/null 2>&1; then
  echo "[fetch_model] 通道：ModelScope"
  "$PY" - "$MODEL_ID" "$LOCAL_DIR" <<'PY'
import sys
from modelscope import snapshot_download
snapshot_download(sys.argv[1], local_dir=sys.argv[2])
PY
else
  echo "[fetch_model] 通道：HuggingFace 镜像 $HF_ENDPOINT"
  "$PY" - "$MODEL_ID" "$LOCAL_DIR" <<'PY'
import sys
from huggingface_hub import snapshot_download
snapshot_download(sys.argv[1], local_dir=sys.argv[2])
PY
fi

echo "[fetch_model] 完成：$LOCAL_DIR"
