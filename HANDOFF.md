# ModelFlow 智模流水线 — 交接文档（新对话续作指引）

> 生成时间：2026-08-31
> 当前版本：0.7.2（发版目标 0.7.4）
> 项目根：`C:\Users\李星历\Desktop\数学建模工作流软件`

---

## 0. 一句话定位

数学建模竞赛全自动桌面应用（Python 后端 + Claude Code CLI 执行引擎）。
核心价值：上传赛题/数据 → 9 步流水线自动跑完（分析→建模→代码→图表→流程架构图→逻辑对抗复核→论文→编译→改进）→ 产出可提交的 LaTeX/PDF 论文。

---

## 1. 架构概况（Web 应用全貌）

### 1.1 前端（static/）
- `app.js`：单页前端，含首页、新建工作流、流水线详情/进度、设置、供应商/预设管理。
- `providers-catalog.js`：供应商目录（国内 9 家，已中文化：深度求索/阿里云百炼/智谱 GLM/月之暗面 Kimi/豆包/火山方舟/MiniMax/硅基流动/百度千帆）。
- `style.css`：主题样式（`btn-accent`、运行时清单 `.rt-row` 等）。

### 1.2 后端（app/）
- `main.py`：FastAPI 路由 + `/api/*` 接口 + 启动调 `jobs.auto_configure_cli()`。
- `jobs.py`：核心执行引擎（流水线编排、CLI 调用、上传解析、运行时检测/一键安装）。
- `tools.py`：REST 工具集（7 个对外工具），统一 `_run_tool` 封装。
- `db.py`：SQLite（api_presets / image_presets / settings / 工作流）。
- `paths.py`：路径解析（frozen 判据 `sys._MEIPASS`）。
- `llm.py`：OpenAI 兼容 + Anthropic 双通道（仅用于工具，不用于执行引擎）。

### 1.3 执行引擎（关键决策）
- **固定 Claude Code CLI**（`run_step_via_cli`，stream-json），**已删除 API 直连**（`run_agent_step`）。
- 每步以工作区为 cwd 启动 `claude -p ... --output-format stream-json`，SKILL 全文经 `CLAUDE.md` 注入。

### 1.4 流水线模板
- 竞赛 9 步 `COMPETITION_STEPS`：analysis/modeling/code/figure/arch/review/paper/compile/improve。
- 非竞赛 10 套 `NON_COMPETITION_STEPS`（idea_discovery / experiment_bridge / auto_review / paper_writing / full_pipeline / thesis_proposal / literature_review / course_paper / course_report / humanities_paper…）。

---

## 2. 核心原则（务必遵守）

**「AI 好调用」原则**：所有工具/运行时/库，必须是 Claude Code agent 在 CLI 会话里能**直接、明确、无歧义**调用，不靠猜路径。

具体落点：
1. Python 入口确定性 → `resolve_python()`：settings → env `MODELFLOW_PYTHON` → `py` launcher → PATH → 常见目录。本机实测命中 `C:/Users/李星历/AppData/Local/Programs/Python/Python312/python.exe`（3.12.10，含 matplotlib/numpy/pandas/scipy 全套）。
2. 环境变量注入（`run_step_via_cli`）：`MH_PYTHON`、`MH_TOOLS_DIR`、`PYTHONPATH`、`PYTHONIOENCODING=utf-8`。
3. **按步骤锚点**（`_env_anchor(step, ws)`）：每步只把本步真正用到的工具入口写进 CLAUDE.md，防上下文过长/换目录后 AI 忘记。**每个位置锚点不同，用不到的不写**（这是用户明确要求）。
4. frozen 下 `sys.executable` 是 exe 非 Python → `tools.py._tool_python()` / `run_check` 用 `resolve_python()` 独立解释器。

---

## 3. 已完成（本轮及前序）

### 3.1 打包依赖修复
- 两个 spec（`ModelFlow-dir.spec` / `ModelFlow.spec`）去掉错误的 `excludes=['scipy','matplotlib','pandas']`，改为 `collect_all` 打入 matplotlib/pandas/scipy/pdfplumber/python-docx/pypdf/openpyxl/PIL。

### 3.2 功能开关真生效
- `_fig_markers()` 产出 `MH_DIAGRAM_STYLE` / `MH_DATA_FIG_PALETTE` / `MH_DATA_FIG_STYLE` / `MH_DATA_FIG_VISION` / `MH_FAST_MODE` / `MH_FLOW_PER_PROBLEM` / `MH_RICH_MODE`，skill 按这些标记 grep CLAUDE.md。
- review_mode=fast → `MH_FAST_MODE=1`；per_flow → `MH_FLOW_PER_PROBLEM=1`；rich_mode → `MH_RICH_MODE=1`。
- flow_engine=drawio → arch 步 skill 切 `paper-figure-drawio`。

