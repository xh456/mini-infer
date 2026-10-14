#!/usr/bin/env bash
# =====================================================================
# WSL / Ubuntu 侧一次性初始化（在 WSL 里执行，不要整个脚本用 sudo 跑）
#
#   bash ~/mini-infer/scripts/wsl-setup.sh
#
# 做的事：
#   1. 安装编译工具链（后面手写 C++/SIMD 算子要用）
#   2. 安装 uv（可选，装不上会自动退回 python3 -m venv）
#   3. 跑项目环境初始化，并打印环境报告
#
# 幂等：重复执行安全。
# =====================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> 环境自检"
if ! grep -qi microsoft /proc/version 2>/dev/null; then
  echo "    警告：看起来不是 WSL 环境，继续执行但请自行确认。" >&2
fi
echo "    发行版：$(. /etc/os-release && echo "$PRETTY_NAME")"
echo "    内核：  $(uname -r)"
echo "    仓库：  $ROOT"

echo "==> 1/4 安装系统依赖（会要求输入 sudo 密码）"
sudo apt update
sudo apt install -y \
  build-essential cmake ninja-build gdb clang \
  git curl python3-venv python3-pip

echo "==> 2/4 安装 uv（可选）"
export PATH="$HOME/.local/bin:$PATH"
if command -v uv >/dev/null 2>&1; then
  echo "    已安装：$(uv --version)"
else
  if curl -LsSf https://astral.sh/uv/install.sh | sh; then
    export PATH="$HOME/.local/bin:$PATH"
    echo "    已安装：$(uv --version 2>/dev/null || echo '需重开终端')"
  else
    echo "    uv 安装失败（网络问题？），将退回 python3 -m venv，不影响后续步骤"
  fi
fi

echo "==> 3/4 初始化项目环境（PyTorch CPU 版）"
bash scripts/bootstrap.sh cpu

echo "==> 4/4 环境报告"
python scripts/env_report.py 2>/dev/null || .venv/bin/python scripts/env_report.py

cat <<'EOF'

完成。接下来可以开始 W1 的 Day 6/Day 7：
  手推 KV Cache 显存公式，把结论补进 docs/w1-notes.md

提示：WSL 发行版默认装在 C 盘（C 盘目前只剩约 30GB）。
如果后面空间紧张，可以用 wsl --export / --import 把发行版整体迁到 D 盘。
EOF
