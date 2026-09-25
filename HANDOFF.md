# 交接文档（给下一个 agent）

> 更新时间：2026-09-25 · 上一任：Qoder agent 会话
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
| 线上 main | 每次发版都推到当轮 HEAD（不写死 sha，改它自己就多一个提交） | `gh api repos/liixnglinb/Loom/commits/main --jq .sha[0:7]` |
| 未推提交 | 以 `git log --oneline origin/main..HEAD` 为准；发版 SOP 第 3 步就是推它 | 同左 |
| 工作区 | 测试全过（条数以 `pytest -q` 末行为准，别抄这里） | `git status --short` |
| 本地服务 | 8000 端口有一个源码态实例在跑（数据在 `modex-data/`） | `curl -s localhost:8000/api/health` |

要推：`unset GITHUB_TOKEN GH_TOKEN`，再走第 3 节那条 `http.curloptResolve` 命令。推完再跑一次上面
那条 `gh api`，**线上 sha 真变了才算上去**（本地 `origin/main` 引用会滞后，别拿它当线上状态；
本文档也故意不写死本地 HEAD 的 sha —— 改它自己就会多出一个提交）。

**这一轮（2026-09-25，发 1.2.0）做完的**：权限模式收成三档并让模式接管沙箱（第四档用检查点代替）、
运行级模型覆盖（候选只列真存在的端点预设）、工作文件夹（**只换智能体的 cwd，Loom 自己的写入仍留在
工作区**）、记忆文件在这台机器上可写（路径仍只从盘点清单里算）、字号基准 13→14 按参考图重标定八档、
暗色侧栏抬到卡片同色（分栏靠色差不靠线）、无边框窗口 + 自绘三枚窗控。

**这一轮留下三条没验的，别当成已验**：① 打包态 `apply_update()` 仍然没真跑过（下面第 2 节那条老账，
1.2.0 不改变这一点）；② 安装包仍无代码签名，SmartScreen 照拦；③ 无边框窗口里那三枚按钮**是否真拿到
`js_api` 桥**，在本机 harness 里脚本化不出来 —— `webview.start(func, args)` 的 loaded 回调、
`win.events.loaded`、后台线程里的 `win.evaluate_js` 全都不返回，只能证明窗口以 `frameless=True`
建出来、WebView2 加载了页面。浏览器态（无桥 → `#tbWin` 整块 `display:none`）是量过的，
原生态的按钮点击链路要靠人装一次才知道。

**上一轮（2026-09-21）做完并已验，别重复做**：六路分区子智能体把"页面上写着的功能到底实现了没有"
逐条对过一遍，确认的缺陷已修完 ——
`llm.chat` 两个分支各引用不存在的名字（"检测连通"在生产里恒红）、产物下载口能取到内部引擎转录、
更新器在下载飞行中被强制检查踩掉进度、统计页"总次数"跟着 500 条窗口一起卡死、
孤儿判定按窗口比会把正常现场报成孤儿、产出面板「刷新」按钮点一下 ReferenceError、
设置页搜索"敲任意乱码都算命中"、技能读口比写口松。
另外两件事改的是约定，别退回去：codex 0.154 的默认 `wire_api` 必须是 `responses`；
出厂技能的 `BASE/skills` 扫描四支全撤（旧安装目录里那份只读副本会复活）。
新钉住的契约见第 6 节，两条断言的实测出处见第 2 节末尾。

**再上一轮（2026-09-20）**：设置页换成 Codex 那套形态 ——
明暗预览磁贴、字号/缩放/内容宽度三条带数字读数的滑块、卡片头部动作位（挂「恢复默认外观」）、
键位页内搜索 + 双键帽；强调色换成色板芯片；更新页下载中加真刻度条。
深浅两套主题都用 `getComputedStyle` 量过，用户外观偏好已逐项还原。
新骨架的用法见第 4 节，新钉住的契约见第 6 节。

---

