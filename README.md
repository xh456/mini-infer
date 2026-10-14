# mini-infer

从零实现的 LLM 推理引擎：手写 Transformer 前向、KV Cache 与分块显存管理、连续批处理调度、
int8/int4 量化与校准，并在此之上构建一套带严格评测与消融实验的 RAG/Agent 应用。

> **状态**：W1（环境、规范与基线）进行中
> **周期**：2026-10-14 → 2027-02-28

## 这个项目要回答的问题

> 待 W2 填写：一句话说明"解决了什么难题"，以及现成方案（HF transformers / vLLM）在这个场景下为什么不够。
> 这句话会成为简历条目和面试开场白的核心，写不出来就说明项目边界还没想清楚。

## 三层结构

| 层 | 内容 | 关键指标 |
|---|---|---|
| 训练层 | 语料清洗去重 → tokenizer → 预训练 100M 模型 → SFT | loss 曲线、消融结果 |
| 推理引擎层 | 手写 forward（RoPE / GQA / SwiGLU）、KV Cache、连续批处理、量化 | TTFT、decode 吞吐、峰值显存、perplexity 损失 |
| 应用层 | RAG/Agent（混合检索 + 重排 + 查询改写）+ 自建评测集 | recall@k、faithfulness、幻觉率、端到端 P95、每千 token 成本 |

## 目录结构

```
mini-infer/
├── src/mini_infer/      # Python 侧引擎与应用代码（W3 起填充）
├── csrc/                # C++ / CUDA 算子（W4 起填充）
├── bench/               # 基准测量脚本
│   └── results/         # 测量结果 JSON（唯一入库的结果形式）
├── scripts/             # 环境、模型、测量的命令行入口
├── tests/               # 冒烟测试与正确性测试
├── docs/                # 约定、实验模板、学习笔记、基建步骤
└── budget/              # 算力预算计划与花费台账
```

## 快速开始

云端（Linux GPU 实例）或本地 WSL：

```bash
bash scripts/bootstrap.sh cuda   # 本地 WSL 用 cpu
```

单独执行：

```bash
bash scripts/fetch_model.sh      # 拉取基线模型到 models/
python scripts/env_report.py     # 打印硬件与版本信息（JSON）
bash scripts/run_bench.sh        # 跑 HF 基线测量
python -m pytest tests/ -q       # 冒烟测试
```

手工步骤（装 Git、装 WSL、注册云平台）见 `docs/infra-setup.md`。

## 基线数据

工具链固定为：PyTorch 2.4.1 / transformers 4.44.2 / Qwen2.5-0.5B-Instruct。
所有对比必须在**同一硬件、同一软件版本**下完成，结果以 JSON 落在 `bench/results/`。

| 指标 | HF 基线 | 自研引擎 | 变化 |
|---|---|---|---|
| prefill 延迟（2048 token） | 待测 | — | — |
| decode 吞吐（batch=1） | 待测 | — | — |
| 峰值显存 | 待测 | — | — |

## 路线图

- [x] **W1** 环境、Git 规范、算力台账、第一条基线数据
- [ ] **W2** 架构与指标冻结（设计文档 + 验收口径）
- [ ] **W3–W6** 推理引擎核心：手写 forward，与 HF 对拍 logits
- [ ] **W7–W9** KV Cache、分块显存管理、连续批处理
- [ ] **W10–W12** 量化与性能调优（12/31 中期检查）
- [ ] **W13–W15** 从零训练 100M 小模型并用自研引擎推理
- [ ] **W16–W18** RAG/Agent 应用与评测体系（2/15 投递物料齐备）
- [ ] **W19–W20** 工程化、博客、演示与面试题库

## 开发约定

分支模型、提交信息规范与实验记录规范见 [`docs/conventions.md`](docs/conventions.md)。
