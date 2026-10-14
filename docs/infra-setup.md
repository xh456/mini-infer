# 基础设置：需要手工完成的部分

> 这些步骤需要管理员权限、实名认证或你的账号，无法由脚本代劳。
> 一次性做完，后面 19 周不用再碰。

## 1. 把 Git 加进 PATH（不需要管理员）

你的 Git 已装在 `D:\Git`，只是没进 PATH。**以普通用户身份**打开 PowerShell 执行：

```powershell
$gitCmd = 'D:\Git\cmd'
$userPath = [Environment]::GetEnvironmentVariable('Path','User')
if ($userPath -notlike "*$gitCmd*") {
    [Environment]::SetEnvironmentVariable('Path', "$userPath;$gitCmd", 'User')
    Write-Host '已写入用户 PATH，重开终端后生效'
} else {
    Write-Host '已存在，无需修改'
}
```

重开终端后验证：

```powershell
git --version
```

## 2. 配置身份与 SSH key

```powershell
git config --global user.name  "你的名字"
git config --global user.email "你的邮箱"
git config --global init.defaultBranch main
git config --global core.autocrlf false      # 换行符由 .gitattributes 统一管理

ssh-keygen -t ed25519 -C "你的邮箱"           # 一路回车即可
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | Set-Clipboard
```

把剪贴板内容粘到 GitHub → Settings → SSH and GPG keys → New SSH key。

## 3. 安装 WSL2（需要管理员 + 重启）

**管理员** PowerShell：

```powershell
wsl --install -d Ubuntu-22.04
```

重启后设置 Linux 用户名密码，然后：

```bash
sudo apt update && sudo apt install -y build-essential cmake ninja-build gdb clang git curl
```

关于 Python 版本，修正一下之前的说法：**Ubuntu 22.04 自带 Python 3.10，
直接用就行，不用额外装 3.11**。这个项目对 3.10 和 3.11 都安全，
而且云 GPU 镜像上最常见的也是 3.10。真正重要的是本地和云端版本一致。

## 4. VS Code

装 VS Code，然后装两个扩展：`WSL` 和 `Python`。
用 `code .` 从 WSL 里打开项目，这样终端、解释器、调试器都在 Linux 侧，
与你云端环境一致。

## 5. 本地 GPU 的定位（重要）

你的机器是 **NVIDIA GeForce MX330 / 2048 MiB / 驱动 532.03 / CUDA 12.1**。

它能干的事：跑 `nvidia-smi`、验证 CUDA 环境、小规模 kernel 正确性测试。

它**不能**干的事：任何有意义的性能测量。原因有两个——2 GB 显存装不下
0.5B 模型的 fp16 权重加 KV Cache；而且 MX330 属于 Pascal 架构（计算能力 6.1），
没有 Tensor Core，不支持 bf16，fp16 运算被大幅降频。

所以：**本地只做正确性，所有性能数字一律来自云 GPU。** 这是纪律，不是建议——
混用两种硬件产生的数字互相不可比。

## 6. 云 GPU 平台

选 2-3 家，不要贪多。优先满足三点：按量计费、有"无卡模式"、镜像里预装好 PyTorch。

| 平台 | 特点 |
|---|---|
| AutoDL | 常用选择，有"无卡模式"（约 ¥0.1/小时），镜像预装环境 |
| 恒源云 | 类似定位，可作为备用 |
| 百度 AI Studio | 每日赠送算力点，适合零成本的调试与试跑 |
| 阿里云 PAI-DSW / 天池 | 有免费额度与活动券 |
| 腾讯云 / 华为云 ModelArts | 新用户活动较多 |

实名认证是硬门槛，提前做完。**注意：学生认证需要在校学籍，你已毕业走不通**，
去走新用户注册礼、首充活动和平台活动券。

省钱三条纪律：

1. 装环境、下模型、传数据 -> 全部在**无卡模式**下完成，不要占用有卡时间；
2. 开发调试 -> 本地免费（本地 CPU / 免费额度），付费卡只跑长任务和正式测量；
3. 每次开机前写好实验清单，一次开机连续跑完，跑完立刻关机并记进台账。

预算分配见 [`../budget/PLAN.md`](../budget/PLAN.md)，花费记进
[`../budget/gpu_budget.csv`](../budget/gpu_budget.csv)。

## 7. 第一次推送

先在 GitHub 上建一个**公开**仓库（名字 `mini-infer`，不要勾选任何初始化文件），然后：

```powershell
cd D:\dev\mini-infer
git init
git add -A
git commit -m "chore: 初始化仓库与 W1 脚手架"
git branch -M main
git remote add origin git@github.com:<你的用户名>/mini-infer.git
git push -u origin main
```

用公开仓库而不是私有：真实的、带时间戳的提交记录本身就是资产。
面试官看到连续几周每天都有提交，和一个最后一天传上去的压缩包，判断完全不同。