## 1. 等用户点头才能动的（别自己拍板）

1. **PPT / Word 的真渲染**。浏览器画不出 pptx/docx 版式，这是硬限制。三条路已摆给用户：
   - A LibreOffice headless 转 PDF 再预览（保真最高，代价几百 MB 外部依赖）；
   - B 纯 Python 拆 OOXML 做"分镜预览"（读 `ppt/slides/slideN.xml` 的文字 + `ppt/media/` 的图，按页出卡片；零新依赖，约 150–200 行 + 测试）；
   - C 让智能体产出 markdown/HTML 源，最后一步再转 pptx（实时预览直接复用现成的 markdown 渲染器）。
   **推荐 B + C**。B 点头就能做；C 动的是流程和技能提示词，要用户定（软件已经不随包带任何流程模板和技能，
   改的是用户自己建的那些）。
2. **要不要下线旧授权后端**。`functions/modelflow/*`、D1 `mflic`、`/modelflow/admin/` 还在部署、还能打开，但已无任何页面引用。下线不可逆（历史授权码数据会没）。
3. **COS 保留策略**。`upload_cos.py` 现在**只列不删**（桶刚被清空过一次，删线上包必须是显式动作）。攒到两个版本以上再谈"留最近两个"。
4. **代码签名**。安装包没签名（`installer.iss` 里没有 SignTool），Windows SmartScreen 会拦"未知发布者"。买证书是花钱的决定，要用户定。
5. **软件侧要不要跟 tabbit 的工艺（不含配色）**。2026-09-20 用户拍的是"不改软件里面的配色"，所以下面这些**只提了没做**，要做得排进一次发版（改了源码但不出包，就和线上 1.0.0 漂移）：
   圆角按 tabbit 节奏抬（`--r-4` 14→16、`--r-5` 18→24）、阴影改大模糊低透明度分层 + 同色投影、`--ease` 换成实测主控曲线
   `cubic-bezier(.4,0,.2,1)`、以及**离线打包 Montserrat 给西文用**（用户当时点了这条，但和上面一起冻住了；
   注意 `test_font_faces_declare_one_standard_weight_each` 要求全站 @font-face 的字重集合**正好**是 400/500/600/700，
   可变字体轴 `100 900` 会直接判失败）。

---

## 2. 已知缺口 / 没做完的事（按重要性）

- **两条对引擎的断言是在本机二进制里量出来的，不是查文档查来的。**
  `D:\npm-global\node_modules\@openai\codex\node_modules\@openai\codex-win32-x64\vendor\x86_64-pc-windows-msvc\bin\codex.exe`（0.154.0）里
  写着 `` `wire_api = "chat"` is no longer supported / How to fix: set `wire_api = "responses"` `` —— 所以 `agents._codex_args`
  的默认值不能是 chat，配了端点的 codex 步骤否则会在启动那一刻就死。同一份二进制里 EventMsg 枚举明确带
  `TokenCount` / `token_count`，所以"codex 没有 token_count 事件"那条断言是**假的**，别照它改解析。
  核对方法：mmap + 字符串搜，别执行 CLI（费配额、还会动用户本机 relay）。
- **供应商目录的 api_base 要实测，别从别家工具的示例抄。** 2026-09-21 拿不带密钥的 POST 逐条探过 9 条
  anthropic 条目（判读：404 = 路径不存在，401/403/429 = 路径在、只是要鉴权）：月之暗面 `/v1/messages` 与
  百度千帆 `/v2/tokenplan/personal/v1/messages` 都是 404，两家的 anthropic 路其实各自在 `/anthropic`，已改；
  硅基流动的 `/v1/messages` 返回 401，是唯一一条以 `/v1` 结尾还成立的，所以它在
  `test_anthropic_catalog_bases_are_not_openai_paths` 的名单里。**新增条目按同一办法探，别照文档抄。**
