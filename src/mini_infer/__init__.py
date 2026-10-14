"""mini-infer：从零实现的 LLM 推理引擎。

模块规划（W3 起填充）：
    model_ref.py     PyTorch 参考实现，用于与自研算子对拍
    cache.py         KV Cache 与分块显存管理
    scheduler.py     连续批处理调度器
    quant.py         int8 / int4 量化与校准
"""

__version__ = "0.0.1"
