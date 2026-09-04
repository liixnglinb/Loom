# ModelFlow 部署交接文档（COS 静态托管 · 前端授权门禁）

> 写给接手的 Agent / 维护者：读完本文即可直接接手 ModelFlow 的打包、上传、验证全流程。
> 本文不包含任何 API 密钥明文（SecretId/SecretKey 只存在于本地 `cos_secrets.json`，禁止提交/外传）。

---

## 〇、当前状态（2026-09-01 · 安全加固版）

- **版本**：0.7.6（已发布上线，2026-09-01）
- **线上最新版**：0.7.6（`release/ModelFlow-0.7.6-setup.exe`，151.8 MB，sha256=4c6a0f827632a4bc48a9d4bb0154a0e1109c6a43fed3c5a1688a8fce4d9a06e1）
- **COS 保留版本**：0.7.5 + 0.7.6（自动只留最近两个，0.7.4 已删除）
- **托管方式**：腾讯云 COS **私有桶** + Cloudflare Pages Functions 后端授权 + 限时预签名下载 URL
- **下载入口**：https://lxlrwxs.top/modelflow/ （Voyra 个人网站，输入授权码 → 后端 verify → 生成 5 分钟预签名 URL → 浏览器直接下载）
- **旧 VPS（SSH/SFTP）通道已弃用**：`upload_release.py` 不再使用（服务器 2026-09-25 到期）
- **COS 桶权限**：桶私有；`latest.json` / `index.html` 单独公有读；exe 直链返回 403，必须预签名下载

---

## 一、线上地址（直接可用）

| 用途 | 地址 |
|---|---|
| 下载页（输入授权码，实际入口） | `https://lxlrwxs.top/modelflow/` |
| 自动更新清单（公有读） | `https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/latest.json` |
| 安装包（COS 私有，直链 403，须预签名下载） | `https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/ModelFlow-0.7.6-setup.exe` |

**下载授权码（5 位，发给用户）**：

```
H2DTH  2FMGW  NFE8H  GX7VJ  9GAQF
```

> 授权码只以 SHA-256 哈希形式内嵌在下载页 `index.html` 的 `const CODES = [...]` 里，
> 不在网页中暴露明文。修改授权码后必须重新跑 `upload_cos.py` 重建下载页。

---

## 二、腾讯云 COS 资源

| 项 | 值 |
|---|---|
| 存储桶全名 | `modelflow-1447874637` |
| 地域 | `ap-guangzhou`（广州） |
| 桶权限 | **私有**（exe 直链 403）；`latest.json` / `index.html` 单独设公有读；下载须通过后端预签名 URL |
| 存储包 | 建议购买「1 元 50GB 标准存储容量包 / 1 年」，流量按量付费（0.5 元/GB） |
| 关键对象 | `index.html`、`latest.json`、`ModelFlow-{版本}-setup.exe` |

---

## 三、本地文件与密钥

| 文件 | 说明 |
|---|---|
| `cos_secrets.json` | **腾讯云密钥 + 桶信息 + 授权码列表**，只存在本地，严禁提交/外传 |
| `cos_secrets.example.json` | 密钥配置模板（占位符，可安全提交） |
| `upload_cos.py` | COS 上传脚本（替代旧 `upload_release.py`） |
| `make_release.py` | 打包脚本（版本号 → PyInstaller onedir → Inno Setup） |
| `release/latest.json` | 本地最新清单（上传时会重写 url 指向 COS） |
| `release/index.html` | 旧下载页（VPS 时代产物，现已不用，COS 用 `upload_cos.py` 动态生成的页面） |

`cos_secrets.json` 结构：

```json
{
  "secret_id": "腾讯云 SecretId",
  "secret_key": "腾讯云 SecretKey",
  "bucket": "modelflow-1447874637",
  "region": "ap-guangzhou",
  "base_url": "",
  "license_codes": ["H2DTH", "2FMGW", "NFE8H", "GX7VJ", "9GAQF"]
}
```

---

## 四、发版全流程（标准操作）

### 1. 打包

```bash
cd "C:\Users\李星历\Desktop\数学建模工作流软件"
"C:/Users/李星历/AppData/Local/Programs/Python/Python312/python.exe" -u make_release.py
```

> ⚠️ 必须用**系统 Python312**（`C:/Users/李星历/AppData/Local/Programs/Python/Python312/python.exe`），
> 它装了 PyInstaller 6.22.2 + 科学计算栈。box-agent 自带的 Python 3.12.6 没有 PyInstaller。

产物：`release/ModelFlow-{版本}-setup.exe` + `release/latest.json`。

### 2. 上传 COS

```bash
"C:/Users/李星历/AppData/Local/Programs/Python/Python312/python.exe" -u upload_cos.py
```

