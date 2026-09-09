# 🚀 ModelFlow · 智模流水线

<div align="center">

**数学建模竞赛全自动工作流桌面应用**
**Automated CUMCM modeling pipeline — a desktop app for math modeling competitions**

[![Version](https://img.shields.io/badge/version-0.8.8-d4a930)](https://lxlrwxs.top/modelflow/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011%20x64-0078d4?logo=windows)](https://lxlrwxs.top/modelflow/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](requirements.txt)
[![Download](https://custom-icon-badges.demolab.com/badge/%E4%B8%8B%E8%BD%BD-Download-2da44e?style=flat-square&logo=download&labelColor=0d1117)](https://lxlrwxs.top/modelflow/)

</div>

---

> 一道赛题进来，可提交的论文 PDF 出来。
> One problem statement in — a submission-ready paper PDF out.

ModelFlow 把数学建模比赛的完整流程组织为**九个专业环节、三段式自动接力**：从赛题解析、建模求解到论文装配与审查，每个环节加载对应的专业 Skill 作为方法内核，产物逐级传递、环环自检。

ModelFlow organizes the full competition workflow into **9 professional stages in 3 automated relay phases** — from problem analysis and modeling to paper assembly and review. Each stage loads a dedicated Skill as its method core; artifacts are passed forward and verified at every step.

## ✨ 特性 / Features

- 🔄 **九步流水线 / 9-step pipeline** — 赛题解析 → 建模 → 求解 → 稳健性 → 论文 → 审查，全流程自动接力
- 🧠 **专业 Skill 内核 / Skill-driven stages** — 每个环节注入对应领域的建模方法论
- 🤖 **多模型接入 / Multi-model** — API 与本地 CLI 引擎并存，断网或没有本地模型时照样能跑
- 🔑 **自带 Key 即用 / Bring your own key** — 软件不售卖模型额度，填入自己的 API Key 直接运行，费用直接交给模型服务商
- 🖥️ **桌面体验 / Desktop-first** — 常驻托盘、实时输出、步骤级进度与产物管理
- 🛡️ **授权体系 / Licensing** — 基于 HMAC 的离线授权码机制，激活即用

## 📦 下载 / Download

访问下载页获取最新版安装包（Windows 10 / 11 x64）：
Visit the download page for the latest installer:

**→ [https://lxlrwxs.top/modelflow/](https://lxlrwxs.top/modelflow/)**

## 🧭 九个环节 / The 9 Stages

| # | 环节 Stage | 产物 Artifact |
|---|---|---|
| 01 | 问题分析 Problem Analysis | 问题分析.md · 建模报告 |
| 02 | 建模求解 Modeling & Solving | Q1_solve.py · 求解结果 |
| 03 | 编程实现 Implementation | 数值示例 · 误差校验 |
| ... | ... | ... |
| 09 | 论文改进循环 Paper Refinement | 可提交的论文 PDF |

## 🧰 技术栈 / Tech Stack

- **应用 / App**: Python 3.10+ · 单实例常驻托盘 · WebSocket 实时输出
- **打包 / Packaging**: PyInstaller SEA · Inno Setup 安装程序
- **分发 / Distribution**: 腾讯云 COS 私有桶 + 预签名下载 · 应用内自动更新
- **安全 / Security**: HMAC-SHA256 离线授权码 · 密钥构建期注入，不落仓库

## 🛠️ 开发 / Development

```bash
pip install -r requirements.txt
python run.py
```

构建发布包（需配置签名与 COS 凭据，见内部文档）：
Build a release (requires signing & COS credentials, see internal docs):

```bash
python make_release.py
```

## 📄 许可 / License

私有项目，保留所有权利。Private project — all rights reserved.