# ModelFlow 智模流水线 · 全量理解报告（0.8.6 · 2026-09-06）

> 本文基于当前工作区源码逐块读证，替代 2026-09-01 的 0.7.6 版报告。
> 版本差异已单独成章（第八章），旧报告中已失效的结论不再沿用。

---

## 一、一句话定位

**ModelFlow 智模流水线** —— 数学建模国赛全自动流水线桌面应用（当前 **0.8.6**）。
上传赛题/数据 → AI（Claude Code CLI）按流水线逐步跑完 → 产出可提交的 LaTeX/PDF 论文。
纯桌面形态：pywebview + WebView2 原生窗口，无浏览器依赖，关窗最小化到托盘。

**技术栈**：Python 3.12 + FastAPI + uvicorn（后端）+ 原生 JS 单文件 SPA（前端，3714 行）+ pywebview（桌面壳）+ SQLite（数据）+ Claude Code CLI（执行引擎）。

---

## 二、目录全景（实测）

```
数学建模工作流软件/                    ← Git 仓库（3 次提交，2026-08-22 起）
├─ app_launch.py          桌面启动入口：单实例 + uvicorn 后台线程 + pywebview + 托盘体系
├─ run.py / 启动ModelFlow.bat   源码运行入口（浏览器模式，开发用）
├─ app/                   后端 FastAPI（11 个模块）
│  ├─ main.py   约 1000 行 / 60+ 路由
│  ├─ jobs.py   约 2090 行 / 执行引擎核心
│  ├─ db.py     SQLite 5 表
│  ├─ tools.py  11 个科研工具 REST 封装
│  ├─ llm.py    OpenAI 兼容 + Anthropic 双协议
│  ├─ licensing.py  机器指纹 + 在线权威校验
│  ├─ updater.py    清单检查 → 下载 → 分形态替换
│  ├─ tray.py       纯 ctypes 实现的系统托盘（无第三方依赖）
│  ├─ ws.py         WebSocket 按工作流隔离推送
│  ├─ paths.py      frozen/installed/源码 三形态路径布局
│  └─ version.py    0.8.6
├─ static/              前端 SPA（app.js 3714 行 + style.css 1389 行 + index.html + 5 个辅助 js/css + fonts/logos/vendor）
├─ skills/              **20 个** SKILL.md（精简后，仅竞赛用）
├─ _utils_py/           43 个 .py 校验/工具脚本 + 6 个 .sh + 15 个 .md 规则文档
├─ _templates/          14 套竞赛 LaTeX 模板
├─ workspaces/          流水线运行工作区（当前为空）
├─ modex-data/          运行时数据根（modex.db / license.json / uploads / export / update）
├─ make_release.py      发版：版本号 → PyInstaller onedir → Inno Setup → latest.json
├─ installer.iss        Inno 安装器（仅装机版单形态）
├─ upload_cos.py        腾讯云 COS 上传 + 授权码门禁下载页
├─ ModelFlow-dir.spec   PyInstaller 打包配置
├─ release/             发布产物（0.8.5 + 0.8.6 两个 setup.exe + latest.json）
├─ dist_app/            PyInstaller onedir 产物（7077 文件）
└─ 交接文档：HANDOFF.md / TRANSFER.md / HANDOFF-COS部署交接.md / modelflow-全量理解报告.md（旧版）
```

---

## 三、两套流水线（0.8.x 最大变化）

**0.8.x 起已从「11 套」精简为「2 套」，仅服务国赛。**

### 3.1 competition —— 极速全自动流（9 步）

| # | key | 环节 | skill | 产物 | 人工检查点 |
|---|---|---|---|---|---|
| 1 | analysis | 赛题分析 | comp-prob-analysis | PROBLEM_ANALYSIS.md | ✔ |
| 2 | modeling | 建模求解 | comp-modeling | MODELING_REPORT.md | ✔ |
| 3 | code | 编程实现 | comp-code | RESULTS.md | ✔ |
| 4 | figure | 图表生成 | paper-figure | FIGURES.md | — |
| 5 | arch | 流程与架构图 | paper-figure-html + diagram-design | ARCHITECTURE.md | — |
| 6 | review | 逻辑对抗复核 | comp-review | LOGIC_REVIEW.md | — |
| 7 | paper | 竞赛论文撰写 | comp-paper-zh | main.tex | ✔ |
| 8 | compile | 编译与合规检查 | comp-compile-zh | main.pdf | — |
| 9 | improve | 论文改进循环 | auto-paper-improvement-loop | IMPROVED_PAPER.md | — |