自动完成：上传 exe → 上传 latest.json（url 指向 COS）→ 生成并上传前端门禁版 index.html。

依赖（已装）：`cos-python-sdk-v5`。若缺失：
```bash
"C:/Users/李星历/AppData/Local/Programs/Python/Python312/python.exe" -m pip install cos-python-sdk-v5 -i https://pypi.org/simple
```
> 注意包名是 `cos-python-sdk-v5`，不是旧的 `qcloud_cos`（后者是 Python2 包，会报错）。

### 3. 验证

```bash
curl -s https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/latest.json
curl -s -I https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/ModelFlow-0.7.4-setup.exe
```

核对三件事：
1. `latest.json` 的 `url` 指向 COS exe 直链；
2. `sha256` 与本地 exe 重算一致；
3. exe 返回 `HTTP 200` + `Content-Type: application/x-msdownload`。

---

## 五、关键约定与坑

1. **密钥不入库**：`cos_secrets.json` 已列在本地敏感文件，任何 Agent 不得把它写进 git、回复正文、日志或产物。
2. **授权码与哈希**：授权码明文只存在于 `cos_secrets.json`；网页里只有 SHA-256。改授权码 → 改 `cos_secrets.json` 的 `license_codes` → 重跑 `upload_cos.py`。
3. **前端门禁的局限**：这是「简单版」门禁，文件本身仍可直链下载，懂技术的人能绕过。要真门禁需改云函数 + 私有桶（暂未做，用户明确暂缓）。
4. **旧 VPS**：`upload_release.py`（SSH 到 177.2.186.149）已停止使用，服务器 2026-09-25 到期后下载页若仍指向旧域名会失效，一切以 COS 为准。
5. **打包环境**：Inno Setup 6.7.3 编译器在 `C:/Users/李星历/AppData/Local/Programs/Inno Setup 6/ISCC.exe`。
6. **减重红线**：不得排除科学计算栈（matplotlib/pandas/scipy/numpy/pymupdf/PIL/pdfplumber/docx/openpyxl），只排除 numba/llvmlite/PySide6/jedi/IPython/pytest/sklearn。

---

## 六、软件端如何指向新更新源

软件「设置 → 软件更新 → 保存更新源」填：

```
https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com
```

（`updater.check()` 会请求 `{update_url}/latest.json`，`latest.json` 里的 `url` 是 exe 直链，
下载时 updater 会附带本机授权码 `?code=xxx`，COS 端暂不校验 code，因此不影响下载。）

---

## 七、接手检查清单

- [ ] `cos_secrets.json` 存在且字段齐全
- [ ] `release/latest.json` 与线上一致
- [ ] `curl latest.json` 返回 200 且 version 正确
- [ ] `curl -I exe` 返回 200 + application/x-msdownload
- [ ] 下载页输入授权码能解锁按钮
- [ ] 授权码明文未出现在任何线上文件或日志中

---

## 更新：第二版分发体系（2026-09-01 · 已上线）

下载入口整体迁到 **Voyra 个人网站（Cloudflare Pages + 腾讯云 COS）**，旧 VPS 授权服务同步搬到 Cloudflare Functions + D1。

### 线上地址（新）

| 用途 | 地址 |
|---|---|
| 网站「下载软件」入口 | 主站右上角 → https://lxlrwxs.top/modelflow/ |
| 下载页（Voyra 静态端，输入授权码后**直接自动下载**） | https://lxlrwxs.top/modelflow/ |
| 授权管理后台 | https://lxlrwxs.top/modelflow/admin/ |
| 软件激活/校验 API | https://lxlrwxs.top/modelflow/api/activate 、/api/verify |
| 下载文件 | 仍由腾讯云 COS 公有读直供（跨域已开，页面直接拉取 latest.json + exe） |

### 仓库（GitHub public：liixnglinb/Voyra，main 分支 → Cloudflare Pages 自动构建）

