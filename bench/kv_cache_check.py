#!/usr/bin/env python3
"""经验校验 KV Cache 显存公式。

公式（推导见 docs/w1-notes.md 第 2 节）：

    bytes = 2(K与V) × 层数 × KV头数 × head_dim × dtype字节 × 序列长度 × batch

做法：用真实模型跑一次前向，把 past_key_values 里所有张量的字节数加起来，
与公式预测值逐项对比。两者必须完全相等——不等就说明公式漏了项
（最常见的是把 GQA 的 KV 头数写成了注意力头数）。

这个脚本的用途不是"跑出数"，而是让你能在自己推导完之后立刻验证对错。

用法：
    python bench/kv_cache_check.py --model models/Qwen2.5-0.5B-Instruct --seq-lens 128,512
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import torch


def flatten_cache(past) -> list[torch.Tensor]:
    """把不同 transformers 版本的缓存对象统一成张量列表。"""
    if past is None:
        return []
    # 新版 DynamicCache：key_cache / value_cache 是逐层的列表
    tensors: list[torch.Tensor] = []
    for attr in ("key_cache", "value_cache"):
        value = getattr(past, attr, None)
        if isinstance(value, (list, tuple)):
            tensors.extend(t for t in value if isinstance(t, torch.Tensor))
    if tensors:
        return tensors
    # 旧版：tuple of (k, v)
    for layer in past:
        if isinstance(layer, (tuple, list)):
            tensors.extend(t for t in layer if isinstance(t, torch.Tensor))
        elif isinstance(layer, torch.Tensor):
            tensors.append(layer)
    return tensors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--seq-lens", default="128,512")
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--dtype", default="float32", choices=["float16", "float32"])
    parser.add_argument("--tag", default="kv-cache-check")
    parser.add_argument("--out-dir", default="bench/results")
    args = parser.parse_args()

    if not (Path(args.model) / "config.json").is_file():
        print(f"[kv] 找不到模型：{args.model}，先跑 scripts/fetch_model.sh")
        return 2

    from transformers import AutoModelForCausalLM

    dtype = getattr(torch, args.dtype)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=dtype).eval()
    cfg = model.config

    layers = cfg.num_hidden_layers
    kv_heads = getattr(cfg, "num_key_value_heads", cfg.num_attention_heads)
    head_dim = getattr(cfg, "head_dim", cfg.hidden_size // cfg.num_attention_heads)
    itemsize = torch.tensor([], dtype=dtype).element_size()

    print(f"[kv] layers={layers} kv_heads={kv_heads} head_dim={head_dim} "
          f"dtype={args.dtype}({itemsize}B) batch={args.batch}")

    rows = []
    for seq_len in [int(x) for x in args.seq_lens.split(",")]:
        input_ids = torch.randint(0, cfg.vocab_size, (args.batch, seq_len))
        with torch.inference_mode():
            out = model(input_ids=input_ids, use_cache=True)
        tensors = flatten_cache(out.past_key_values)
        actual = sum(t.numel() * t.element_size() for t in tensors)
        predicted = 2 * layers * kv_heads * head_dim * itemsize * seq_len * args.batch
        rows.append({
            "seq_len": seq_len,
            "batch": args.batch,
            "cache_tensors": len(tensors),
            "actual_bytes": actual,
            "actual_mib": round(actual / 1024**2, 3),
            "predicted_bytes": predicted,
            "predicted_mib": round(predicted / 1024**2, 3),
            "match": actual == predicted,
        })
        print(f"[kv] seq={seq_len:>5}  实测 {actual:>10} B ({actual / 1024**2:>7.3f} MiB)  "
              f"公式 {predicted:>10} B ({predicted / 1024**2:>7.3f} MiB)  "
              f"{'一致' if actual == predicted else '不一致'}")

    result = {
        "tag": args.tag,
        "model": args.model,
        "layers": layers,
        "kv_heads": kv_heads,
        "head_dim": head_dim,
        "dtype": args.dtype,
        "batch": args.batch,
        "rows": rows,
    }
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{args.tag}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[kv] 已写入 {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