> 第 4 步（图表）与第 5 步（架构图）**并行执行**（0.8.6 新增，ThreadPoolExecutor max_workers=2）。
> `logic_review` 开关关闭时，第 6 步整步跳过。

### 3.2 competition_bzd —— BZD 双审精制流（9 阶段，新增）

题面解析 → 策略选型 → 建模执行 → 稳健性总检验 → 章节写作 → 摘要首页 → **全面审查 I（章节自查）** → **全面审查 II（综合评审）** → 终稿装配与合规出库。

- 每阶段 skill = `bzd-2026-stage-0X` + `diagram-design`（薄封装，29–42 行，指向主 skill）
- 主 skill `cumcm-bzd-2026`（353 行）带完整资产：`references/`（19 个规则文档 + template_library）、`config/dim_weights.json`、`scripts/`、`templates/`
- **资产注入机制**：`prepare_cli_workspace` 把 `skills/cumcm-bzd-2026/` 整体拷入 `ws/_bzd/`，并注入环境变量 `MH_BZD_DIR`，供 skill 用 `${MH_BZD_DIR}/scripts/score_artifact.py` 等方式确定性调用
- 定位：正式比赛冲奖推荐，耗时约 2–3 天（极速流之外的第二条路线）

### 3.3 已移除（Git 实证）

```
5153909  精简：移除 10 套学术流水线及非竞赛 skill/资产，仅保留两套国赛工作流
9a5b3a4  精简：清理竞赛流用不到的共享库副本/学术skill/人文社科文档
```
删除内容包括：10 套学术流水线（论文写作/文献综述/开题报告/课程论文/基金申请/软著等）、`comp-paper-en*`（英文论文）、`auto-review-loop*`、`dse-loop`、`experiment-bridge`、`humanities-*`（8 个 md 规则文档）等。skill 数从 **127 → 20**。

---

## 四、后端架构

### 4.1 执行引擎（核心，固定 Claude Code CLI）

`run_step_via_cli`（jobs.py:1595）单次调用形态：

```
claude -p --output-format stream-json --verbose
       --dangerously-skip-permissions
       --setting-sources project
       [--append-system-prompt-file <abs>] [--model <m>]
       ↑ prompt 经 stdin 写入（不是命令行参数）
```

**0.8.x 的四处关键演进：**

1. **prompt 改走 stdin**（0.7.x 是 `-p <参数>`）。原因：火山方舟 Agent Plan 的 `/api/plan` 端点对 Windows `claude.cmd` 传多行 argv 有兼容问题，会把请求错误路由到账号旧模型；stdin 可稳定保持 `ark-code-latest`。
2. **新增 `--setting-sources project`**：只加载工作区 project 指令，隔离用户 `~/.claude/settings.json` 中的旧模型映射/状态栏配置（否则 ark-code-latest 会被旧 user 配置拦成 `unrecognized_model`）。
3. **协议前置门禁**：执行引擎只支持 Anthropic 兼容端点。若预设协议为 openai 且 base 不含 Anthropic 特征串，直接抛清晰错误（而不是把 key 塞进 `ANTHROPIC_*` 后收到莫名 HTTP 错误）。
4. **超时** `MODELFLOW_CLI_TIMEOUT`，默认 2700 秒（45 分钟），超时树杀。

**凭据与环境变量注入**：`ANTHROPIC_API_KEY` + `ANTHROPIC_AUTH_TOKEN` 双 header、`ANTHROPIC_BASE_URL`、`MH_PYTHON`、`MH_TOOLS_DIR`、`MH_BZD_DIR`、`PYTHONPATH`（frozen 下指向 `_MEIPASS`）、`EDITOR_AI_*`/`OPENAI_*`（视觉质检，统一走 `_resolve_vision_cred()`，消除 REST 与 CLI 两套 key 解析漂移）。

**留痕**：逐事件 `_turn_logs/{step}_{HHMMSS}.jsonl` + 完整会话 `_sessions/` + 工具调用实时推 WS。

### 4.2 编排层（execute_job）

- 顺序执行 + **真暂停/恢复**（threading.Event 阻塞）+ **断点续跑**（跳过 status=done 的步骤）
- 人工检查点（checkpoint=True 的步骤停下等人确认）
- 每步跑自检脚本，rc 语义：`0=通过 / 1=阻断 / 2=跳过`
- compile/improve 后本地兜底 xelatex 编译（3 轮）
- `start_job` 带 `_JOB_START_LOCK` 防重复启动（P2-10）