- **`app/cli_inventory.py` 只许回名字、条数、路径 —— 值一个字节都不许进接口。** 它扫的是两家 CLI
  自己的配置面，那些文件里就是真密钥：本机 `~/.claude/settings.json` 的 `env` 里有
  `ANTHROPIC_AUTH_TOKEN`、`~/.claude.json` 里有 `oauthAccount`、`~/.codex/config.toml` 里有
  `experimental_bearer_token`。所以预览口只开给四类"用户自己写的 markdown"
  （记忆 / 技能 / 命令 / 子智能体），mcp / hooks / plugins 连预览都没有。
  别顺手加"编辑"：schema 不归我们（同一轮里 codex 一次升级就把 `wire_api="chat"` 判死了），
  写坏的是用户 CLI 本体，而且 Loom 自己也跑不了 —— 它靠那两个 CLI 出正文。
  真机上踩到过两处误判（假数据里没有的形状）：`officialMarketplaceAutoInstalled` 这类记账布尔
  被当成插件、`[mcp_servers.node_repl.env]` 子段被当成第二台 MCP 服务器。
- **步骤的 `skill_src` 是"引用哪一家的技能目录"，不是路径。** 三家技能同格式（`<name>/SKILL.md`），
  所以能并列选择；但外部技能只往提示词里放一句"按你原生机制加载并遵守「x」"，
  **不读文件、不抄正文** —— 抄一份进工作区等于把别人会升级的东西冻成我们的快照。
  `skill_src` 只有一个字段，所以一步的主技能与叠加技能必须同源。引擎与来源不匹配时
  只在轨迹里留原因，不禁用。导出/导入必须带上它（`test_the_skill_source_survives_the_roundtrip`）。
- **统计页的两个开关（每日/每周/累计、近 7/近 30）刻意不落库。** 它们是这一屏的视图，
  不是外观偏好；写进 `ui_*` 那套通道就要多一个设置键、多一处白名单，
  而 `test_appearance_bulk_cannot_touch_engine_keys` 那类边界也会被拖进来。
  热力图列数恒定 52（锚点是"今天那一周的周日往回数 51 周"）—— 按天数换算再补一周的写法
  会在非周日收尾时多出第 53 列，把网格顶出卡片。
- **统计页有两套口径，别混。** 逐条累计（token / 时长 / 步骤 / 成本）只扫最近 500 条 run —— 一次
  `list_runs` 要把每行 steps JSON 全解出来，跑几千条再点设置页会卡住；而"总次数"和状态分布走
  `db.run_status_counts()`（COUNT(*)），孤儿工作区判定走 `db.all_run_ids()`（全表）。
  把后两者接回窗口的写法都出现过，后果分别是：跑到 501 就永远显示 500、第 501 条的现场被当成孤儿报出来。
- **软件只剩一个技能目录。** `paths.BASE / "skills"` 那四支扫描（列表 / 详情 / 另存源 / 提示词装载）已全撤：
  装过 1.0.0 的目录里还留着 `skills/ff-*`，扫它等于让出厂技能悄悄复活。随之 `editable`/`source` 恒为真，
  技能徽标、只读提示、编辑器 readonly 与 `sk.viewTitle`/`sk.readonly`/`sk.badgeUser`/`c.user` 一并删掉；
  「另存副本」从"只读才能按"改成常驻，否则这条功能就没入口了。
- **`extra.model_map` / `extra.fallback_model` / `extra.wire_api` 是活的但没有界面。** 它们由
  `runner.resolve_agent_config` 读，界面上既看不见也改不了，唯一会碰它们的是「编辑供应商」——
  而 `pfSave` 以前把 `extra` 整列覆盖写，等于改一次名字就把模型阶梯抹平了。现在表单只拥有自己那两个键。
  真要做界面，先和用户确认这三个键的语义再摆控件。
