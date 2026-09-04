# ModelFlow 数模软件 · 全量理解报告（2026-09-01）

## 一、软件是什么

**ModelFlow 智模流水线**——数学建模竞赛全自动流水线桌面应用（当前版本 0.7.6），内置 9 步竞赛流水线与 10 套学术/科研流水线。核心链路：赛题分析 → 建模 → 编程 → 图表 → 架构图 → 逻辑复核 → 论文撰写 → LaTeX 编译 PDF → 改进循环。纯桌面形态：pywebview + WebView2 原生窗口，无浏览器依赖，关窗即退出。

## 二、目录全景

```
数学建模工作流软件/
├─ app_launch.py        桌面启动入口（pywebview 窗口 + 单实例 + uvicorn 后台线程）
├─ run.py / 启动ModelFlow.bat   源码运行入口
├─ app/                 后端 FastAPI（main 830 行 / jobs 2043 行 / db / llm / tools / ws / updater / licensing / paths / version）
├─ static/              前端 SPA（app.js 2666 行单文件 + index/new/run/settings.html + new.js + providers-catalog.js + 99 家供应商 logo + MiSans 字体）
├─ skills/              291 文件 / 127 个 SKILL.md / 86 个顶层技能（随包分发的步骤指令库）
├─ _utils_py/           78 项确定性校验脚本 + 规则文档（Windows 无 bash 的 py 等价实现）
├─ _templates/          14 套竞赛 LaTeX 模板（cumcm/mcm/mathorcup/huawei 等，.cls+.tex 骨架）
├─ workspaces/          流水线运行工作区（job_{id}：CLAUDE.md、PROBLEM_ANALYSIS.md、main.tex/pdf、_sessions/ 等）
├─ modex-data/          运行时数据根（modex.db、license.json、uploads/、export/、update/）
├─ server/              授权服务端 license_server.py（云部署 /opt/mflic/，8807 端口）
├─ make_release.py      发版打包（版本号→PyInstaller onedir→Inno Setup→latest.json）
├─ installer.iss / installer_upgrade.iss   Inno 安装器（装机版 / 静默升级版）
├─ upload_cos.py        腾讯云 COS 上传（exe + latest.json + 前端哈希门禁下载页）
├─ download_index.html  旧 VPS 时代下载页（已弃用）
├─ HANDOFF.md / TRANSFER.md / HANDOFF-COS部署交接.md   三份交接文档
├─ _study/                 UI 学习参考（历史留档）
├─ dist/ dist_app/ dist_build/ build/   PyInstaller 产物
└─ release/             发布产物（0.7.4/0.7.5 setup.exe + latest.json + index.html）
```

## 三、后端架构（app/）

- **main.py**：FastAPI 主入口，约 60 个路由。授权锁中间件（仅 frozen 模式复未激活 403 封锁除 /static、/api/license 外全部 API）；工作流 CRUD；产物文件浏览/下载（防路径穿越）；zip/Word 导出；上传白名单（30+ 扩展名，500MB 上限）；在线更新 API；运行时检测/一键安装；流水线元数据；提示词定制 API；供应商/图片预设 CRUD；用量查询代理（带 SSRF 内网拦截）；科研工具 REST 封装。
- **jobs.py**（核心，2043 行）：
  - **11 条流水线定义**：competition 9 步 + 10 套学术流水线，每步含 key/label/skill/out/checkpoint/role/check 自检脚本。
  - **CLI 执行器 run_step_via_cli**：以工作区为 cwd 启动 claude CLI（`-p --output-format stream-json --verbose --dangerously-skip-permissions`）复凭据经 ANTHROPIC_API_KEY/AUTH_TOKEN/BASE_URL 环境变量透传，stream-json 逐事件解析、工具调用实时推 WS、45 分钟超时树杀、逐轮日志 `_turn_logs/` + 完整会话留痕 `_sessions/`。找不到 CLI 直接失败不降级。
  - **prepare_cli_workspace**：每步重写工作区 CLAUDE.md（SKILL 全文 + 图表配置 MH_* 标记 + 环境锚点 + 用户硬条款 + 能力清单契约摘要 + 上传文件索引）；搬入 _templates/（按赛项关键词匹配）与 _utils/ 工具链；写 .env_skill（MIN_FIGURES/MIN_TABLES/MIN_MODELS/MAX_PAGES 硬目标）。
  - **execute_job**：顺序执行，支持真暂停/恢复（线程事件）、断点续跑、人工检查点、review 步骤 disclose/block 双策略、compile/improve 后本地兜底 xelatex 编译（3 轮）、每步自检脚本 rc 语义（0 过 / 1 阻断 / 2 跳过）。
  - resolve_python / find_claude_cli / detect_runtimes / winget 白名单静默安装；上传文件智能预处理（PDF/docx/xlsx/pptx 抽文本、图片视觉 OCR、PDF 扫描页 PyMuPDF 渲染再 OCR、视频 ffprobe+抽帧+抽音轨）。
