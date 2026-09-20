# 交接文档（给下一个 agent）

> 更新时间：2026-09-20 · 上一任：Qoder agent 会话
> 本文**不含任何密钥**，只写路径。密钥与站点全局信息在同目录之外的私人文档
> `C:\Users\李星历\Desktop\个人开发信息\个人网站信息\Voyra个人网站说明.md`（含全部密钥，严禁入库）。
> 读那一份的 0 节 + 2.6 节 + 5 节，再回来看这里。

---

## 0. 30 秒自检：现在线上是什么样

| 项 | 状态 | 怎么复核 |
|---|---|---|
| 源码仓库 | `liixnglinb/Loom`（**公开**，main） | `gh api repos/liixnglinb/Loom/commits/main --jq .sha` |
| 旧 ModelFlow | 保留在同仓库 `modelflow-legacy` 分支 + `v0.8.8-legacy` 标签 | `gh api repos/liixnglinb/Loom/branches --jq '.[].name'` |
| 安装包 | `https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/Loom-1.0.0-setup.exe`（36.2 MB，公有读） | `curl -sI <url> \| grep -i content-length` |
| 版本清单 | 同桶 `latest.json`（公有读，含 version/url/sha256/size/notes） | `curl -s .../latest.json` |
| 下载页 | `https://lxlrwxs.top/modelflow/`（**URL 沿用 modelflow**，内容已是 Loom，无授权码） | 带浏览器 UA 抓页面，`grep -c 授权码` 应为 0 |
| 软件内更新 | 读同一份 `latest.json`；打包态可静默装上 | `curl -s localhost:8000/api/update` |

```bash
# 一把梭验证（任何一条不对就是分发链断了）
curl -s https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/latest.json
curl -sI https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/Loom-1.0.0-setup.exe | head -3
curl -s -A "Mozilla/5.0" https://lxlrwxs.top/modelflow/ | grep -o "Loom-[0-9.]*-setup.exe" | head -1
```

---

## 0.5 交接这一刻的仓库状态

| 项 | 值 | 怎么复核 |
|---|---|---|
| 线上 main | 停在 `fd4b7f5`（2026-09-19 的 upload 修复） | `gh api repos/liixnglinb/Loom/commits/main --jq .sha[0:7]` |
| 未推提交 | **有** —— 至少含「设置页吸收 Codex 形态」和本文档这次改动 | `git log --oneline origin/main..HEAD` |
| 工作区 | 干净，130 条测试全过 | `git status --short` |
| 本地服务 | 8000 端口有一个源码态实例在跑（数据在 `modex-data/`） | `curl -s localhost:8000/api/health` |

要推：`unset GITHUB_TOKEN GH_TOKEN`，再走第 3 节那条 `http.curloptResolve` 命令。推完再跑一次上面
那条 `gh api`，**线上 sha 真变了才算上去**（本地 `origin/main` 引用会滞后，别拿它当线上状态；
本文档也故意不写死本地 HEAD 的 sha —— 改它自己就会多出一个提交）。

**上一轮（2026-09-20）做完并已验，别重复做**：设置页换成 Codex 那套形态 ——
明暗预览磁贴、字号/缩放/内容宽度三条带数字读数的滑块、卡片头部动作位（挂「恢复默认外观」）、
键位页内搜索 + 双键帽；强调色换成色板芯片；更新页下载中加真刻度条。
深浅两套主题都用 `getComputedStyle` 量过，用户外观偏好已逐项还原。
新骨架的用法见第 4 节，新钉住的契约见第 6 节。

---

## 1. 等用户点头才能动的（别自己拍板）

1. **PPT / Word 的真渲染**。浏览器画不出 pptx/docx 版式，这是硬限制。三条路已摆给用户：
   - A LibreOffice headless 转 PDF 再预览（保真最高，代价几百 MB 外部依赖）；
   - B 纯 Python 拆 OOXML 做"分镜预览"（读 `ppt/slides/slideN.xml` 的文字 + `ppt/media/` 的图，按页出卡片；零新依赖，约 150–200 行 + 测试）；
   - C 改内置流程：让智能体产出 markdown/HTML 源，最后一步再转 pptx（实时预览直接复用现成的 markdown 渲染器）。
   **推荐 B + C**。B 点头就能做；C 要改内置流程和技能提示词，动的是用户定过的东西。