### 4.3 自检体系（step_audit.py → _utils_py）

每个 step 对应一组确定性对账脚本：

| step | 检查项 |
|---|---|
| prob | facts_audit |
| modeling | modeling_coverage_check / count_subproblems / cross_problem_check / facts_audit |
| code | count_subproblems / claim_code_check / data_ingest_check / delivery_audit / leakage_audit / facts_audit |
| figure | figure_check / fig_include_size |
| arch / review / paper / compile / improve | 各自对应脚本组 |

**跨步契约 `CAPABILITY_CHECKLIST.json`** 仍在（实测 13 处命中：jobs.py + 5 个审计脚本 + 7 个 skill），由 comp-prob-analysis 产出、后续步骤消费。

### 4.4 上传解析（0.8.x 已补齐短板）

| 类型 | 处理方式 |
|---|---|
| PDF | pdfplumber + pypdf 抽文本；**扫描页/公式图** → PyMuPDF 渲染 PNG → vision OCR |
| docx / xlsx / xls / csv | python-docx / pandas 抽文本 |
| **图片** | **vision LLM OCR**（`_ocr_image`），写 `*_ocr.txt` |
| **视频 mp4/avi/mov 等 12 种** | **ffprobe 探测 + 抽关键帧 + 抽音轨**（`_probe_video` / `_extract_video`） |
| 模板/大纲 | 按 cf 前缀分类落盘 `user_data/` |

### 4.5 其他模块要点

- **db.py**：5 张表（`workflows` / `settings` / `api_presets` / `skill_overrides` / `image_presets`）。settings 有内存缓存（高频进度循环避免反复开库）。
- **tools.py**：11 个工具，统一 `_run_tool`，**退出码语义已分层**：`0=成功 / 2=已降级（degraded=True）/ 其它=失败`。frozen 下用 `resolve_python()` 独立解释器（sys.executable 是 exe）。
- **llm.py**：OpenAI 兼容 + Anthropic 双协议。`anthropic_url()` 已修 `/v1/v1/messages` 双拼 404 问题。
- **ws.py**：按 wid 隔离推送，跨线程 `call_soon_threadsafe` 投递主 loop。
- **paths.py**：三形态布局。`_detect_installed()` 兼容 `unins000.exe` / `Uninstall.exe` / 注册表卸载项三证据。

---

## 五、桌面壳与前端

### 5.1 app_launch.py（桌面形态，0.8.4 起大幅增强）

- pywebview 原生窗口（1440×900，最小 1100×700），白底防 WebView2 初始化黑闪，就绪后 show
- **单实例**：端口占用时 `FindWindowW` 把已有窗口拉前台
- **强制浅色标题栏**（DWMWA_USE_IMMERSIVE_DARK_MODE，兼容属性号 20/19）
- **关闭按钮子类化为最小化到托盘**（WM_CLOSE → 隐藏，非退出），并记忆窗口位置到 `settings.window_rect`
- **托盘体系**（app/tray.py，纯 ctypes + Win32 API，无第三方依赖）：打开/隐藏/设置/打开工作区目录/开机自启（HKCU Run）/退出；首次启动气泡引导（仅一次）
- WebView2 缺失时弹原生 MessageBox 并落盘 `data/boot-error.log`，**绝不降级打开浏览器**

### 5.2 前端（static/app.js，3714 行，6 视图）

| 视图 | 内容 |
|---|---|
| **list** | 工作流列表 + 统计卡 + 筛选 + 轮询 |
| **new** | 赛事卡片墙 + 竞赛表单（赛项/题号/输出格式/审查模式/页数/丰满模式/逻辑复核/流程图引擎/配色/数量硬目标/上传/视觉质检/AI 声明/检查点/改进循环/模型分配）；**流程对比树状图**（极速快跑流 vs 双审冲奖流）；配色/版式/图表类型实时预览墙 |
| **run** | 步骤时间线 + WS 实时日志（节流刷新）+ 产物文件分组浏览/预览/下载/上传 + **产物编辑器**（文件树 + AI 润色）+ **提示词定制弹窗**（原版/追加/替换/恢复） |
| **tools** | **独立工具页**（0.8.x 新增）：文献检索 / Docx 转换 / 图片生成 / 论文评审 / 数据查真 / 排版派生 |
| **settings** | 模型预设（供应商目录弹窗）/ 图片生成预设 / 软件更新 / 本地运行时一键装 / LaTeX 检测 |
| **lock** | 授权锁屏 |