- **`apply_update()` 的打包态分支没真跑过。** 只验证了源码态明确拒绝、以及有任务在跑时返回 409。真自装要装两个版本互演，且会改本机程序 —— 上一任没敢擅自做。改这块时注意：批处理用 `encoding="mbcs"` 写（中文用户名路径 + cmd 代码页），以及 `DETACHED_PROCESS` 起 cmd 后 `os._exit(0)` 的时序。
- **下载页的兜底版本号/体积要人工同步，而且是 9 处不是 2 处。** 页面正常运行时从 `latest.json` 现拉，拉不到才用写死的值。1.0.1 实测数过：版本号 6 处（`navVer` / `heroVer` / `btnVer` / `ftVer` 四个 span + 下载直链文件名 `Loom-X.Y.Z-setup.exe` + 更新器 mock 里那句"更新至 X.Y.Z"），体积 3 处（`heroSize` / `btnSize` / 安装步骤正文那句"安装包约 N MB"）。**改法只能用 Python 脚本做字符串替换 + 计数断言**（先断言 6 和 3，换完断言旧值归零）—— 这文件用 Edit/Write 会 Native execution failed，而漏一处不会报错，只会在 fetch 失败时给用户看一个说谎的兜底值。想彻底根治：让按钮在 fetch 成功前禁用，而不是显示兜底值。
- 下载页 FAQ 里以前写死过测试条数，几天里飘了三次（122→130→145）。2026-09-20 改成不报数、只说"看守哪些契约"，这条同步义务到此为止 —— 别再往页里塞具体条数。
- **下载页的配色基准是软件，不是任何外部参考站。** 那张页的令牌逐值等于本仓库 `static/style.css`：页面 chrome 对 `:root`（浅色），页内那张产品图对 `html[data-theme="dark"]`（页面 `#161616`、侧栏 = 卡片 = 浮层 `#2b2b2b`、内凹面板 `#202020`、条带 `rgba(13,13,13,.19)`、描边 `rgba(255,255,255,.1/.065/.15)`、输入台圆角 `--r-4` 12px、mock 外壳 `--r-5` 16px）。**改软件配色 = 要同步改它**；反过来照抄第三方站的色相是明确不要的（用户 2026-09-20 纠正过一次）。它仿 tabbit.com 仿的是**工艺**：滚动揭示、`perspective` + `rotateX` 的 hero 抬起、大模糊低透明度阴影、圆角节奏、字距纪律。
- **那张产品图会随软件过期，而且过期点很隐蔽。** 2026-09-25 这一轮对出来的四处漂移：mac 的三枚 traffic-light（软件已换自绘窗控的无边框窗口）、侧栏那条 `border-right`（软件删了，分栏只靠色差）、进度行的 `--d-panel` 底带（软件的 `.rp-bar` 不铺底）、"刚写入"推到行尾（被浮在右上角的进程卡压住半截）。**逐值比 `getComputedStyle`，别目测像不像** —— 这四条里没有一条是"看一眼能发现"的。
- **这张页被砍过一次，别再砍。** `9c53b61`（2026-09-19）把它从 64KB 删到 25.8KB，交互动效、区块、mock 窗口的精细度全没了；`a28065e`（2026-09-20）按软件真实结构重做到 63.7KB。改它之前先 `git show` 对比一下字节数，掉一档就是又在删东西。
- **没有 CI。** `liixnglinb/Loom` 里连 `.github/` 都没有，测试只在本地跑。公开仓库加一条 `python -m pytest -q` 的 workflow 成本很低，但会引入"CI 绿了才发版"的新约定，先问。
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
  令牌算法（**别把 `index.html` 算进去**，否则改令牌会改哈希，永远追不上）：
  `md5(relpath + bytes)` 累加 `static/**` 里的 `.js/.css/.svg/.png`，取前 8 位。