2. **要不要下线旧授权后端**。`functions/modelflow/*`、D1 `mflic`、`/modelflow/admin/` 还在部署、还能打开，但已无任何页面引用。下线不可逆（历史授权码数据会没）。
3. **COS 保留策略**。`upload_cos.py` 现在**只列不删**（桶刚被清空过一次，删线上包必须是显式动作）。攒到两个版本以上再谈"留最近两个"。
4. **代码签名**。安装包没签名（`installer.iss` 里没有 SignTool），Windows SmartScreen 会拦"未知发布者"。买证书是花钱的决定，要用户定。

---

## 2. 已知缺口 / 没做完的事（按重要性）

- **`apply_update()` 的打包态分支没真跑过。** 只验证了源码态明确拒绝、以及有任务在跑时返回 409。真自装要装两个版本互演，且会改本机程序 —— 上一任没敢擅自做。改这块时注意：批处理用 `encoding="mbcs"` 写（中文用户名路径 + cmd 代码页），以及 `DETACHED_PROCESS` 起 cmd 后 `os._exit(0)` 的时序。
- **下载页的兜底版本号/体积要人工同步。** 页面正常运行时从 `latest.json` 现拉，拉不到才用写死的 `1.0.0` / `36 MB`。发新版时**记得改** `D:\Voyra 个人网站\public\modelflow\index.html` 里那两处（第 5 节 SOP 里也写了）。想彻底根治：让按钮在 fetch 成功前禁用，而不是显示一个可能说谎的兜底值。
- **没有 CI。** `liixnglinb/Loom` 里连 `.github/` 都没有，130 条测试只在本地跑。公开仓库加一条 `python -m pytest -q` 的 workflow 成本很低，但会引入"CI 绿了才发版"的新约定，先问。
- **`update_repo` / `update_asset` 是废弃设置项**，值还留在用户机器的 settings 表里、`/api/settings` 也还回得出来。代码已不读它们。清理要连带迁移，别顺手删一半。
- **只有 Windows 安装包。** macOS/Linux 靠源码跑（README 里这么写的，没撒谎）。
- **组件图鉴里有一行 mock 数据写着 `modelflow`**（`src/pages/UIKit.jsx` 的演示表格）。是组件示例不是产品入口，上一任故意没改。
- **工作区面板是 3 秒轮询**，不是文件事件订阅（子进程直接写盘，没有可订阅的事件，Windows 上也不想在包里塞 watchdog）。一步里连写多个文件时面板最多滞后 3 秒 —— 设计取舍，不是 bug。
- **侧栏折叠（图标轨道）在 ≤860px 不生效**，因为那个宽度下侧栏本来就横过来了。有意为之，见 `style.css` 里 `@media (min-width:861px)` 那一段。
- **孤儿工作区只能看不能清。** 「使用统计」报得出孤儿数量和体积，但没有任何删文件的端点 —— 破坏性动作宁可先不给人按。要做「一键清理」得先和用户确认保留策略（第 1 节第 3 条）。
- **设置页刻意没跟的 Codex 形态**：侧栏折叠没做设置项（品牌位点击 + Ctrl B 已经是两个入口，再加第三个违反「一个功能只留一个入口」）；明暗磁贴里那个小窗口是纯 CSS 假预览，不是真缩略图 —— 别为它去截图。

---

## 3. 这台机器的坑（不知道会白白耗掉一小时）

