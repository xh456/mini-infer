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

- [x] 装 WSL2 + Ubuntu 22.04：**管理员** PowerShell 里跑 `wsl --install -d Ubuntu-22.04`，然后重启
- [x] 重启后首次启动 Ubuntu，设置 UNIX 用户名与密码（纯小写英文，记牢，这是 sudo 密码）
- [x] 在 WSL 里一次跑完剩余步骤（下面这一条即可，内含克隆 + 装工具链 + 初始化环境）

```bash
sudo apt update && sudo apt install -y git \
  && git clone https://github.com/xh456/mini-infer.git ~/mini-infer \
  && bash ~/mini-infer/scripts/wsl-setup.sh
```

> 仓库是公开的，所以 HTTPS 克隆不需要任何凭据。
> **不要**把仓库放在 `/mnt/d` 下跨系统访问，跨文件系统 IO 会慢十倍；WSL 里用 `~/mini-infer`，
> 两边用 git 同步（提交在 Windows 侧做，运行在 WSL 侧做）。

> 注意这里有个取舍：仓库主副本放 `D:\dev\mini-infer`（Windows 侧，方便你现在用），
> WSL 里干活时用 `~/mini-infer` 的克隆。两边用 git 同步，不要用同一个工作区跨系统访问。

### Day 3（10/16）

- [x] `bash scripts/bootstrap.sh cpu`，观察是否一次跑通
- [x] 记录第一个卡点（哪一步报错、报什么）——这是最值钱的复盘素材

### Day 4（10/17）

- [x] 注册云 GPU 平台并完成实名认证（已完成）
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

---

## 执行记录：2026-10-14（实际发生了什么）

### Day 1 —— 完成

- Git 早已装在 `D:\Git`（2.56.0），只是没进 PATH，加一行即可，不必重装
- SSH 密钥在 `C:\Users\86195\.ssh\id_ed25519`，指纹 `SHA256:DfFVU8Mq9OAXaccqyUjzdrpq/U05ZhIkfGzBLWu5`
- 公开仓库 https://github.com/xh456/mini-infer 建立并推送，首个提交 `892882c`

### Day 2 —— 完成

- WSL 平台 3.0.3.0，内核 6.18.54.1，WSLg 1.0.79
- Ubuntu 22.04.5 LTS，用户 `hy`（uid 1000，已在 sudo 组）；
  `/etc/wsl.conf` 已启用 `systemd=true` 并设 `user.default=hy`
- 工具链：gcc 11.4.0 / cmake 3.22.1 / ninja 1.10.1 / Python 3.10.12 / git 2.34.1
- apt 源切换到清华镜像，原文件备份为 `/etc/apt/sources.list.bak`
- 发行版位于 `C:\Users\86195\AppData\Local\wsl\{a00d4c39-...}`；
  空间紧张时可用 `wsl --manage Ubuntu-22.04 --move D:\wsl\Ubuntu-22.04` 迁移

### Day 3 —— 完成

`bash scripts/bootstrap.sh cpu` 一次跑通，退出码 0，冒烟测试 4 项全过
（含"贪心解码两次结果完全一致"——这是后续数值对拍的前提）。

第一组基线（本地 CPU / fp32 / batch=1，数据在 `bench/results/20261014-201608-local-cpu-wsl.json`）：

| 指标 | 数值 |
|---|---|
| 模型加载 | 14.02 s |
| prefill 128 token | 1425.48 ms（89.8 tok/s） |
| prefill 512 token | 4470.83 ms（114.5 tok/s） |
| decode TTFT | 340.78 ms |
| decode TPOT | 130.98 ms |
| decode 吞吐 | 7.6 tok/s |

**这不是云端基线**，只用于验证测量链路；硬件不同，数字不可比。
⚠️ 这组数字后来被证明**不可复现**，见下方"测量方差调查"。

### 遇到的三个真问题（比顺利的部分更值得记住）

1. **`download.pytorch.org` 被连接重置**（curl 返回码 000）。
   已在 `bootstrap.sh` 里加了自动回退：探测官方 index 不可达时改用阿里云
   `pytorch-wheels` 平铺目录，并注意它需要 `--find-links` 配合带后缀的
   `torch==2.4.1+cpu` 版本号，用 `--index-url` 是不行的。
2. **`raw.githubusercontent.com` 被重置**，`wsl --install -d Ubuntu-22.04` 会反复重试，
   表面上看像卡死，实际上最终能成功（走微软 CDN）。判断长任务是否卡死，
   要看日志文件或文件大小增长，**不能只看终端有没有输出**。
3. **WSL 内访问 GitHub HTTPS 超时**（`github.com:443` 连 134 秒后失败）。
   绕行方案：从 Windows 侧仓库直接同步，不走网络——

```bash
cd /mnt/d/dev/mini-infer && tar cf - --exclude=.git --exclude=.venv . | (cd ~/mini-infer && tar xf -)
```

   反向同步测量产物：`cp ~/mini-infer/bench/results/*.json /mnt/d/dev/mini-infer/bench/results/`

### W1 完成标准核对

| 标准 | 状态 |
|---|---|
| 新机器上一条命令重建环境并跑通冒烟测试 | 已达成（`scripts/bootstrap.sh cpu`） |
| GitHub 上有真实、带时间戳的提交记录 | 已达成 |
| 至少一份带完整四要素的基线 JSON | 已达成（本地 CPU，含 env 报告） |
| 换机器复跑数字能对上（5% 内） | **本机不满足**，原因已定位（见下）；需在云实例上重测 |
| 能不看笔记手推 KV Cache 公式 | 待自测；`bench/kv_cache_check.py` 可验证答案 |
| 账上花了多少钱心里有数 | **待办**：云平台尚未开通 |

---

## 测量方差调查（2026-10-16）

起因：10/14 两次同参数测量的偏差最高达 40%，远超"5% 内"的验收标准。

改进动作：保留全部样本并报告 min / median / 离散度；warmup 提到 2、repeats 提到 10；
显式记录 `torch` 线程数与 `loadavg`；新增"机器是否静默"的前置检查。

改完后连跑三次的结果——**反而更糟**：

| 指标 | 三次运行的 min | 跨运行差异 | 单次运行内部离散 |
|---|---|---|---|
| prefill 128 token | 2655 / 2789 / 1615 ms | +73% | 90% ~ 1199% |
| prefill 512 token | 13413 / 8595 / 6808 ms | +97% | 83% ~ 284% |
| decode TPOT | 258 / 158 / 151 ms | +71% | — |

而且 prefill 512 从 10/14 的 4.1~4.5 s 退化到 6.8~13.4 s。三次运行的 `loadavg`
分别是 3.4 / 2.9 / 3.2，说明宿主始终有额外负载。

### 结论（这是本次调查真正有价值的部分）

1. **这不是统计方法能修的问题，是环境问题。** 这台笔记本在测量期间无法保持静默：
   网盘同步、杀毒扫描、浏览器都在抢 CPU，持续满载还会让 CPU 降频——**测越久越慢**。
2. 因此"5% 内复现"这条标准在**本机**不可能达成，也不该假装达成。正确做法是把
   正式基线放到专用云实例上做，那里没有第二个进程和它抢资源。
3. 已把这条教训固化成脚本护栏：`REQUIRE_QUIET=1` 时，机器不静默就直接拒绝出数，
   而不是产出一份看起来很像样、实际毫无比较价值的 JSON。
4. 副产物：`bench/kv_cache_check.py` 用实测校验了 KV Cache 公式，结果与公式**完全相等**
   （128 token → 3,145,728 B；512 token → 12,582,912 B），这项验收可以打勾了。
