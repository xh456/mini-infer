#!/usr/bin/env python3
"""打印当前环境的关键信息（JSON）。

为什么需要它：任何性能数字脱离了硬件和版本都没有意义。这个脚本输出的硬件与
版本字段，就是实验记录"四要素"里的前两项，每次测量都必须一并保存。
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime


def _run(cmd: str) -> str:
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _cpu_model() -> str | None:
    if platform.system() == "Linux" and os.path.exists("/proc/cpuinfo"):
        with open("/proc/cpuinfo", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                if "model name" in line:
                    return line.split(":", 1)[1].strip()
    if platform.system() == "Windows":
        return _run("wmic cpu get name /value") or None
    return None


def collect() -> dict:
    info: dict = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "cpu_model": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "git_commit": _run("git rev-parse --short HEAD") or None,
        "git_dirty": bool(_run("git status --porcelain")),
        "torch": None,
        "cuda_runtime": None,
        "gpu_name": None,
        "gpu_mem_gb": None,
        "gpu_capability": None,
        "transformers": None,
    }

    try:
        import torch

        info["torch"] = torch.__version__
        info["cuda_runtime"] = torch.version.cuda
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            info["gpu_name"] = torch.cuda.get_device_name(0)
            info["gpu_mem_gb"] = round(props.total_memory / 1024**3, 2)
            info["gpu_capability"] = ".".join(
                map(str, torch.cuda.get_device_capability(0))
            )
    except Exception:
        pass

    try:
        import transformers

        info["transformers"] = transformers.__version__
    except Exception:
        pass

    return info


if __name__ == "__main__":
    print(json.dumps(collect(), ensure_ascii=False, indent=2))