启动链：授权锁屏 → 启动准备遮罩（8 项环境自检逐行点亮）→ 主界面。

---

## 六、发版、授权与分发

### 6.1 发版链路

```
源码 → make_release.py --version X --notes "..."
        （PyInstaller onedir → dist_app/ModelFlow → Inno Setup → release/ModelFlow-X-setup.exe + latest.json）
     → upload_cos.py（上传私有 COS 桶 modelflow-1447874637/ap-guangzhou）
     → 下载页 https://lxlrwxs.top/modelflow/
```
- 本地只保留最新两个安装包（0.8.5 / 0.8.6，各约 164 MB）
- **便携版已停售**，仅装机版单形态

### 6.2 授权（0.8.x 已加固）

三层判定：
1. **本地预检**：HMAC-SHA256(secret, code|mid) 前 32 位 + 设备指纹匹配
2. **在线权威校验**：`POST https://lxlrwxs.top/modelflow/api/check`（1 小时间隔）。码不存在/已吊销/设备不匹配 → **立即清除本地授权**
3. **离线宽限**：网络不可用时，7 天内有过成功在线校验则放行

> 相比 0.7.x 的「纯离线 HMAC」，伪造 token 已无法绕过在线校验。SECRET 硬编码仍在，但仅作快速预检用途。

### 6.3 在线更新

`latest.json` 清单（COS 公有读）→ 流式下载 + SHA-256 校验 → 分形态替换：
- **装机版**：下载新 setup.exe → Inno 静默升级（`/VERYSILENT /SUPPRESSMSGBOXES /MERGETASKS=keepsl` /restart）→ 自动重启
- 软件内下载走 `/api/update-download` 换 COS 预签名 URL
- 启动后延迟 6 秒后台自动检查，发现新版自动下载，安装仍需用户在设置页确认

---

## 七、当前运行时实况（modex-data 实测）

| 项 | 状态 |
|---|---|
| 授权 | 已激活，`admin=true`，机器指纹 `57d884a8…` |
| 工作流 | 3 条：`#37` BZD双审精制流验证（**paused 22%**）、`#35` 流程冒烟验证（completed）、`#4` 国赛新建（pending） |
| API 预设 | 仅 1 条：`火山方舟AgentPlan`（anthropic / `ark.cn-beijing.volces.com/api/coding` / `ark-code-latest`） |
| 图片预设 | **空**（无记录） |
| 提示词定制 | 1 条：`competition/code` |
| Python | `C:\Users\李星历\AppData\Local\Programs\Python\Python312\python.exe` |
| Claude CLI | `D:\npm-global\claude.CMD` |
| 主题 | voyra |

---

## 八、0.7.6 → 0.8.6 差异总览（旧报告失效项）

| 维度 | 旧报告（0.7.6） | 当前（0.8.6） |
|---|---|---|
| 流水线 | 11 套（competition + 10 套学术） | **2 套**（competition + competition_bzd） |
| skills | 127 个 SKILL.md / 86 顶层 | **20 个** |
| 前端视图 | 4 个 | **6 个**（+tools 工具页、+lock 授权锁屏） |
| app.js | 2666 行 | **3714 行** |
| 授权 | 纯本地 HMAC（可伪造） | **本地预检 + 在线权威校验 + 7 天离线宽限** |
| 工具层 | 7 个，exit 2 当纯成功 | **11 个，0/2/其它 语义分层 + degraded 标记** |
| CLI 调用 | `-p <prompt>` argv | **stdin + `--setting-sources project` + 协议门禁** |
| 执行调度 | 全串行 | **figure + arch 并行** |
| 桌面壳 | pywebview 窗口 | **+ 托盘体系**（最小化到托盘/开机自启/位置记忆） |
| 上传解析 | PDF/docx/xlsx；视频未接 | **+ 视频（ffprobe+抽帧+音轨）、图片 OCR、PDF 扫描页 OCR** |
| 发版形态 | 装机 + 便携 | **仅装机版**（便携已停售） |
| _utils_py | 78 项 | 43 py + 6 sh + 15 md（人文社科文档已删） |
| _templates | 14 套 | 14 套（未变） |

---

## 九、风险与待办（按严重度）

### 头号

