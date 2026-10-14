"""W1 冒烟测试：环境可用、模型在位、前向能跑、解码可复现。

这里不做性能断言（性能属于 bench/），只保证"这台机器现在确实能干活的"。
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
import torch

MODEL_DIR = Path(os.environ.get("MODEL", "models/Qwen2.5-0.5B-Instruct"))
MODEL_READY = (MODEL_DIR / "config.json").is_file()


def test_torch_present() -> None:
    assert torch.__version__


def test_reports_device() -> None:
    # 不要求有 GPU，但必须能明确回答有没有
    assert isinstance(torch.cuda.is_available(), bool)


@pytest.mark.skipif(not MODEL_READY, reason="模型未下载，先执行 scripts/fetch_model.sh")
def test_model_forward_shape() -> None:
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    model = AutoModelForCausalLM.from_pretrained(str(MODEL_DIR)).eval()
    encoded = tokenizer("hello", return_tensors="pt")
    with torch.inference_mode():
        out = model(**encoded)
    assert out.logits.shape[0] == 1
    assert out.logits.shape[1] == encoded["input_ids"].shape[1]
    assert out.logits.shape[-1] == model.config.vocab_size


@pytest.mark.skipif(not MODEL_READY, reason="模型未下载，先执行 scripts/fetch_model.sh")
def test_greedy_decode_is_deterministic() -> None:
    """贪心解码两次结果必须完全一致 —— 这是后续与自研引擎做数值对拍的前提。"""
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    model = AutoModelForCausalLM.from_pretrained(str(MODEL_DIR)).eval()
    encoded = tokenizer("The capital of France is", return_tensors="pt")

    def run():
        with torch.inference_mode():
            return model.generate(
                **encoded,
                max_new_tokens=8,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )

    assert torch.equal(run(), run())
