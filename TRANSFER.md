# ModelFlow 智模流水线 · 完整任务转接文档（2026-08-30 定稿）

> **接手 Agent 须知**：这是唯一权威入口，读完即可 100% 接手，无需追问历史。
> 更深的历史时间线在同目录 `HANDOFF.md`（§8a–§8s），按需查阅。
> 所有路径、凭据、命令均为实测可用——直接照做。

---

# 〇、30 秒了解全局

**产品**：ModelFlow 智模流水线 —— 数学建模竞赛全自动流水线桌面应用
（赛题分析 → 建模 → 编程 → 图表 → 论文 → 编译 PDF → 审查改进），扩展 10 套学术/科研流水线。形态为 **纯桌面应用**（pywebview 原生窗口，
无浏览器依赖，关窗即退出）。

**当前版本**：0.7.0（本机已安装运行）；**线上服务器已是 0.7.0**（latest.json 指向
`ModelFlow-0.7.0-setup.exe`，sha256 `dac397d1…`，2026-08-30 已上传上线）。
**挂起事项**：云服务器 **2026-09-25 到期**（续费或迁移，约 25 天缓冲）。

**源码目录**：`C:\Users\李星历\Desktop\数学建模工作流软件`（非 git 仓库）
**参考库**：`_study/`（UI 学习参考，历史留档）
**skill 资产**：`skills/`（随包内置全量 90 个 skill，机器无关；外部覆盖见 §二）
**深度历史**：同目录 `HANDOFF.md`（§8a–§8t 时间线 + 全部踩坑记录）

---

# 一、产品功能全景（全部已上线本机，0.7.0）

## 1. 竞赛流水线（核心）
9 步全自动：赛题分析 → 建模求解 → 编程实现 → 图表生成 → 流程架构图 →
逻辑对抗复核 → 竞赛论文撰写 → 编译与合规 → 论文改进循环。
产物实时落盘 `workspaces/job_{id}/`，运行页可浏览/编辑/AI 润色/导出 Word。

## 2. 双执行引擎（jobs.py）
- **API 直连**：每步一次 LLM 调用（OpenAI 兼容/Anthropic 双协议），
  内置代码自修正循环（执行失败自动回喂报错重试 ≤3 轮，`run_agent_step`）。
- **Claude CLI 全自动**（`run_step_via_cli`）：以工作区为 cwd 启动 claude 子进程
  （stream-json 解析、工具调用实时推送、45min 超时树杀、会话留痕 `_sessions/`），
  agent 自主读写文件与执行工具，SKILL 经工作区 CLAUDE.md 注入。
- 新建工作流页可选 API / CLI / 自动。

## 3. 预设供应商目录（69 家）
- 全 agent 预设（315 条 → 排除聚合中转站 216 家
  + 合作商 + OAuth + 无效地址 → 69 家官方直连），源码 `_extract_cc_presets.py`。
- UI：新增供应商弹窗顶部 = 搜索框 + 分类标签（全部/国内官方/国际官方/云厂商/第三方直连）
  + 彩色品牌图标网格（static/logos/cc/ 99 个）。
- 点卡片自动填充：显示名、协议、端点、官网、获取 Key 直达链接。
  **供应商标识由用户自行填写**（不自动生成）。

## 4. 供应商卡片六按钮（悬停显示）
① 启动/使用中（互斥切换，使用中禁删）② 编辑（内联表单）③ 复制配置
④ 检测连通 ⑤ 配置使用量查询（弹窗：自动预填已知余额接口+服务端代理
`/api/usage/query` 带 SSRF 内网拦截+保存配置持久化）⑥ 删除。

## 5. 在线更新（updater.py）
设置页「检查更新」→ 发现新版自动下载（进度条）→ SHA-256 校验 →
「立即安装并重启」→ 二段式静默安装（/FORCECLOSEAPPLICATIONS，数据/快捷方式保留）。
更新源指向用户云服务器 https://apilxl.bbroot.com/modelflow。