- **llm.py**：OpenAI 兼容 + Anthropic 双协议客户端（双 header 兼容三方网关）。
- **db.py**：SQLite 六表（workflows/settings/api_presets/skill_overrides/image_presets + sequence）。
- **licensing.py**：机器指纹（MachineGuid→wmic UUID→MAC，SHA256 前 32 位）+ HMAC 令牌离线校验；激活落盘 license.json；管理员码不限机。
- **updater.py**：latest.json 清单检查 → 流式下载 SHA-256 校验 → 分形态替换（装机版 Inno 静默升级 /VERYSILENT /MERGETASKS=keepsl /FORCECLOSEAPPLICATIONS + --relaunch 重启；便携版二段式 bat 原地替换）。0.7.6+ 走 /api/update-download 换 COS 预签名 URL（10 分钟有效）。
- **tools.py**：科研工具集 REST 封装 _utils_py 7 个工具（scholar_fetch 四源文献检索/gpt_image 生图/reviewer_client 评审/paper_data_check 数据查真/tikz_vision_check/derive_reference_from_docx/md_to_docx），退出码语义 0/2/其他。
- **ws.py**：WebSocket 按工作流隔离推送，跨线程 call_soon_threadsafe 投递主 loop。
- **paths.py**：frozen/installed 三形态路径布局（源码=modex-data/，装机=安装根 data/，INSTALLED 用 unins000.exe+注册表检测）。

## 四、前端（static/）

app.js 单文件 SPA，hash 路由四视图：
- **list**：工作流列表 + 统计卡 + 3s 轮询。
- **new**：国赛大卡 + 22 项赛事卡片墙 + 学术流水线网格；竞赛表单（赛项/题号/输出格式/审查模式/页数/丰满模式/逻辑复核/流程图引擎/配色/高级数量硬目标/上传/视觉质检开关/AI 声明/人工检查点/改进循环/模型分配）；配色/版式 SVG 实时预览弹窗。
- **run**：步骤时间线（CLI 徽标 + 提示词定制入口）+ WebSocket 实时日志（轻量追加 + 1.2s 节流刷新）+ 产物文件分组浏览/预览/下载/上传 + 产物编辑器（文件树 + AI 润色）。
- **settings**：模型预设（供应商目录弹窗：搜索/分类/图标/模型列表拉取/模型映射/认证字段）+ 图片生成预设 + 软件更新 + 本地运行时一键装 + LaTeX 检测。
- 启动链：授权锁屏 → 启动准备遮罩 8 项自检逐行点亮 → 进入主界面。

## 五、技能库与校验脚本（关键契约）

- **skills/**：127 个 SKILL.md 是流水线的灵魂——后端把 SKILL.md 作为该步 system prompt 经 CLAUDE.md 注入 CLI。jobs.py 引用的 20 个 skill 全部存在无缺失。跨技能契约 **CAPABILITY_CHECKLIST.json** 由 comp-prob-analysis 产出、9 处消费。
- **_utils_py/**：确定性对账脚本（capability_audit/modeling_coverage_check/paper_claim_check/facts_audit/leakage_audit/data_ingest_check/compile_check/figure_check/drawio_check 等）+ 配方规则文档 + vision 质检。硬底线：数据图 ≥3；用户显式 MIN_* > 0 才硬阻塞。
- **_templates/**：14 套竞赛模板，ensure_template_assets 按 \documentclass 名称匹配注入 cls/sty。

## 六、打包发布与授权闭环

```
源码 → make_release.py（PyInstaller onedir → dist_app/ModelFlow → Inno Setup → release/ModelFlow-{v}-setup.exe + latest.json）
     → upload_cos.py（上传私有 COS 桶 modelflow-1447874637/ap-guangzhou）
     → 下载页 https://lxlrwxs.top/modelflow/（Cloudflare Pages + Functions）
```

- 授权：5 位码（字母表去 I/O/0/1），一码一机 + 一机一码复HMAC 令牌本地离线校验；服务端三代演进（VPS license_server.py → Cloudflare Functions + D1 → 私有桶 + 预签名 URL + 防爆破限速）。
- COS 桶私有：exe 直链 403，verify 通过后 Functions 用 COS 密钥生成 5 分钟预签名 URL；SignKey = HMAC-SHA1(SecretKey, sign_time)（踩坑：非官方文档写法）。
- 版本 0.7.6 打包中；0.7.5 及更早的软件内更新在 COS 私有化后会失败，需手动重装 0.7.6+。

## 七、运行时落盘约定（workspaces/job_{id}/）

CLAUDE.md（每步重写）、.env_skill（硬目标）、user_data/（上传资料 + 抽取文本 + OCR）、_utils/（工具链副本）、_templates/（赛项模板副本）、各步产物（PROBLEM_ANALYSIS.md / MODELING_REPORT.md / RESULTS.md / FIGURES.md / ARCHITECTURE.md / LOGIC_REVIEW.md / main.tex / main.pdf / IMPROVED_PAPER.md）、_sessions/ + _turn_logs/（CLI 会话留痕）、compile_log.txt。

## 八、关键风险与坑（交接文档 + 代码实证）

1. HMAC SECRET 硬编码在 app/licensing.py（客户端可提取伪造 token）——离线校验方案的固有弱点。
2. 前端哈希门禁只是简单版，0.7.5 及以前更新链路在私有桶后已断。
3. make_release --skip-build 沿用旧 exe；lzma2 压缩使字节搜索验证无效。
4. 打包必须用系统 Python312（含 PyInstaller 6.22.2 + 科学计算栈）；减重红线：只排除 numba/PySide6/jedi/IPython/pytest/sklearn。
5. Windows 无 bash：.sh 自检自动映射同名 .py；CLI 相对路径必须 resolve() 绝对化。
6. 源码目录非 git 仓库；并行 AI 会话改文件需先重新 Read。
