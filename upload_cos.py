# -*- coding: utf-8 -*-
"""把 release/ 产物上传到腾讯云 COS（替代 upload_release.py 的 SSH/VPS 通道）。

形态：COS 纯静态托管 + 前端授权门禁（授权码 SHA-256 嵌入下载页，零后端）。
  ModelFlow-{v}-setup.exe  -> <bucket>/ModelFlow-{v}-setup.exe   （公有读，用户下载）
  latest.json               -> <bucket>/latest.json               （自动更新清单，url 指向 exe）
  index.html                -> <bucket>/index.html                （下载页，内嵌授权码哈希）

用法：
  1) 复制 cos_secrets.example.json 为 cos_secrets.json 并填入你的真实信息：
       secret_id    腾讯云 SecretId（建议用仅授权该桶的子账号）
       secret_key    腾讯云 SecretKey
       bucket       桶全名（含 -APPID，例如 modelflow-release-1447874637）
       region       地域，例如 ap-guangzhou
       license_codes  5 位授权码列表（前端门禁只放哈希，不放明文）
  2) 先跑 make_release.py 打包，再跑本脚本：
       python upload_cos.py
  依赖：pip install cos-python-sdk-v5
"""
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REL = BASE / "release"
CONFIG = BASE / "cos_secrets.json"

try:
    from qcloud_cos import CosConfig, CosS3Client
except ImportError:
    sys.exit("缺少 cos-python-sdk-v5，请先：pip install cos-python-sdk-v5")


def _cfg():
    if not CONFIG.exists():
        sys.exit(f"未找到 {CONFIG.name}，请先复制 cos_secrets.example.json 并填入真实信息")
    c = json.loads(CONFIG.read_text(encoding="utf-8"))
    for k in ("secret_id", "secret_key", "bucket", "region"):
        if not str(c.get(k) or "").strip():
            sys.exit(f"cos_secrets.json 缺少字段：{k}")
    return c


def _sha_hex(s: str) -> str:
    return hashlib.sha256(s.strip().upper().encode("utf-8")).hexdigest()


def _build_index(ver: str, sha: str, exe_name: str, exe_url: str, codes: list) -> str:
    """生成 COS 静态下载页（前端门禁版）。授权码只内嵌 SHA-256，不含明文。"""
    code_hashes = json.dumps([_sha_hex(c) for c in codes if str(c).strip()],
                             ensure_ascii=True)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ModelFlow 智模流水线 · 下载</title>
