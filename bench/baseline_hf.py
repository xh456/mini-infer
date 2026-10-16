#!/usr/bin/env python3
"""HF 基线测量：prefill 延迟 / decode 吞吐 / 峰值显存。

为什么这样设计：
  - 只报"总耗时"没有信息量。prefill 是计算密集（compute-bound），decode 是
    带宽密集（memory-bound），两者瓶颈完全不同，必须分开测；否则后面优化自研
    引擎时，你根本不知道自己改进了哪一段。
  - 结果写成 JSON 并附带硬件与版本（四要素），保证半年后仍可对比。
  - decode 用差值法求单步耗时：t(N) = 首 token + (N-1) × 单步，
    所以 TPOT = (t_N - t_1) / (N - 1)，避免把 prefill 时间算进 decode。

用法：
    python bench/baseline_hf.py --model models/Qwen2.5-0.5B-Instruct \
        --prompt-lens 128,512,2048 --decode-steps 128 --batch 1 --tag hf-baseline
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from env_report import collect  # noqa: E402


def sync(device: str) -> None:
    if device == "cuda":
        torch.cuda.synchronize()


def samples(fn, *, warmup: int, repeats: int, device: str) -> list[float]:
    """返回每次迭代的耗时样本（秒），warmup 之后才开始计时。

    为什么保留全部样本而不是只报平均：同一台机器重复测量时，
    短窗口加系统噪声（后台进程、CPU 降频）会让均值漂移几十个百分点。
    只有保留样本才能看出离散度；报告时用最小值作为"这台机器能做到多快"的估计，
    因为噪声几乎只会让结果变慢，不会让它变快。
    """
    for _ in range(warmup):
        fn()
    sync(device)
    out: list[float] = []
    for _ in range(repeats):
        started = time.perf_counter()
        fn()
        sync(device)
        out.append(time.perf_counter() - started)
    return out


def stats(values: list[float]) -> dict:
    ordered = sorted(values)
    lo, hi = ordered[0], ordered[-1]
    return {
        "min_ms": round(lo * 1000, 2),
        "median_ms": round(statistics.median(ordered) * 1000, 2),
        "mean_ms": round(statistics.fmean(ordered) * 1000, 2),
        "max_ms": round(hi * 1000, 2),
        "spread_pct": round((hi - lo) / lo * 100, 1) if lo > 0 else None,
        "samples_ms": [round(v * 1000, 2) for v in values],
    }


def quiet_check(threshold: float) -> tuple[bool, list[float] | None]:
    """机器是否处于"静默"状态（loadavg 低于阈值）。

    这个检查是被实测逼出来的：2026-10-16 在同一台笔记本上重复测量，
    同一配置跨运行差异达 70%~100%，单次运行内部离散度甚至超过 1000%。
    这种数字没有比较价值，与其默默产出垃圾数据，不如直接告诉使用者。
    """
    if not hasattr(os, "getloadavg"):
        return True, None
    values = list(os.getloadavg())
    return values[0] <= threshold, values


def build_inputs(tokenizer, length: int, batch: int, device: str):
    """构造恰好 length 个 token 的输入（重复文本 + 截断，保证长度精确）。"""
    unit = "The quick brown fox jumps over the lazy dog. "
    text = unit
    while len(tokenizer(text)["input_ids"]) < length:
        text *= 2
    encoded = tokenizer(text, return_tensors="pt")
    input_ids = encoded["input_ids"][:, :length].to(device)
    attention_mask = encoded["attention_mask"][:, :length].to(device)
    if batch > 1:
        input_ids = input_ids.repeat(batch, 1)
        attention_mask = attention_mask.repeat(batch, 1)
    return input_ids, attention_mask


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--prompt-lens", default="128,512,2048")
    parser.add_argument("--decode-steps", type=int, default=128)
    parser.add_argument("--decode-prompt-len", type=int, default=32)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--threads", type=int, default=0,
                        help="torch 线程数，0 表示保留默认值")
    parser.add_argument("--quiet-loadavg", type=float, default=1.0,
                        help="1 分钟负载高于该值即视为机器不静默")
    parser.add_argument("--require-quiet", action="store_true",
                        help="机器不静默时直接退出，不出数")
    parser.add_argument("--dtype", default="auto", choices=["auto", "float16", "float32"])
    parser.add_argument("--tag", default="hf-baseline")
    parser.add_argument("--out-dir", default="bench/results")
    args = parser.parse_args()

    if not (Path(args.model) / "config.json").is_file():
        print(f"[bench] 找不到模型：{args.model}，先跑 scripts/fetch_model.sh", file=sys.stderr)
        return 2

    quiet, load = quiet_check(args.quiet_loadavg)
    if load is not None:
        print(f"[bench] loadavg = {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}"
              f"（阈值 {args.quiet_loadavg}）")
    if not quiet:
        advice = ("机器当前不静默，测量结果会严重失真"
                  "（实测同一配置跨运行可差 70% 以上）。"
                  "建议关掉浏览器、暂停网盘同步与杀毒扫描后重测，或改用专用云实例。")
        if args.require_quiet:
            print(f"[bench] 中止：{advice}", file=sys.stderr)
            return 3
        print(f"[bench] 警告：{advice}")

    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if args.dtype == "auto":
        dtype = torch.float16 if device == "cuda" else torch.float32
    else:
        dtype = getattr(torch, args.dtype)

    torch.manual_seed(0)  # 固定随机性，保证可复现

    # 线程数显式固定：不固定的话，宿主机负载变化会改变 OpenMP 的线程调度，
    # 这是 CPU 上测量方差最大的来源之一。
    if args.threads > 0:
        torch.set_num_threads(args.threads)
    print(f"[bench] device={device} dtype={dtype} batch={args.batch} "
          f"threads={torch.get_num_threads()} warmup={args.warmup} repeats={args.repeats}")

    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()

    t0 = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype).to(device).eval()
    load_time_s = time.perf_counter() - t0
    print(f"[bench] 模型加载耗时 {load_time_s:.2f}s")

    result: dict = {
        "tag": args.tag,
        "model": args.model,
        "device": device,
        "dtype": str(dtype).replace("torch.", ""),
        "batch": args.batch,
        "decode_steps": args.decode_steps,
        "warmup": args.warmup,
        "repeats": args.repeats,
        "torch_threads": torch.get_num_threads(),
        "loadavg": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
        "quiet": quiet,
        "num_params": sum(p.numel() for p in model.parameters()),
        "env": collect(),
        "load_time_s": round(load_time_s, 3),
        "prefill": [],
        "decode": {},
    }

    # ---- prefill：纯前向，含 KV Cache 写入 ----
    for length in [int(x) for x in args.prompt_lens.split(",")]:
        input_ids, attention_mask = build_inputs(tokenizer, length, args.batch, device)

        def prefill():
            with torch.inference_mode():
                model(input_ids=input_ids, attention_mask=attention_mask, use_cache=True)

        raw = samples(prefill, warmup=args.warmup, repeats=args.repeats, device=device)
        st = stats(raw)
        entry = {
            "prompt_tokens": length,
            "latency_ms": st["min_ms"],           # 以最小值为准
            "latency_ms_median": st["median_ms"],
            "spread_pct": st["spread_pct"],
            "tokens_per_s": round(length * args.batch / (st["min_ms"] / 1000), 1),
            "stats": st,
        }
        result["prefill"].append(entry)
        print(f"[bench] prefill {length:>5} token: {entry['latency_ms']:>8.2f} ms (min) / "
              f"{entry['latency_ms_median']:>8.2f} ms (median), 离散 {entry['spread_pct']:>5.1f}%  "
              f"({entry['tokens_per_s']:>8.1f} tok/s)")

    # ---- decode：差值法分离首 token 与后续单步 ----
    decode_ids, decode_mask = build_inputs(
        tokenizer, args.decode_prompt_len, args.batch, device
    )

    def generate(steps: int):
        with torch.inference_mode():
            return model.generate(
                input_ids=decode_ids,
                attention_mask=decode_mask,
                max_new_tokens=steps,
                do_sample=False,          # 贪心，去掉采样引入的抖动
                use_cache=True,
                pad_token_id=tokenizer.eos_token_id,
            )

    s_first = samples(lambda: generate(1), warmup=args.warmup,
                      repeats=args.repeats, device=device)
    s_full = samples(lambda: generate(args.decode_steps), warmup=args.warmup,
                     repeats=args.repeats, device=device)
    steps = max(args.decode_steps - 1, 1)
    tpot_min = (min(s_full) - min(s_first)) / steps
    tpot_median = (statistics.median(s_full) - statistics.median(s_first)) / steps

    # 非物理解护栏：decode 步数太少时，只多出几个 token 可除，
    # 噪声会盖过信号，甚至算出负数（2026-10-16 实测踩到过）。
    # 与其把垃圾数字写进 JSON，不如标记为无效。
    tpot_valid = tpot_min > 0
    if args.decode_steps < 8:
        print(f"[bench] 警告：decode 步数只有 {args.decode_steps}，"
              f"TPOT 的噪声会大于信号，建议 >=32")
    if not tpot_valid:
        print(f"[bench] 警告：TPOT 出现非物理解（{tpot_min * 1000:.2f} ms），"
              f"本次 decode 数据作废")

    result["decode"] = {
        "prompt_tokens": args.decode_prompt_len,
        "ttft_ms": round(min(s_first) * 1000, 2),
        "ttft_stats": stats(s_first),
        "tpot_ms": round(tpot_min * 1000, 2) if tpot_valid else None,
        "tpot_ms_median": round(tpot_median * 1000, 2) if tpot_valid else None,
        "tpot_valid": tpot_valid,
        "tokens_per_s": round(1.0 / tpot_min, 1) if tpot_valid else None,
        "total_ms_for_N_steps": round(min(s_full) * 1000, 2),
        "total_stats": stats(s_full),
    }
    if tpot_valid:
        print(f"[bench] decode TTFT {result['decode']['ttft_ms']:.2f} ms (min), "
              f"TPOT {result['decode']['tpot_ms']:.2f} ms (min) / "
              f"{result['decode']['tpot_ms_median']:.2f} ms (median) "
              f"({result['decode']['tokens_per_s']} tok/s)")
    else:
        print(f"[bench] decode TTFT {result['decode']['ttft_ms']:.2f} ms (min)，TPOT 无效")

    if device == "cuda":
        result["peak_memory_gb"] = round(torch.cuda.max_memory_allocated() / 1024**3, 3)
        print(f"[bench] 峰值显存 {result['peak_memory_gb']:.3f} GB")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{stamp}-{args.tag}.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[bench] 已写入 {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