## 6. 授权锁（licensing.py）
机器指纹（MachineGuid sha256）+ HMAC 令牌离线校验；frozen 模式未激活封锁全部
受保护 API（首页/静态豁免）；未激活显示激活锁屏；管理员码不限机不绑定。

## 7. 桌面化细节
- 启动准备遮罩：六项真实自检逐行点亮（本地服务/授权/LaTeX/供应商目录/图标库/字体/更新源），
  进度条 +「x / 6 已就绪」，完成后渐出（可选项失败标黄不阻塞）。
- 浅色标题栏（DWM 强制，深色模式不再出现顶部黑条）；窗口白底防黑闪。
- 单实例：重复启动自动聚焦已有窗口（FindWindowW + SetForegroundWindow）。
- 确认弹窗全部应用内样式化（appConfirm，删除红钮/更新蓝钮，替代系统原生框）。
- 弹窗渐进渐出动效（mfPopIn/Out：fade + zoom95 + slideY）。
- 新图标 v3：蓝渐变底 + 白 M + 上扬箭头（exe/favicon/logo.svg 三处同步）。

## 8. 其他
- 10 套学术流水线（idea_discovery/experiment_bridge/paper_writing 等；SKILL 已随包内置，可正常运行）
- 科研工具集（文献搜索/AI 生图/Word 导出/论文评审/数据检查/排版派生）
- 提示词定制（每步骤可查看原版 SKILL / 追加 / 替换 / 恢复，skill_overrides 表）
- 图片生成支持自定义端点与模型（gpt_image_base / gpt_image_model settings）

---

# 二、技术架构

```
桌面窗口(pywebview, app_launch.py)
   │ http://127.0.0.1:8000
FastAPI(app/main.py) ── SQLite(modex-data/modex.db 或 安装目录\data\)
   ├─ app/jobs.py      双引擎执行器 + 69家目录使用 + 9步竞赛流水线定义
   ├─ app/llm.py       OpenAI 兼容 / Anthropic 双协议
   ├─ app/updater.py   在线更新（二段式静默安装）
   ├─ app/licensing.py 授权锁（frozen 才启用；源码模式全开放）
   ├─ app/tools.py     科研工具集（subprocess 调 _utils_py/）
   ├─ app/ws.py        WebSocket 实时推送（/ws/{wid}）
   └─ static/          SPA（app.js 单文件）+ providers-catalog.js + logos/ + fonts/
```

## 关键目录
```
C:\Users\李星历\Desktop\数学建模工作流软件\
├─ app/            后端（main/jobs/llm/db/updater/licensing/tools/ws/paths/version）
├─ static/          SPA（app.js 单文件）+ providers-catalog.js + logos/ + fonts/
├─ skills/         随包内置全量 skill（90 个：9 竞赛 + 81 学术/工具），机器无关
├─ _utils_py/      自检/工具脚本（step_audit 等 57 文件，随包分发）
├─ _templates/     13 套竞赛 LaTeX 模板骨架
├─ server/          云端授权服务源码（部署在云服务器 /opt/mflic/）
├─ release/         发布产物（只留最新两个 setup + index.html + latest.json）
├─ _study/  UI 学习参考（历史留档）
├─ _e2e_agent_loop.py      流水线 E2E（mock LLM + 真 xelatex）
├─ _test_cli_executor.py   CLI 执行器解析
├─ _sync_static.py         静态热同步到安装版（免重装）
├─ make_release.py         发版打包
├─ upload_release.py       上传云服务器
└─ _extract_cc_presets.py  预设提取器
```

**skill / utils 路径设计（机器无关，接手必读）**：
- `jobs.py` 中 skill 与自检脚本的路径**不再写死任何本机目录**（历史硬编码已移除）。
- 随包内置 `skills/`（`paths.BASE / "skills"`）与 `_utils_py/` 是**唯一可靠来源**，换机器、打包分发均可直接使用。
- 如需外部覆盖：环境变量 `MODELFLOW_SKILLS_DIR` / `MODELFLOW_UTILS_DIR`，或 settings 表 `skills_dir` / `utils_dir`；指向的目录**真实存在才生效**，否则静默回退内置副本。
- 完整 skill 套件（90 个）已并入 `skills/`，机器无关。