- `db.get_setting` 有**进程内缓存**：绕过 API 直接改库，正在跑的服务看不见。
- Git Bash 里 `taskkill` 要写 `taskkill //PID xxx //F`（双斜杠）。
- **D 盘那些仍是单行压缩的 HTML（部分下载页）用 Edit/Write 工具会 Native execution failed**，必须用 Python 脚本做字符串替换 + **计数断言**（不断言就会静默漏替换）。
  `public/modelflow/index.html` 现在已经换成多行可读版，Edit/Write 正常 —— 但批量改色值/文案时照样推荐脚本 + `assert s.count(old) == n`，
  2026-09-20 就是这么抓到"以为只有一处、实际有两处"的。普通 `.jsx` / `.css` 文件不受影响。
- 内嵌的 in-app 浏览器经常 `visibilityState: hidden`，CSS `:hover` 的 computed style 量不到；JS 驱动的提示（`data-tip`）可以用 `dispatchEvent(new PointerEvent('pointerover'))` 触发。截图工具基本用不了（`NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`）。
- **隐藏标签页里 CSS transition 不走**：切完主题立刻 `getComputedStyle` 会量到上一套主题的颜色，看起来像暗色令牌漏进浅色。多等两秒或先重渲染再量，别急着改 CSS。
- 想在浏览器里验一个只有真下载才会出现的状态：临时 `window.fetch = (u,o)=> String(u).includes('/api/update')&&… ? Promise.resolve(new Response(JSON.stringify(假状态))) : real(u,o)`，再 `await renderSettings('update')`。**验完必须把 fetch 换回去并重渲染**，否则页面留着一个不存在的下载进度。

---

## 4. 文件地图（谁负责什么）

```
app/main.py            全部 /api 路由。注意 /api/settings/bulk 只收 ui_ 前缀
                       技能只有一个目录（paths.USER_SKILLS_DIR），读写四条口共用 _skill_dir_safe
app/runner.py          执行引擎：工作区、SSE 事件、检查点、日志读取、使用统计
  ├ _is_internal()     整条相对路径任一段以下划线开头 = 内部文件，别泄漏进清单
  ├ ws_file()          工作区路径校验只写这一处（预览和下载共用）
  └ read_workspace_file()  预览单文件；内部文件与二进制不给正文
app/agents.py          Claude / Codex CLI 适配（参数拼装 + 流式解析）
app/cli_inventory.py   两家 CLI 配置面的只读盘点：只回名字/条数/路径，值不进接口
                       ├ scan()          设置页「Agent 能力」的数据源
                       ├ preview_text()  只放四类用户写的 markdown
                       └ reveal_path()   /api/reveal 的 agent 分支，绝不 mkdir
app/updater.py         读 COS latest.json → 下载 → 核对 sha256 → 打包态静默装上
app/paths.py           FROZEN 分支：打包态数据在 exe 同级 data/
static/ui.js           中英双字典 + ICONS + 外观通道 + mdToHtml
static/app.js          路由、侧栏（含折叠轨道）、tooltip、设置页各分区、更新胶囊
  ├ stSeg/secRepaint   分段控件与"只重渲染当前分区"；页头 chip 也要一起补，否则切引擎后还写着旧引擎
  └ tokenHeat/hmValues 一年热力图三档读数共用一套格子；悬停是两行 data-tip（&#10; 分隔，裸换行会被归一化成空格）
  ├ spanel/srow/sblk  设置页三种骨架：卡片（可带头部动作）、右侧控件行、整块控件行
  ├ apTiles/apSwatches 明暗磁贴与强调色板，档位取 window.AP_OPTS，点击只改类不重渲染
  └ sslider/slPick    字号/缩放/内容宽度三条滑块：oninput 只 previewAppearance，onchange 才落盘
static/run.js          运行台：转录、进程卡、工作区实时面板、日志查看
static/style.css       设计令牌。圆角只准 --r-1…--r-5/--r-pill；字号只准 --fs-* 七档
  └ --sw-lite-*/--sw-dark-*/--sw-acc-*  明暗磁贴与色板要显示「另一个主题长什么样」，
     故意固定在 :root 里，不随 html[data-theme] 走 —— 别顺手把它们搬进主题块
tests/                 契约与回归（条数以 pytest -q 为准）。test_static_contract.py 是静态资产契约（见第 6 节）
loom_launch.py         打包态入口（pywebview 窗口 → 失败退回浏览器）
loom.spec              PyInstaller。**excludes 里那串重库别删**，见 make_release 注释
installer.iss          Inno。装 {localappdata}\Programs\Loom，卸载保留 data\
make_release.py        一键出 setup.exe + latest.json；拒绝把开发机 data/ 打进包
upload_cos.py          上传 + 设公有读 + 匿名回读验证（签名成功 ≠ 公网能下）
sync_landing.py        发版第 5 步：下载页兜底版本号/体积，锚点 + 计数断言都写死在里面
make_icon.py           PIL 画图标（本机无 SVG 渲染器）。大档走矢量几何，16/20/24/32/40
                       走 SMALL 表按目标像素网格各画一遍 —— 别改回"画 1024 再缩放"，
                       眼距 9/120 缩到 16px 只剩 1 列，任务栏上就是一团糊的。
                       产物除 assets/（ico + 各档 PNG）外还写 static/logo-sm.svg 与
                       static/favicon-{16,32}.png，侧边栏和标签页用的是这两份小尺寸变体。
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

# 5. 同步下载页的兜底版本号与体积（fetch 失败时用户看到的就是这些值）
#    python sync_landing.py <旧版本> <新版本> [新体积MB]   ← 6 处版本号 + 3 处体积，
#    锚点写死在脚本里（heroSize / btnSize / "安装包约 N MB"），带计数断言。
#    体积没变就不传第三个参数。别按"约 N MB"宽匹配 —— 页里还有 2.4 MB 的 mock
#    日志和"约 200 MB 磁盘"，宽匹配会把它们一起改掉。
#    文件在 D:\Voyra 个人网站\public\modelflow\index.html，用 Edit/Write 会
#    Native execution failed，只能脚本改。
#    改完 npm run build → commit → push（Cloudflare 1~2 分钟上线）

# 6. 线上验证：第 0 节那三条 curl + 装一次新机看「检查更新」
```