### 3.3 上传解析（`_extract_text` + `_save_assets`）
- PDF（pdfplumber+pypdf）、docx（python-docx）、xlsx/xls/csv（pandas）→ 抽文本写 `*_extracted.txt`。
- 前端 `cf` 前缀 cat 与后端目录映射已对齐（problem/prob_img/data/template/outline）。

### 3.4 运行时探测 + 一键安装
- `detect_runtimes()`（8 项：claude_cli/node/git/python/python_libs/xelatex/drawio/ffmpeg）。
- `install_runtime()`：winget/npm（国内镜像）白名单。
- `/api/runtimes` + `/api/runtimes/install` + 设置页「本地运行时」卡片 + 启动遮罩检测。

### 3.5 反编译损坏文件的处置（6 个工具）
来源：历史恢复存档（字节码级一致）。

- **4 个纯脚本直接用恢复版进 `_utils_py`**：
  - `humanities_review.py`（人文社科质检，check_* 系列 + Severity/Issue）
  - `docx_template_analyze.py`（Word 模板结构分析，含 .dotx 转换）
  - `data_fig_vision_check.py`（数据图视觉质检）
  - `drawio_vision_check.py`（流程图视觉质检，per-key/全局双道计数锁）
- **2 个依赖 Electron/Node 的：恢复版存档不进包**：
  - `screenshot_capture.py` → 改写为 **Edge/Chrome 无头 printToPDF**（本机已装 Edge/Chrome，实测 32201 字节矢量 PDF rc=0）。关键 bug 已修：需加独立 `--user-data-dir` 防 Edge 单实例复用导致 PDF 不落盘，且不能加 `--virtual-time-budget`。
  - `docx_template_fill.py` → 保留恢复版全部插入/图片迁移/占位符逻辑，仅把 Node 依赖 `_render_md_via_node` 换成纯 python-docx（`md_to_docx.py`）。实测填充 rc=0。

> 决策（用户选定 `keep_light_impl`）：保留 ModelFlow 轻量实现，恢复原版存档对照。
> 待补：若以后要切回原版，需用户提供干净的 `docx_export.py`（Node 引擎）和 `capture.js`（Electron）。

### 3.6 视觉质检环境变量注入
- `run_step_via_cli` 里从图片预设/默认 API 预设取 key，注入 `EDITOR_AI_API_KEY/BASE_URL/MODEL_ID` + `OPENAI_API_KEY/BASE_URL`。

---

## 4. 待办清单（todo 状态）

当前 7 项，`#42` in_progress（实际已完成，待标记），其余 pending：

| # | 内容 | 状态 |
|---|---|---|
| 42 | spec 加依赖/去 excludes | ✅ 已完成，待勾 |
| 43 | 开关空转修复（review_mode/logic_review） | ✅ 已完成，待勾 |
| 44 | 上传解析 PDF/docx/xlsx | ✅ 已完成，待勾 |
| 45 | DrawIO 引擎切换 + draw.io 自检 | ✅ 已完成，待勾 |
| 46 | 重写 screenshot_capture + 重建 vision/docx | ✅ 已完成，待勾 |
| 47 | 启动自检 + 一键引导安装 | ✅ 已完成，待勾 |
| 48 | **打包 0.7.4 + 三项审查（工具可调用/路径正确/AI 可用）** | ⬜ 未做 |

**未完成的具体工作：**
1. **打包 0.7.4 + 本地静默安装 + 装机版运行态两遍审查**（`make_release` 打包 → 静默安装 → 健康检查 + 浏览器渲染回归）。
2. **「高级选项自定义图片数量」控件**：skill 已确认读 `MIN_FIGURES`，只差前端输入框 + `MH_MIN_FIG` 标记 + config 字段。

---

## 5. ⚠️ 需要优化的全部问题（用户上一轮确认的优化清单）

### 5.1 上传与解析
| 类型 | 现状 | 问题 |
|---|---|---|
| PDF | ✅ 可解析 | 公式图片/扫描页会丢（只抽文字层） |
| Word .docx | ✅ 可解析 | — |
| Excel xlsx/xls/csv | ✅ 可解析 | — |
| 图片 PNG/JPG | ⚠️ 只落盘 | **不做 OCR/视觉抽取**，靠 AI Read 多模态（公式易读错） |
| **视频 mp4/avi/mov** | ❌ **完全未接** | 只搬运不解析，AI 读不了内容 |
| 老 .doc | ❌ | 需转换，未接 |
| .ppt/.pptx | ❌ | python-pptx 在包但未接抽取链 |
| /api/upload | ⚠️ | **无扩展名白名单与大小上限** |