1. **`image_presets` 表为空** → 图片 OCR、data_fig 视觉质检、tikz 视觉质检全部走 `exit 2` 静默降级。当前本机所有视觉质检实际**没有生效**。需在设置页新增多模态图片预设并设为默认。
2. **`#37` BZD 流停在 22%（paused）** → 新增的第二套流水线**未跑完验证**。若对外的 BZD 卖点要成立，需补跑完整 9 阶段。
3. **API 预设单点**：仅 1 条火山方舟预设，无备份。该端点故障时整条流水线停摆。建议加一条备用预设。

### 中等

4. **BZD 9 个阶段 `check` 字段全为空串** → 无 `step_audit` 自检兜底，质量完全依赖 skill 自述的质量门。极速流 9 步都有自检，BZD 流没有。
5. **`_utils_py/humanities_review.py`（736 行）死代码残留**：依赖的 `humanities-terminology-bilingual.md` 等 8 个文档已在精简提交中删除，且 `app/` 与 `skills/` 中均**无任何调用**。误调用时术语检查会静默跳过。
6. **`_utils_py/*.sh`（6 个）在 Windows 无 bash**：compile_check / figure_check / tikz_check / writing_check 等需同名 .py 等价实现。

### 轻微

7. HMAC SECRET 仍硬编码在客户端（离线宽限期内伪造仍可能生效，宽限期过后会被在线校验拒绝）。
8. `tools/gen_topjournal_guide.py`、`_scidraw_pdf/`（168 文件）、`_preview/`、`_gen_missing_catalog.py`（33KB）、`缺失图表候选清单.pdf`、`顶刊配图风格手册.pdf` 属于配图库建设期的旁支产物，与主流水线无关，可归档。
9. 根目录存在 `NUL` 空文件（Windows 重定向误产物），已在 .gitignore 中。

---

## 十、守住的底线（勿回退）

- 执行引擎**固定 Claude Code CLI**，不降级 API 直连。
- 所有工具/库走 `resolve_python()` 确定性入口（frozen 下 `sys.executable` 是 exe，不能用）。
- 环境锚点 `_env_anchor(step, ws)` **按步骤生成，只写本步用得到的**。
- 不引入机器硬编码路径（除 `启动ModelFlow.bat` 中一处回退路径外，全库无 `李星历` 硬编码）。
- 打包必须用系统 Python312（含 PyInstaller + 科学计算栈）。

---

## 十一、残留清理记录（2026-09-06 · 本报告快照之后执行）

本报告基于清理前快照，以下残留已在同日清理中落地（§九.5/8/9 全部解决）：

**代码同步修改**
- `app/tools.py`：移除 `tool_watchdog` 及 TOOLS 注册（11 → 10 个工具）；`app/main.py` /api/tools 描述同步
- `app/jobs.py`：`CONTEST_TEMPLATE_MAP` 精简为仅国赛条目、`_CLASS_TEMPLATE_HINTS` 移除 mathorcupmodeling（模板库已只有 cumcm，其余赛项兜底注入 cumcm）
- `static/app.js`：删除无消费者的 `FIG_THEMES`/`FIG_THEME` 数据；图墙固定 vivid，`_figSrc` 默认回退 vivid（配色弹窗的 8 张代表图 × 5 配色主题 PNG **保留在用**，勿删）
- `static/providers-catalog.js`：头注释不再指向已删除的 `_extract_cc_presets.py`

**文件删除**
- `_utils_py/`：humanities_review.py（§九.5）、docx_template_analyze.py、docx_template_fill.py、gen_paper_previews.py、watchdog.py
- `static/img/`：21 种已下架图型的孤儿预览 PNG（143 → 122 张）
- `_templates/`：13 套非国赛模板，仅留 cumcm
- 5 个 SKILL.md 与 `_utils_py/` 内脚本/规则文档（figure_check.sh、writing_check.sh、get_recipe.py、plot_utils.py、tikz_rules.md、ai_disclosure_rules.md、figure_recipes_competition.md）共 42 处指向已不存在目录 `skills/shared-scripts/` 的死 fallback
- 根目录：HANDOFF.md、TRANSFER.md、旧版（0.7.6）全量理解报告、_dbg3d.py 等调试残留 10 项、`_scidraw_pdf/`、`tools/`、`_api_test/`、`_preview/`、5 个日期命名临时目录、`_gen_missing_catalog.py`、《缺失图表候选清单.pdf》《顶刊配图风格手册.pdf》、`NUL`（§九.9）、`__pycache__/`

**现存文档**：仅本报告 + `HANDOFF-COS部署交接.md`（部署 SOP，仍有效）。