---

## 6. 每次改完跑什么

```bash
PYTHONUTF8=1 "<python>" -m pytest -q          # 全绿即可，不需网络
```

契约测试会替你看住这些事，报错时**先怀疑自己改错了，别急着放宽断言**：

- 中英字典必须一一对应，且**不能有没人用的 key**（`t()` 用 `||` 取字典会把空文案印成 key 本身）。
- CSS 变量必须有定义；圆角/字号只能取刻度里的档位；`--fs-*` 八档每档都得有人用。
- **`rem` 只准出现在 `--fs-*` 那八档，几何一律 px**（2026-09-22 定的）。根字号是
  `html{font-size:calc(14px * var(--text-scale))}`，也就是「文字大小」设置在动的东西 ——
  图标/内边距/行高一旦用 rem，选「特大」就等于把整个界面放大 26%，跟「界面缩放」
  （`body{zoom}`）职责重叠，而且这几轮量出来的像素节奏只在默认档成立。
  改前实测：图标 16.25px → 20.47px；改后两个档位都是 16.25px，字号照常 13 → 16.38px。
- 挂到 `window` 上的处理函数必须有调用方 —— 内联 `onclick` 只能调它们，但反方向没人管：
  把弹层改成首页时 ✕ 按钮没了，`tkHideSugs` 就成了孤儿，几百条测试一条不红。
