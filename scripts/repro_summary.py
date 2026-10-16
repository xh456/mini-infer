#!/usr/bin/env python3
"""比较多份基线 JSON，输出复现性结论。

用途有两个：
  1. 复现性验收：同一配置背靠背跑 N 次，跨运行的 min 值差异必须 <= 5%
  2. 阶段对比：优化前后各一份，直接看出改进了多少

用法：
    python scripts/repro_summary.py --tag repro            # 按 tag 前缀筛选
    python scripts/repro_summary.py --runs 2               # 只取最新 2 份
    python scripts/repro_summary.py --files a.json b.json  # 显式指定
    python scripts/repro_summary.py --threshold 5.0        # 改判定阈值

以 min 值为准：噪声只会让结果变慢，不会变快（见 docs/experiment-template.md）。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_metrics(path: Path) -> dict[str, float | None]:
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics: dict[str, float | None] = {}
    for item in data.get("prefill", []):
        metrics[f"prefill_{item['prompt_tokens']}_ms"] = item.get("latency_ms")
    decode = data.get("decode", {})
    metrics["decode_ttft_ms"] = decode.get("ttft_ms")
    metrics["decode_tpot_ms"] = decode.get("tpot_ms")
    metrics["decode_tokens_per_s"] = decode.get("tokens_per_s")
    metrics["model_load_s"] = data.get("load_time_s")
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="bench/results")
    parser.add_argument("--tag", default=None, help="按 JSON 内的 tag 前缀筛选")
    parser.add_argument("--runs", type=int, default=0, help="只取最新 N 份，0 表示全部")
    parser.add_argument("--files", nargs="*", default=None)
    parser.add_argument("--threshold", type=float, default=5.0,
                        help="跨运行差异上限（百分比）")
    args = parser.parse_args()

    if args.files:
        paths = [Path(f) for f in args.files]
    else:
        candidates = []
        for path in sorted(Path(args.dir).glob("*.json")):
            if path.name.startswith("env-"):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if "prefill" not in data:
                continue
            if args.tag and not str(data.get("tag", "")).startswith(args.tag):
                continue
            candidates.append(path)
        paths = candidates[-args.runs:] if args.runs > 0 else candidates

    if len(paths) < 2:
        print(f"需要至少 2 份结果才能比较，实际找到 {len(paths)} 份")
        return 2

    runs = [(p.name, load_metrics(p)) for p in paths]
    labels = [f"run{i + 1}" for i in range(len(runs))]

    print("参与比较的文件（按时间顺序）：")
    for i, (name, _) in enumerate(runs):
        print(f"  run{i + 1} = {name}")
    print()

    header = f"{'指标':<24}" + "".join(f"{lab:>14}" for lab in labels)
    print(header)
    print("-" * len(header))

    failures: list[tuple[str, float]] = []
    for key in runs[0][1]:
        values = [m.get(key) for _, m in runs]
        if any(v is None for v in values):
            cells = "".join(f"{('n/a' if v is None else f'{v:.2f}'):>14}" for v in values)
            print(f"{key:<24}{cells}")
            continue
        numeric = [float(v) for v in values]
        lo = min(numeric)
        spread = (max(numeric) - lo) / lo * 100 if lo > 0 else float("inf")
        cells = "".join(f"{v:>14.2f}" for v in numeric)
        flag = "" if spread <= args.threshold else f"   << 差异 {spread:.1f}%"
        if spread > args.threshold:
            failures.append((key, spread))
        print(f"{key:<24}{cells}{flag}")

    print()
    print(f"运行份数：{len(runs)}    差异上限：{args.threshold}%")
    if failures:
        print("判定：不通过。以下指标跨运行差异超标：")
        for key, spread in sorted(failures, key=lambda kv: -kv[1]):
            print(f"  - {key}：{spread:.1f}%")
        print("\n可能原因：机器不静默（看 JSON 里的 loadavg / quiet 字段）、")
        print("实例是共享型或限速型、或者两次测量之间环境发生了变化。")
        print("请注意：换硬件导致的差异不算问题，但必须重新建立基线，不能直接对比。")
        return 1

    print("判定：通过。同一配置跨运行差异在上限之内，这组数字可以用于横向对比。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
