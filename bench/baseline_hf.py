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


def timeit(fn, *, warmup: int, repeats: int, device: str) -> float:
    """返回单次平均耗时（秒）。warmup 之后的测量才作数。"""
    for _ in range(warmup):
        fn()
    sync(device)
    started = time.perf_counter()
    for _ in range(repeats):
        fn()
    sync(device)
    return (time.perf_counter() - started) / repeats


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
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--dtype", default="auto", choices=["auto", "float16", "float32"])
    parser.add_argument("--tag", default="hf-baseline")
    parser.add_argument("--out-dir", default="bench/results")
    args = parser.parse_args()

    if not (Path(args.model) / "config.json").is_file():
        print(f"[bench] 找不到模型：{args.model}，先跑 scripts/fetch_model.sh", file=sys.stderr)
        return 2

    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if args.dtype == "auto":
        dtype = torch.float16 if device == "cuda" else torch.float32
    else:
        dtype = getattr(torch, args.dtype)

    torch.manual_seed(0)  # 固定随机性，保证可复现

    print(f"[bench] device={device} dtype={dtype} batch={args.batch}")

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

        latency = timeit(prefill, warmup=args.warmup, repeats=args.repeats, device=device)
        entry = {
            "prompt_tokens": length,
            "latency_ms": round(latency * 1000, 2),
            "tokens_per_s": round(length * args.batch / latency, 1),
        }
        result["prefill"].append(entry)
        print(f"[bench] prefill {length:>5} token: {entry['latency_ms']:>8.2f} ms  "
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

    t_first = timeit(lambda: generate(1), warmup=args.warmup,
                     repeats=args.repeats, device=device)
    t_full = timeit(lambda: generate(args.decode_steps), warmup=args.warmup,
                    repeats=args.repeats, device=device)
    tpot_s = (t_full - t_first) / max(args.decode_steps - 1, 1)

    result["decode"] = {
        "prompt_tokens": args.decode_prompt_len,
        "ttft_ms": round(t_first * 1000, 2),
        "tpot_ms": round(tpot_s * 1000, 2),
        "tokens_per_s": round(1.0 / tpot_s, 1) if tpot_s > 0 else None,
        "total_ms_for_N_steps": round(t_full * 1000, 2),
    }
    print(f"[bench] decode TTFT {result['decode']['ttft_ms']:.2f} ms, "
          f"TPOT {result['decode']['tpot_ms']:.2f} ms "
          f"({result['decode']['tokens_per_s']} tok/s)")

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
