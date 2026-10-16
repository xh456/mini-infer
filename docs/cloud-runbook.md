# 云端实例操作手册

> 目的：别把钱花在重复劳动上。每次上云前过一遍，不要临场想步骤。

## 三条铁律

1. **开机前先写清单**：这次要跑什么、预期产出什么文件。没有清单不开机。
2. **装环境、下数据用"无卡模式"**（约 ¥0.1/小时）。有卡时间只用来跑测量和训练。
3. **关机后立刻补一行** `budget/gpu_budget.csv`，事后补账一定会忘。

## 卡型与计费

| 用途 | 建议卡型 | 参考单价 | 说明 |
|---|---|---|---|
| P2/P3 引擎测量、量化实验 | 4090 24G / 3090 24G | ¥1.2-2.2/小时 | 0.5B~7B 量化推理够用 |
| P5 训 100M 小模型 | 单卡 4090 | ¥2/小时 | 8-12 小时可完成，约 ¥20-25 |
| SWE-bench 类评测（若转方向） | **不需要 GPU** | ¥0.3-1/小时（CPU 机型） | 评测是 CPU + Docker 密集，用 GPU 纯属浪费 |

## 一次标准会话

阶段 A（无卡模式或本地）先把材料备齐：

```bash
git clone https://github.com/xh456/mini-infer.git ~/mini-infer
cd ~/mini-infer
```

若 GitHub 打不开，改从本地同步（命令见 w1-checklist.md 的 tar 管道一节）。

阶段 B（切到有卡模式）一条命令建环境：

```bash
PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple bash scripts/bootstrap.sh cuda
```

bootstrap 会先探测 download.pytorch.org，不通则自动切阿里云 cu121 镜像
（已验证该镜像同时提供 cp310 与 cp311 轮子）。

阶段 C 正式测量：

```bash
REQUIRE_QUIET=1 PROMPT_LENS=128,512,2048 DECODE_STEPS=128 TAG=cuda-baseline bash scripts/run_bench.sh
```

专用实例的 loadavg 应接近 0；`REQUIRE_QUIET=1` 会让机器不静默时直接拒绝出数。

阶段 D 回传并关机：确认 `bench/results/` 里有新 JSON，回传本地，立刻关机，记台账。

## 这一轮（W1 Day 6）要拿到的东西

1. 一份 `bench/results/*-cuda-*.json`，四要素完整（GPU 型号、显存、torch/CUDA 版本）
2. 同一会话内**背靠背连测两次**，两次 min 值差异在 5% 以内
   —— 这是 W1 验收清单里唯一还没打勾的硬指标
3. 台账里一行真实花费

预期花费：4-6 小时 4090 约 **¥8-15**。这是整个项目最便宜也最关键的一次测量。

## 常见坑

- **别在共享/竞价实例上做正式测量**。CPU 会被人抢，和本机遇到的是同一个问题：噪声比信号大。
- **测量期间不要同时装包或下模型**。I/O 会污染 decode 的带宽测量。
- **两次测量之间不要改任何东西**（包括 pip 升级）。W1 要验证的就是"同样的东西跑两遍结果一样"。
- **别忘了关机**。忘关一晚约 ¥15-20，等于白跑好几次实验。