- 下载页：public/modelflow/index.html（前端哈希门禁，存 5 码 SHA-256，不暴露明文；验证通过即触发浏览器下载并关闭小窗，无中间过渡页）
- 真实图标：public/modelflow/logo-64.png / favicon-48.png（从 modelflow.ico 提取）
- 授权 API：unctions/modelflow/api/*.js（activate/verify/admin/*；共享库 unctions/_mf.js，含 SECRET/ALPHABET/种子码/自动建表）
- 管理后台页：public/modelflow/admin/index.html（首次设密码→登录→生成/列表/解绑/吊销/改密）
- D1 建表：migrations/0001_mflic.sql（Functions ensure() 会自动建表播种，此文件仅供手动初始化/文档）
- 主站下载按钮：src/pages/Dashboard.jsx → href=/modelflow/（已提交）

### 待用户外部操作（唯一卡点）：绑定 D1

本地无 Cloudflare 登录态/API Token，无法自动创建 D1。线上 API 未绑定前返回 503 友好提示（管理后台页会给出指引）。步骤：
1. Cloudflare 控制台 → Workers & Pages → voyra → **设置 → Functions → D1 数据库绑定**
2. 新建数据库（建议名 mflic）→ 以**变量名 DB** 绑定到 voyra
3. 刷新 https://lxlrwxs.top/modelflow/admin/ → 首次设置管理密码（≥6 位）→ 即可生成/管理授权码

### 软件端改动（0.7.6 已生效）

- `app/licensing.py`：SERVER 已改为 https://lxlrwxs.top/modelflow（激活走新 API）
- `app/updater.py`：改用 `/api/update-download` 换取预签名 URL 下载新版（0.7.6+）
- `app/version.py`：当前版本 0.7.6

---

## 第三版：安全加固（2026-09-01 · 已上线）

### 核心变更
1. **COS 桶改私有**：`modelflow-1447874637` 从公有读改为私有；`latest.json` / `index.html` 单独设公有读；exe 直链返回 403
2. **后端预签名下载**：verify 通过后，Functions 用 COS 密钥生成 5 分钟限时预签名 URL，前端直接触发浏览器下载
3. **软件更新器适配**：0.7.6+ 的 `updater.py` 调 `/api/update-download`（传 code+token）换取 10 分钟预签名 URL 下载新版
4. **旧版兼容接口**：`/api/legacy-download?code=XXXXX`（GET），0.7.5 及更早版本的 updater 拉 latest.json 拿到此地址，带 code 请求后 302 重定向到 5 分钟预签名 URL，requests 库自动跟随即可下载——**旧版软件内自动更新也能用了**
5. **防爆破速率限制**：D1 `rate_limit` 表，verify 10次/分、activate 5次/分、admin_login 5次/10分、update-download 5次/分、legacy_download 10次/分，超限分别封 5/10/60/10/5 分钟

### 线上地址（最终版）
| 用途 | 地址 |
|---|---|
| 下载页 | https://lxlrwxs.top/modelflow/ |
| 管理后台 | https://lxlrwxs.top/modelflow/admin/ |
| 激活 API | POST https://lxlrwxs.top/modelflow/api/activate |
| 下载校验 API（返回预签名 URL） | POST https://lxlrwxs.top/modelflow/api/verify |
| 更新下载 API（返回预签名 URL） | POST https://lxlrwxs.top/modelflow/api/update-download |
| 旧版兼容下载（302→预签名 URL） | GET https://lxlrwxs.top/modelflow/api/legacy-download?code=XXXXX |
| latest.json（公有读，url 字段=legacy-download） | https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/latest.json |
| exe 直链（私有，返回 403） | https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/ModelFlow-{ver}-setup.exe |

### Cloudflare 环境变量（Production，已配置 Encrypt）
- `COS_SECRET_ID`：腾讯云 SecretId（值同 cos_secrets.json）
- `COS_SECRET_KEY`：腾讯云 SecretKey（值同 cos_secrets.json）
- 修改变量后需重新部署（空 commit 或控制台 retry）才能生效

### COS 预签名算法要点（踩坑记录）
- **SignKey = HMAC-SHA1(SecretKey, sign_time)**——只用 sign_time，不是官方文档写的完整消息串。按 Python SDK 实际行为实现才能通过验证
- sign_time 开始时间 = 当前时间 - 60 秒（处理时钟偏移）
- GET 下载只签 host 头，不签查询参数（q-url-param-list 为空）
- 实现位置：`D:\Voyra 个人网站\functions\_mf.js` 的 `signCosUrl()`

### 发版流程（安全加固后）
1. 改代码 → `app/version.py` 升版本号
2. `python make_release.py --version X.Y.Z`（系统 Python312，约 10-15 分钟）
3. `python upload_cos.py`（上传 exe + 更新 latest.json + 自动只留最近两个版本）
4. 验证：下载页输授权码 → 浏览器下载成功 → 安装 → 激活 → 软件内检查更新
5. COS 桶保持私有；latest.json / index.html 保持公有读

### 过渡期注意
- 0.7.5 及更早版本的 updater 用旧逻辑（直接 GET latest.json 里的 url，带 ?code= 参数），现已通过 `/api/legacy-download` 兼容接口支持——**旧版软件内自动更新也能正常下载了**，无需手动重装
- latest.json 的 `url` 字段现在指向 `/api/legacy-download`（不是 COS 直链）；`direct_url` 字段存 COS 直链仅供参考（桶私有，直链 403）
- 0.7.6+ 的 updater 优先用 `/api/update-download`（传 code+token，验证机器绑定），失败时回退到 latest.json 的 url（legacy-download，只验证 code 不验证绑定）
- 下载页本身不受影响（始终走后端 verify + 预签名 URL）