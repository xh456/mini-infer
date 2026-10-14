# W1 验收清单（10/14 - 10/20）

**远端仓库**：https://github.com/xh456/mini-infer

> 这份清单是活的：每完成一项就勾掉并提交。提交记录本身就是"计划、执行、复盘"的证据。

## 我已经替你完成的部分

- [x] 项目目录结构（`src/` `csrc/` `bench/` `scripts/` `tests/` `docs/` `budget/`）
- [x] `README.md`（三层结构、路线图、基线数据表占位）
- [x] `.gitignore` / `.gitattributes`（权重、数据、编译产物不入库；脚本强制 LF）
- [x] `docs/conventions.md`（分支模型、提交规范、复现性红线）
- [x] `docs/experiment-template.md`（四要素 + 测量纪律）
- [x] `docs/infra-setup.md`（Git PATH、SSH、WSL2、云平台、首次推送）
- [x] `docs/w1-notes.md`（KV Cache 公式推导、prefill/decode 瓶颈分析）
- [x] `scripts/bootstrap.sh`（一条命令重建环境）
- [x] `scripts/fetch_model.sh`（走 ModelScope / HF 镜像拉权重）
- [x] `scripts/env_report.py`（输出四要素）
- [x] `scripts/run_bench.sh` + `bench/baseline_hf.py`（基线测量，含 TTFT/TPOT/显存）
- [x] `tests/test_smoke.py`（环境、前向形状、贪心解码可复现）
- [x] `budget/PLAN.md` + `budget/gpu_budget.csv`（¥300 分配与台账）

## 需要你亲手做的部分

### Day 1（10/14）

- [x] 把 `D:\Git\cmd` 加进 PATH（见 `docs/infra-setup.md` 第 1 节）
- [x] 配置 git 身份 + 生成 SSH key 并贴到 GitHub
- [x] 在 GitHub 建公开仓库 `mini-infer`
- [x] `git init` 并推送第一批提交（首个提交 `892882c`）

> Day 1 已全部完成。环境勘察的结论记在下面，避免后面重复踩坑：
> - Git 已装在 `D:\Git`（2.56.0），无需重新安装
> - 显卡为 MX330 / 2GB / 计算能力 6.1，只做正确性验证，性能数字一律来自云 GPU
> - 系统级 `core.autocrlf=true` 已被 `.gitattributes` 与仓库级配置双重覆盖，脚本恒为 LF

### Day 2（10/15）

- [ ] 装 WSL2 + Ubuntu 22.04（管理员权限，需重启）
- [ ] WSL 里 `sudo apt install build-essential cmake ninja-build gdb clang`
- [ ] 在 WSL 里克隆仓库到 `~/mini-infer`（**不要**把仓库放进 `/mnt/d`，跨文件系统 IO 会慢十倍）

> 注意这里有个取舍：仓库主副本放 `D:\dev\mini-infer`（Windows 侧，方便你现在用），
> WSL 里干活时用 `~/mini-infer` 的克隆。两边用 git 同步，不要用同一个工作区跨系统访问。

### Day 3（10/16）

- [ ] `bash scripts/bootstrap.sh cpu`，观察是否一次跑通
- [ ] 记录第一个卡点（哪一步报错、报什么）——这是最值钱的复盘素材

### Day 4（10/17）

- [ ] 注册 2-3 家云 GPU 平台并完成实名认证
- [ ] 领取新用户券，把券的面额和有效期记进 `budget/gpu_budget.csv` 备注列
- [ ] 建立台账使用习惯：开机前记录计划，关机后补上实际耗时与花费

### Day 5（10/18）

- [ ] 在云实例上（无卡模式）跑通 `bash scripts/bootstrap.sh cuda`
- [ ] 确认 `python scripts/env_report.py` 能正确报出云端 GPU 型号与显存

### Day 6（10/19）

- [ ] 有卡模式下跑 `TAG=hf-baseline bash scripts/run_bench.sh`
- [ ] 换一台新实例复跑一次，两次数字差异应在 5% 以内（超出说明测量方法有问题）
- [ ] 关机，把花费记进台账

### Day 7（10/20）

- [ ] 手推一遍 KV Cache 显存公式（不许看笔记）
- [ ] 通读 nanoGPT 的 `model.py`（约 300 行）并写批注
- [ ] 读 vLLM 的 PagedAttention 论文摘要部分
- [ ] 用一分钟讲清"连续批处理为什么提升吞吐"，讲给自己听
- [ ] 写 W1 复盘：花了多久、卡在哪、明天怎么避免

## W1 完成标准

能同时回答"是"才算过关：

1. 一台全新的机器上，一条命令能重建环境并跑通冒烟测试？
2. GitHub 上有真实的、带时间戳的提交记录？
3. 有至少一份带完整四要素的基线 JSON？
4. 同样参数换机器复跑，数字能对上（5% 内）？
5. 能不看笔记手推 KV Cache 公式？
6. 账上花了多少钱，心里有数？