---

# 三、凭据与服务器（全部）

| 项 | 值 |
|---|---|
| 云服务器 SSH | root@177.2.186.149（Ubuntu 24.04 日本；密钥 ~/.ssh/id_ed25519_voyra；工具 `python C:\Users\李星历\.claude\tools\srv.py "命令"`） |
| ⚠️ 到期 | 服务器 2026-09-25；SSL 2026-11-23（acme.sh 自动续） |
| 授权管理后台 | https://apilxl.bbroot.com/modelflow/admin，管理密码 `1607570960qqQ` |
| 管理员授权码 | `MUZ9B`（不限机不绑定；本机已预激活） |
| 可售用户码 | ZW7EP DLVBH DC78W 6DBKB FK4WW 23QZL |
| HMAC 密钥 | /opt/mflic/secret.txt = 1adee14c…（已嵌入 app/licensing.py） |
| 官网 | https://lxlrwxs.top（React SPA；代码 D:\Voyra 个人网站；GitHub liixnglinb/Voyra → Cloudflare Pages 自动构建；右上角有下载入口） |
| 官网仓库凭据 | 见 桌面\个人开发\个人网站信息\（含 Bmob key 等） |

**服务器目录结构**：
```
nginx (apilxl.bbroot.com, SSL ZeroSSL 2026-11-23)
├─ /modelflow/            → /var/www/modelflow/（下载页+latest.json+latest-portable.json）
├─ /modelflow/api/        → proxy 127.0.0.1:8807/api/（授权服务；⚠️ 必须带路径替换）
├─ /modelflow/admin       → proxy 8807/admin（管理页）
├─ /modelflow_internal/   → internal alias /var/www/modelflow_files/（⚠️ 必须在静态根之外）
└─ /                      → New API 中转站（Docker，勿动）

/var/www/modelflow/        下载页 + latest.json + latest-portable.json(停更钉0.5.3)
/var/www/modelflow_files/  setup.exe（门禁目录，当前=0.6.3+0.7.0）
/opt/mflic/                授权服务（license_server.py + licenses.db + systemd mflic:8807）
```

**授权规则**：5 位码（字母表去 I/O/0/1）；一码绑一机（机器指纹 sha256）；
管理员码不限机不绑定；吊销即时生效。API：POST /api/verify（下载门禁）、
POST /api/activate（激活绑定）、GET /api/dl/{file}?code=（门禁下载）。

---

# 四、发版 SOP（两条命令 + 一步用户确认）

```bash
# ① 打包（自动：版本号写入→onedir→Inno→本地清理只留最新两个→生成 latest.json）
python make_release.py --version X.Y.Z --notes "更新说明"

# ② 上传（⚠️ 需用户点头；自动：SFTP 上传+服务器旧包清理+停更清单覆写）
python upload_release.py
```
- make_release 内置本地清理（只留最新两个 setup）。
- upload_release 内置服务器清理（同样只留最新两个 setup）+ 停更清单。
- **改了代码/静态必须全量构建（不带 --skip-build），--skip-build 会沿用旧 exe。**

---

# 五、验收基线（改完必跑）

```bash
python -m py_compile app/*.py && node -e "new Function(require('fs').readFileSync('static/app.js','utf8'))"
python _e2e_agent_loop.py        # 9 步流水线 + agent 循环 + 编译闭环 → ALL PASS
python _test_cli_executor.py     # CLI 执行器解析 → ALL PASS
```
安装验证：静默安装 → health 含 version → /api/license/status activated →
首页 200 → 未激活(临时改名 license.json) 受保护 API 403。

---

# 六、挂起事项与建议方向