- 模板里写了 `class="xxx"` 而 style.css 没这条规则 → 直接失败（上一任就是这么写出过一个 `.pl-row-sub`，量出来字号还是正文 14px）。
- 静态 `style="font-size:…/padding:…"` 禁止（绕过刻度）；动态宽度不算。
- 侧栏折叠轨道：清单里每个文字类都必须有 `display:none` 规则，**多藏一个也算漂移**。
- 键位是一张表（`app.js` 的 `KEYMAP`）：绑定和设置页的「键位」说明同源。加一行就必须有 `sc.<id>` / `sc.<id>D` 两份文案，全局那几行还得有 `KEY_ACTION` 里的处理函数 —— 别再写 `if(k===...)`。
- 圆角跟**嵌套层数**走：第一个圆角容器 `--r-4`，往里 `--r-3 → --r-2 → --r-1`；`--r-5` 只有四个批准例外（主输入台壳 / 对话框壳 / toast / 品牌底板）；胶囊档只给故意的胶囊和正圆（清单是 `NESTED_RADIUS` + `CIRCLE_50`，双向锁）。
- 侧栏一个入口一件事：同一次运行不在「项目」和另一组「最近」里各出现一次；run 嵌在自己的流程下面。
- 居中的浮层收起时必须 `pointer-events:none`（`inset:0` 的遮罩只用 opacity 收 = 全屏点不动）。
- **`ws` 和 `cwd` 是两件事，不许合并。** `ws` 是 Loom 自己的落盘处（派生工作区 `run-<id>`：转录、给 claude 的系统提示文件、步骤产物），`cwd` 只是智能体在哪个目录干活（下任务时选的文件夹）。合成一个的后果是具体的：`delete_run` 里那句 `rmtree(workspace_dir(...))` 会去删用户的工程目录，而 codex 那路会往里面写 `AGENTS.md` 覆盖人家的项目记忆 —— 所以 codex + 自定义文件夹在 `start_run` 就直接拒（按 `resolve_engine` 判，和实际跑的那套同源）。
- 派生工作区的目录名只有一份规则：`db.ws_dir_name(run_id)`。`runner._ws_path` 和 `create_run` 写进库的那个名字都必须走它 —— 从前是两份各写各的，库里存着 `run-run-<id>` 这种磁盘上根本不存在的名字。
- 滑块读数说「14px」：`ROOT_PX`（app.js）必须等于 CSS 里 `html{font-size:calc(14px * …)}` 的那个 14，测试钉着。
- 设置页外观的档位表只有一处真相：`ui.js` 的 `TEXT_SIZES/ZOOMS/WIDTHS/THEMES/ACCENTS`，`APP` 里的键名和
  `loadAppearance` 白名单必须同名（测试钉着），否则滑块会静默停在 0 档。
- **`node --check` 过一遍每个 `static/*.js`。** 其余契约全靠正则扫源码，看不见语法错误：
  这一轮把 Python 的"相邻字符串自动相连"当成 JS 写进字典，设置页整个白屏
  （`t is not a function`），200 条测试一条不红。
- 路径越界用例是参数化的一整套（`../../db`、`%2e%2e`、绝对路径…），新加读文件的端点要接进同一套校验。
- **内联 `onclick="x()"` 里的名字必须在 `window` 上找得到。** 四个脚本各自是 IIFE，没导出的函数在全局作用域里
  不存在 —— 产出面板那个「刷新」就是这么死的（按钮照画，点一下 ReferenceError，而几百条测试一条都不会红）。
  `test_inline_handlers_only_call_exported_globals` 现在盯着；它的兜底名单 `HOST_GLOBALS` 只有三个词，
  另有一条反向测试盯着这个名单别烂掉。
- 「检测连通」这条直连路有两道锁：`llm.chat` 的 64 token 硬顶，和 `test_llm_probe.py` 那组只桩到 HTTP
  一层的用例（路由侧的测试直接 monkeypatch `test_connection`，是**看不出** chat 内部引用了不存在的名字的）。

改完**在浏览器里量一遍**再收工：`getComputedStyle` 拿真实值，别凭眼睛看。
上一任靠这个抓到过：轨道被两个图标按钮撑破 4px、图标按钮漏 `data-tip-any`、
换语言时两处文案不刷新。