- **`github.com` 被 DNS 指到一个不响应的加速 IP**（`101.198.198.198`），`git push` / `curl https://github.com` 一律超时；`api.github.com` 正常。绕过办法（**别改系统 hosts**）：
  ```bash
  git -c http.curloptResolve=github.com:443:140.82.113.3 push origin main
  ```
  真 IP 会轮换，一个不行就换 `140.82.112.3` / `20.205.243.166` 多试几轮。推完用
  `gh api repos/<o>/<r>/commits/main --jq .sha` 确认线上真状态（本地 `origin/main` 引用可能滞后）。
- **动 GitHub Actions / secret 前先 `unset GITHUB_TOKEN GH_TOKEN`**，本机那个环境变量会劫持凭据且无 workflow 权限。
- `python` 不在 PATH（中文用户名把路径搞坏了）。用绝对路径：
  `C:\Users\李星历\AppData\Local\Programs\Python\Python312\python.exe`，并且带 `PYTHONUTF8=1`。
- **uvicorn 没有热重载**：改了 `app/*.py` 必须重启服务，否则你验的是旧代码（上一任在这上面被骗过两次）。
  静态文件不用重启，但浏览器侧还有一层缓存 —— 改 `static/` 后要升 `index.html` 里的 `?v=` 令牌。
- `db.get_setting` 有**进程内缓存**：绕过 API 直接改库，正在跑的服务看不见。
- Git Bash 里 `taskkill` 要写 `taskkill //PID xxx //F`（双斜杠）。
- **D 盘那些单行压缩 HTML（各下载页）用 Edit/Write 工具会 Native execution failed**，必须用 Python 脚本做字符串替换 + 计数断言。普通 `.jsx` / `.css` 文件不受影响。
- 内嵌的 in-app 浏览器经常 `visibilityState: hidden`，CSS `:hover` 的 computed style 量不到；JS 驱动的提示（`data-tip`）可以用 `dispatchEvent(new PointerEvent('pointerover'))` 触发。截图工具基本用不了（`NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`）。
- **隐藏标签页里 CSS transition 不走**：切完主题立刻 `getComputedStyle` 会量到上一套主题的颜色，看起来像暗色令牌漏进浅色。多等两秒或先重渲染再量，别急着改 CSS。
- 想在浏览器里验一个只有真下载才会出现的状态：临时 `window.fetch = (u,o)=> String(u).includes('/api/update')&&… ? Promise.resolve(new Response(JSON.stringify(假状态))) : real(u,o)`，再 `await renderSettings('update')`。**验完必须把 fetch 换回去并重渲染**，否则页面留着一个不存在的下载进度。

---

## 4. 文件地图（谁负责什么）

```
app/main.py            全部 /api 路由。注意 /api/settings/bulk 只收 ui_ 前缀
app/runner.py          执行引擎：工作区、SSE 事件、检查点、日志读取、使用统计
  ├ _is_internal()     整条相对路径任一段以下划线开头 = 内部文件，别泄漏进清单
  ├ ws_file()          工作区路径校验只写这一处（预览和下载共用）
  └ read_workspace_file()  预览单文件；内部文件与二进制不给正文
app/agents.py          Claude / Codex CLI 适配（参数拼装 + 流式解析）
app/updater.py         读 COS latest.json → 下载 → 核对 sha256 → 打包态静默装上
app/paths.py           FROZEN 分支：打包态数据在 exe 同级 data/
static/ui.js           中英双字典 + ICONS + 外观通道 + mdToHtml
static/app.js          路由、侧栏（含折叠轨道）、tooltip、设置页各分区、更新胶囊
  ├ spanel/srow/sblk  设置页三种骨架：卡片（可带头部动作）、右侧控件行、整块控件行
  ├ apTiles/apSwatches 明暗磁贴与强调色板，档位取 window.AP_OPTS，点击只改类不重渲染
  └ sslider/slPick    字号/缩放/内容宽度三条滑块：oninput 只 previewAppearance，onchange 才落盘
static/run.js          运行台：转录、进程卡、工作区实时面板、日志查看
static/style.css       设计令牌。圆角只准 --r-1…--r-5/--r-pill；字号只准 --fs-* 七档
  └ --sw-lite-*/--sw-dark-*/--sw-acc-*  明暗磁贴与色板要显示「另一个主题长什么样」，
     故意固定在 :root 里，不随 html[data-theme] 走 —— 别顺手把它们搬进主题块
tests/                 130 条。test_static_contract.py 是静态资产契约（见第 6 节）
loom_launch.py         打包态入口（pywebview 窗口 → 失败退回浏览器）
loom.spec              PyInstaller。**excludes 里那串重库别删**，见 make_release 注释
installer.iss          Inno。装 {localappdata}\Programs\Loom，卸载保留 data\
make_release.py        一键出 setup.exe + latest.json；拒绝把开发机 data/ 打进包
upload_cos.py          上传 + 设公有读 + 匿名回读验证（签名成功 ≠ 公网能下）
make_icon.py           PIL 画图标（本机无 SVG 渲染器），产物在 assets/
```