### 5.2 AI 工具调用
1. **`_run_tool` 把 exit code 2 也算 `ok=True`** → 掩盖「工具降级跳过、实际没干活」，应拆 `0=成功/2=已降级/其它=失败` 并给 `degraded` 标记。
2. **`tool_tikz_vision_check` 的 key 取错字段** → 取的是旧 `gpt_image_key`（图片生成 key），不是 vision model key，视觉质检大概率静默跳过。
3. **两套调用通道 key 解析不一致** → 前端按钮走 REST（tools.py），skill 在 CLI 里 bash 调 `_utils/*.py`，逻辑各写一份易漂移，应统一成一个 key 解析函数。
4. **第三方库未进一键安装清单** → `python_libs` 装的是 matplotlib/numpy/pandas/scipy/pdfplumber/python-docx/pypdf/openpyxl，但：
   - `drawio_vision_check.py` 用 `fitz`（**PyMuPDF**）→ 未装则 PDF→PNG 静默失败；
   - `docx_template_fill.py` 图片缩放用 `PIL`；
   - 将来接 ppt 需 `python-pptx`。
5. **`tool_review` 的 provider 透传** → `reviewer_client.py` 只支持 OpenAI 兼容，默认预设是 anthropic 时会报错，需加路由或提示。

### 5.3 优化优先级（按 ROI）
1. **视频解析链路**（最能补短板）：ffmpeg 抽关键帧 + 抽音频 → 关键帧给 vision LLM 读、音频转写；至少先 `ffprobe` 报时长/分辨率/帧数。
2. **图片公式提取**：赛题图片加 OCR（或复用 vision key 做文字识别），写 `*_ocr.txt` 供 skill 优先读。
3. **PDF 图片兜底**：`pymupdf` 把扫描页/公式图转 PNG 再 OCR。
4. **exit code 语义分层**（0/2/其它）。
5. **统一 key 解析 + PyMuPDF 进安装清单**，消除视觉质检静默失效。

---

## 6. 关键文件/路径速查

| 项 | 位置 |
|---|---|
| 项目根 | `C:\Users\李星历\Desktop\数学建模工作流软件` |
| 执行引擎 | `app/jobs.py`（`run_step_via_cli` / `resolve_python` / `_env_anchor` / `prepare_cli_workspace` / `_extract_text` / `detect_runtimes`） |
| REST 工具 | `app/tools.py` |
| 工具脚本 | `_utils_py/`（几十个，含恢复版 + 轻量实现） |
| 恢复原版存档 | 历史留档（已清理） |
| skills | `skills/`（90 个 SKILL.md） |
| 打包 spec | `ModelFlow-dir.spec` / `ModelFlow.spec` |
| 版本号 | `app/version.py`（当前 `0.7.2`） |
| 参考源码 | 历史留档（已清理） |

**本机环境事实（写给 AI 的确定性入口）：**
- Python312：`C:/Users/李星历/AppData/Local/Programs/Python/Python312/python.exe`（3.12.10 + 全套科学栈）
- 浏览器：Edge `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe` + Chrome（轻量出图内核用）
- 运行时实测：claude_cli/node/git/python/python_libs/xelatex 就绪；drawio/ffmpeg 缺失（已给 winget 引导）

---

## 7. 新对话如何无缝继续

**先读本文件**，然后按顺序：

1. **勾掉已完成的 todo**（#42–#47 均已完成，用 `todo_write` 标记 completed）。
2. **补「图片数量」控件**：前端输入框 + `MH_MIN_FIG` 标记 + config 字段（skill 已读 `MIN_FIGURES`）。
3. **按 §5.3 顺序做优化**（视频解析 → 图片 OCR → PDF 兜底 → exit code 语义 → 统一 key + PyMuPDF）。
4. **打包 0.7.4 + 三项审查**（工具可调用 / 路径正确 / AI 可用）。

**守住的底线（勿回退）：**
- 不引入机器硬编码路径（全库已复扫无 `李星历`/`31f626729e04` 残留）。
- 固定 Claude Code CLI，不降级 API 直连。
- 所有工具/库走 `resolve_python()` 确定性入口。
- 锚点按步骤生成，不写用不到的。