**挂起**：云服务器 **2026-09-25 到期**（续费或迁移；SSL 2026-11-23 由 acme.sh 自动续）。
0.7.0 已于 2026-08-30 上传上线（线上 latest.json = 0.7.0 / sha dac397d1）。

**建议方向**（做前先问用户）：
- 用量查询扩展：更多家解析器 / 用量 JS 脚本自定义模板
- 提示词中心总览页（数据层已有 list_skill_overrides）
- 授权在线心跳（远程吊销即时生效）
- 未移植功能：多套餐展开、拖拽排序、故障转移队列
- E2E 残留 workspace 清理（job_12/13/17-21 等）

---

# 七、坑位大全（全部踩过，按频率排序）

1. **并行 AI 会话**：用户同时开多个 agent 改同一批文件——Edit 前必须重新 Read；
   官网仓库曾被并行会话回滚提交，改完立即 commit+push 原子化。
2. **make_release --skip-build 沿用旧 exe**：改代码/静态后必须全量构建。
   setup 是 lzma2 压缩——**字节搜索验证无效**，以安装后实例服务的 /static/app.js 为准。
3. **Mimosa 安全钩子**：拦 bash 直写源码/配置（用 Edit/Write 工具）、拦 eval/new Function
   （改读全局量）、拦 SSRF（外发请求必须内网拦截）。heredoc 嵌套 python 转义易炸，
   复杂补丁写独立 .py 执行。
4. **浏览器缓存**：改 app.js/style.css 后验证，先页面内 `fetch(url,{cache:'reload'})`
   再 reload；**验证 UI 用浏览器渲染，curl 扫压缩 JS 不可靠**（曾误报构建陈旧）。
5. **Inno 静默升级被占用文件卡住**（rc=5 伪装成"用户取消"）：必须带 /FORCECLOSEAPPLICATIONS
   （updater 已内置）。
6. **frozen 限制**：sys.executable 非 python（自检子进程跳过）；INSTALLED 检测用
   unins000.exe（不是 Uninstall.exe）+注册表兜底。
7. **Popen 切 cwd 后相对路径全灭**：CLI 路径、system-prompt 文件必须 resolve() 绝对化。
8. **路径名**：源码目录含两个空格；updater 用 paths.DB_DIR 不是 DATA_DIR。
9. **授权门禁**：文件目录必须在 nginx 静态根之外（曾被 /modelflow/files/ 直链绕过）。
10. **nginx proxy_pass**：/modelflow/api/ 必须写 `proxy_pass http://127.0.0.1:8807/api/;`
    （带路径替换），不带会 404。
11. **Git Bash 中文 heredoc**：curl -d '中文' 按 GBK 发送导致服务端 UTF-8 解析 500——
    中文 body 写 UTF-8 文件后 --data-binary @file。
12. **版本号只升不降**：曾 0.6.2→0.6.1 交错导致降级安装混乱。
13. **bash 大补丁截断**：>10KB 的 heredoc 会被截断——拆分或用 Write 工具写 .py 再执行。
14. **Pillow 画图标**：粗曲线用「圆点盖章法」（沿线盖圆），line+width 有毛边；
    favicon.ico 下载后 Pillow 解析失败时检查是否返回了 HTML（SPA fallback）。
15. **pnpm/monorepo**：供应商目录工程用 pnpm workspace；改其源码后 pnpm build 才生效。

---

# 八、环境与依赖

- Python 3.12（系统 Python312，含 fastapi/uvicorn/openai/requests/pydantic/pywebview/paramiko/Pillow）
- 启动需 PYTHONUTF8=1（避免中文编码问题）
- 本机 8000 端口：装机版占用时源码用 MODELFLOW_PORT=其他端口
- Git Bash（shell），node（JS 语法检查），Inno Setup 6.7.3（ISCC 路径写死在 make_release.py）
- 授权服务依赖：云服务器 /opt/mflic/venv（fastapi+uvicorn）