---

## 5. 发版 SOP（照做）

```bash
cd "C:/Users/李星历/Desktop/FlowForge 数模流水线"
PY="/c/Users/李星历/AppData/Local/Programs/Python/Python312/python.exe"

# 1. 版本号 + 全量测试
#    改 app/version.py，然后：
PYTHONUTF8=1 "$PY" -m pytest -q

# 2. 打包（图标动过先跑 make_icon.py）
PYTHONUTF8=1 "$PY" make_release.py --notes "这一版改了什么"

# 3. 先提交源码（别先传包，失败了好回退）
git add -A && git commit -m "release: X.Y.Z —— …"
unset GITHUB_TOKEN GH_TOKEN
git -c http.curloptResolve=github.com:443:140.82.113.3 push origin main

# 4. 上传 COS（公有读 + 匿名回读验证）
PYTHONUTF8=1 "$PY" upload_cos.py

# 5. 同步下载页的兜底版本号与体积（fetch 失败时用户看到的就是这两个值）
#    D:\Voyra 个人网站\public\modelflow\index.html —— 必须用 Python 脚本改
#    改完 npm run build → commit → push（Cloudflare 1~2 分钟上线）

# 6. 线上验证：第 0 节那三条 curl + 装一次新机看「检查更新」
```

---

## 6. 每次改完跑什么

```bash
PYTHONUTF8=1 "<python>" -m pytest -q          # 130 条，不需网络
```

契约测试会替你看住这些事，报错时**先怀疑自己改错了，别急着放宽断言**：

- 中英字典必须一一对应，且**不能有没人用的 key**（`t()` 用 `||` 取字典会把空文案印成 key 本身）。
- CSS 变量必须有定义；圆角/字号只能取刻度里的档位；`--fs-*` 七档每档都得有人用。
- 模板里写了 `class="xxx"` 而 style.css 没这条规则 → 直接失败（上一任就是这么写出过一个 `.pl-row-sub`，量出来字号还是 13px）。
- 静态 `style="font-size:…/padding:…"` 禁止（绕过刻度）；动态宽度不算。
- 侧栏折叠轨道：清单里每个文字类都必须有 `display:none` 规则，**多藏一个也算漂移**。
- 绑了快捷键就必须写进「键位」说明，反之亦然。
- 滑块读数说「13px」：`ROOT_PX`（app.js）必须等于 CSS 里 `html{font-size:calc(13px * …)}` 的那个 13，测试钉着。
- 设置页外观的档位表只有一处真相：`ui.js` 的 `TEXT_SIZES/ZOOMS/WIDTHS/THEMES/ACCENTS`，`APP` 里的键名和
  `loadAppearance` 白名单必须同名（测试钉着），否则滑块会静默停在 0 档。
- 路径越界用例是参数化的一整套（`../../db`、`%2e%2e`、绝对路径…），新加读文件的端点要接进同一套校验。

改完**在浏览器里量一遍**再收工：`getComputedStyle` 拿真实值，别凭眼睛看。
上一任靠这个抓到过：轨道被两个图标按钮撑破 4px、图标按钮漏 `data-tip-any`、
换语言时两处文案不刷新。