<style>
  :root{{--bg:#0b0d12;--panel:#12151d;--line:#232836;--txt:#e8eaf0;--muted:#8b92a5;
    --accent:#4f7cff;--accent2:#7c5cff;--ok:#2fbf71;}}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:"MiSans","HarmonyOS Sans SC","PingFang SC","Microsoft YaHei UI","Segoe UI",system-ui,sans-serif;
    background:var(--bg);color:var(--txt);min-height:100vh;
    background-image:radial-gradient(ellipse 60% 40% at 50% -10%, rgba(79,124,255,.18), transparent);}}
  .wrap{{max-width:880px;margin:0 auto;padding:64px 24px 80px}}
  .badge{{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:999px;
    padding:6px 14px;font-size:13px;color:var(--muted);margin-bottom:20px}}
  .badge .dot{{width:8px;height:8px;border-radius:50%;background:var(--ok)}}
  h1{{font-size:40px;line-height:1.2;letter-spacing:-.5px;margin-bottom:12px}}
  h1 .grad{{background:linear-gradient(90deg,var(--accent),var(--accent2));-webkit-background-clip:text;
    background-clip:text;color:transparent}}
  .sub{{color:var(--muted);font-size:16px;margin-bottom:40px;line-height:1.7}}
  .meta{{display:flex;gap:20px;flex-wrap:wrap;color:var(--muted);font-size:13px;margin-bottom:32px}}
  .meta b{{color:var(--txt);font-weight:600}}
  .gate{{display:flex;gap:12px;align-items:center;background:var(--panel);border:1px solid var(--line);
    border-radius:14px;padding:18px 20px;margin:0 auto 28px;flex-wrap:wrap}}
  .gate-label{{font-size:15px;font-weight:700}}
  .gate input{{flex:0 0 190px;text-align:center;font-family:Consolas,monospace;font-size:17px;letter-spacing:8px;
    text-transform:uppercase;padding:11px;border:1px solid #3a4258;border-radius:10px;background:#0b0d12;color:var(--txt)}}
  .gate button{{border:0;background:linear-gradient(90deg,var(--accent),var(--accent2));color:#fff;border-radius:10px;
    padding:12px 24px;font-weight:700;cursor:pointer;font-size:15px}}
  .gate button:hover{{filter:brightness(1.1)}}
  .gate .err{{font-size:12.5px;color:#ff6b6b;width:100%}}
  .btn{{display:block;text-align:center;border-radius:12px;padding:16px 22px;font-size:16px;font-weight:700;
    text-decoration:none;transition:transform .15s, box-shadow .15s}}
  .btn-primary{{background:linear-gradient(90deg,var(--accent),var(--accent2));color:#fff;
    box-shadow:0 4px 20px rgba(79,124,255,.35)}}
  .btn-primary:hover{{transform:translateY(-1px)}}
  .btn:disabled{{opacity:.45;cursor:not-allowed;box-shadow:none}}
  .steps{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:28px;margin-bottom:28px}}
  .steps h3{{font-size:15px;margin-bottom:18px}}
  .step-line{{display:flex;gap:14px;align-items:flex-start;padding-bottom:18px}}
  .step-line:last-child{{padding-bottom:0}}
  .num{{width:27px;height:27px;border-radius:50%;background:rgba(79,124,255,.15);border:1px solid var(--accent);
    color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0}}
  .step-line .t{{font-size:14px;font-weight:600;margin-bottom:3px}}
  .step-line .d{{font-size:13px;color:var(--muted);line-height:1.6}}
  .foot{{color:#5b6274;font-size:12px;line-height:1.8;border-top:1px solid var(--line);padding-top:20px}}
  .foot code{{background:#1a1e29;border:1px solid var(--line);border-radius:4px;padding:1px 6px;font-size:11px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="badge"><span class="dot"></span>已发布最新版本 <b id="ver">{ver}</b></div>
  <h1>ModelFlow <span class="grad">智模流水线</span></h1>
  <p class="sub">数学建模竞赛全自动流水线 —— 从赛题解析到论文 PDF，一条龙。</p>

  <div class="meta">
    <span>版本 <b id="ver2">{ver}</b></span>
    <span>系统 <b>Windows 10/11 x64</b></span>
    <span>SHA-256 <b id="sha">{sha[:8]}…</b></span>
  </div>

  <div class="gate" id="gateBox">
    <span class="gate-label">🔑 输入 5 位授权码解锁下载</span>
    <input id="lic" maxlength="5" placeholder="如：K7X2M" autocomplete="off">
    <button onclick="unlock()">验证</button>
    <span class="err" id="gerr"></span>
  </div>

  <a class="btn btn-primary" id="dl" disabled>下载安装版</a>

  <div class="steps" style="margin-top:28px">
    <h3>三步上手</h3>
    <div class="step-line"><span class="num">1</span><div><div class="t">下载并运行安装包</div><div class="d">双击 {exe_name}，无需管理员权限。</div></div></div>
    <div class="step-line"><span class="num">2</span><div><div class="t">点下一步装完</div><div class="d">默认装到你的用户目录，可勾选创建桌面快捷方式。</div></div></div>
    <div class="step-line"><span class="num">3</span><div><div class="t">启动后激活</div><div class="d">首次启动输入授权码激活，即可使用。</div></div></div>
  </div>

  <div class="foot">
    <p>安装包的 SHA-256 校验值见上方，下载后可用 <code>certutil -hashfile 文件名 SHA256</code> 对比。</p>
    <p style="margin-top:6px">已有旧版本？在软件内 <b>设置 → 在线更新</b> 一键升级即可。</p>
  </div>
</div>
<script>
  const CODES = {code_hashes};
  const FILE_URL = "{exe_url}";
  const saved = (()=>{{try{{return localStorage.getItem("mf_lic")||""}}catch(e){{return ""}}}})();
  async function shaHex(s){{
    const u = new TextEncoder().encode(s.trim().toUpperCase());
    const b = await crypto.subtle.digest("SHA-256", u);
    return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,"0")).join("");
  }}
  function unlockBtn(){{
    const a=document.getElementById("dl");
    a.href = FILE_URL; a.disabled=false; a.textContent="下载安装版";
    document.getElementById("gateBox").style.display="none";
  }}
  async function unlock(){{
    const code=document.getElementById("lic").value||"";
    const err=document.getElementById("gerr");
    if(code.trim().length!==5){{err.textContent="请输入 5 位授权码";return;}}
    const h=await shaHex(code);
    if(CODES.includes(h)){{localStorage.setItem("mf_lic",code);err.textContent="";unlockBtn();}}
    else{{err.textContent="授权码无效";}}
  }}
  document.getElementById("lic").addEventListener("keydown",e=>{{if(e.key==="Enter")unlock();}});
  if(saved && saved.trim().length===5){{shaHex(saved).then(h=>{{if(CODES.includes(h))unlockBtn();}});}}
</script>
</body>
</html>"""


def main():
    c = _cfg()
    secret_id = c["secret_id"].strip()
    secret_key = c["secret_key"].strip()
    bucket = c["bucket"].strip()
    region = c["region"].strip()
    codes = [str(x).strip() for x in (c.get("license_codes") or []) if str(x).strip()]

    latest_path = REL / "latest.json"
    if not latest_path.exists():
        sys.exit("release/latest.json 不存在，请先跑 make_release.py")
    mf = json.loads(latest_path.read_text(encoding="utf-8"))
    ver = mf["version"]
    sha = mf.get("sha256", "")
    notes = mf.get("notes", "ModelFlow " + ver)
    exe_name = f"ModelFlow-{ver}-setup.exe"
    exe_path = REL / exe_name
    if not exe_path.exists():
        sys.exit(f"release/{exe_name} 不存在")

    base_url = c.get("base_url") or f"https://{bucket}.cos.{region}.myqcloud.com"
    base_url = base_url.rstrip("/")
    exe_url = f"{base_url}/{exe_name}"

    cfg = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(cfg)

    # 1) exe（继承桶私有；直链 403，须通过后端预签名 URL 下载）
    print(f"↑ {exe_name} ({exe_path.stat().st_size/1048576:.1f} MB) …")
    client.upload_file(Bucket=bucket, Key=exe_name, LocalFilePath=str(exe_path))
    print(f"  ok -> {exe_url}")

    # 2) latest.json（url 指向 legacy-download 兼容接口：旧版 0.7.5 更新器带 ?code=
    #    请求此地址，后端验证后 302 重定向到限时预签名 URL；direct_url 存 COS 直链仅供参考）
    legacy_url = "https://lxlrwxs.top/modelflow/api/legacy-download"
    mf2 = {"version": ver, "url": legacy_url, "direct_url": exe_url,
           "sha256": sha, "notes": notes}
    lj = json.dumps(mf2, ensure_ascii=False, indent=2)
    client.put_object(Bucket=bucket, Key="latest.json",
                      Body=lj.encode("utf-8"), ContentType="application/json",
                      ACL="public-read")
    print(f"↑ latest.json -> {base_url}/latest.json")

    # 3) index.html（前端门禁版，内嵌授权码哈希）
    page = _build_index(ver, sha, exe_name, exe_url, codes)
    client.put_object(Bucket=bucket, Key="index.html",
                      Body=page.encode("utf-8"), ContentType="text/html; charset=utf-8",
                      ACL="public-read")
    print(f"↑ index.html -> {base_url}/index.html")

    # 4) 清理旧版本：COS 只留最近两个版本的安装包（latest.json / index.html 不动）
    import re
    resp = client.list_objects(Bucket=bucket)
    exes = []
    for item in resp.get("Contents", []):
        key = item["Key"]
        m = re.match(r"ModelFlow-(\d+\.\d+\.\d+)-setup\.exe$", key)
        if m:
            exes.append((tuple(int(x) for x in m.group(1).split(".")), key))
    exes.sort(reverse=True)
    if len(exes) > 2:
        for _, key in exes[2:]:
            print(f"× 删除旧版本 {key}")
            client.delete_object(Bucket=bucket, Key=key)
    kept = ", ".join(k for _, k in exes[:2])
    print(f"  保留版本：{kept}")

    print("\n完成。验证：")
    print(f"  下载页   {base_url}/index.html")
    print(f"  更新清单 {base_url}/latest.json")


if __name__ == "__main__":
    main()
