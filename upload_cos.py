# -*- coding: utf-8 -*-
"""把 release/ 的安装包与 latest.json 传到腾讯云 COS，并设成公有读。

密钥不复制进本仓库：默认读同级开发目录里那份 cos_secrets.json，
也可以用环境变量 LOOM_COS_SECRETS 指定路径，或在仓库根放一个
同名文件（.gitignore 已拦）。

桶本身仍是私有桶，只有这两个对象开公有读：
  Loom-{v}-setup.exe   下载页直链 + 软件内更新器
  latest.json          版本清单（更新器与页面都读它）
旧版本保留最近两个，和 make_release.py 的本地策略一致。
"""
import json
import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REL = BASE / "release"
CANDIDATES = [
    os.environ.get("LOOM_COS_SECRETS"),
    str(BASE / "cos_secrets.json"),
    str(Path(r"C:/Users/李星历/Desktop/数学建模工作流软件/cos_secrets.json")),
]


def load_secrets() -> dict:
    for p in CANDIDATES:
        if p and Path(p).is_file():
            s = json.loads(Path(p).read_text(encoding="utf-8"))
            if s.get("secret_id") and s.get("secret_key"):
                print(f"[cos] 使用密钥文件 {p}")
                return s
    sys.exit("找不到 COS 密钥（设 LOOM_COS_SECRETS 或放一份 cos_secrets.json）")


def main() -> int:
    try:
        from qcloud_cos import CosConfig, CosS3Client
    except ImportError:
        sys.exit("缺少 qcloud_cos SDK：pip install qcloud_cos")

    s = load_secrets()
    bucket = s.get("bucket") or "modelflow-1447874637"
    region = s.get("region") or "ap-guangzhou"
    client = CosS3Client(CosConfig(Region=region, SecretId=s["secret_id"],
                                   SecretKey=s["secret_key"]))

    manifest = json.loads((REL / "latest.json").read_text(encoding="utf-8"))
    exe = REL / manifest["file"]
    if not exe.is_file():
        sys.exit(f"缺少 {exe.name}，先跑 make_release.py")

    print(f"↑ {manifest['file']} ({exe.stat().st_size/1048576:.1f} MB)")
    client.upload_file(Bucket=bucket, Key=manifest["file"], LocalFilePath=str(exe),
                       ACL="public-read")
    body = json.dumps(manifest, ensure_ascii=False)
    client.put_object(Bucket=bucket, Key="latest.json", Body=body.encode("utf-8"),
                      ACL="public-read", ContentType="application/json")
    print(f"↑ latest.json  version={manifest['version']}")

    # 下载页在 lxlrwxs.top，读 COS 上的 latest.json 属于跨域。没配 CORS 时
    # fetch 会静默失败，页面就一直显示写死的旧版本号 —— 看着正常，其实说谎。
    try:
        from qcloud_cos import CosSchema
        cors = {"CORSRules": [{"AllowedOrigin": ["https://lxlrwxs.top", "https://*.lxlrwxs.top"],
                               "AllowedMethod": ["GET", "HEAD"],
                               "AllowedHeader": ["*"],
                               "ExposeHeader": ["ETag", "Content-Length"],
                               "MaxAgeSeconds": 86400}]}
        client.put_bucket_cors(Bucket=bucket, CORSConfiguration=cors)
        print("[cos] CORS 已设：lxlrwxs.top 可跨域读 latest.json")
    except Exception as e:
        print(f"[cos] ⚠ CORS 设置失败（下载页版本号会退回写死值）：{e}")

    # 匿名回读：签名请求成功不代表公网能下，这一步才是用户看到的真相
    import requests
    base = f"https://{bucket}.cos.{region}.myqcloud.com"
    got = requests.get(f"{base}/latest.json", timeout=20)
    got.raise_for_status()
    print("[cos] 匿名读 latest.json ->", got.json().get("version"))
    head = requests.head(manifest["url"], timeout=20)
    print(f"[cos] 匿名 HEAD 安装包 -> HTTP {head.status_code} "
          f"{int(head.headers.get('content-length') or 0)/1048576:.1f} MB")
    print("[cos] 跨域预检 ->", requests.options(
        f"{base}/latest.json",
        headers={"Origin": "https://lxlrwxs.top",
                 "Access-Control-Request-Method": "GET"}, timeout=20).status_code)

    # 桶刚被清空过（2026-09-15 实测 0 对象），这里只列清单不自动删任何东西：
    # 攒够两个版本后再谈保留策略，删线上包必须是显式动作。
    listed = client.list_objects(Bucket=bucket, Prefix="Loom-", MaxKeys=200).get("Contents", [])
    print(f"[cos] 桶内 Loom 安装包 {len(listed)} 个：")
    for o in listed:
        print(f"      {o['Key']}  {int(o['Size'])/1048576:.1f} MB")
    print(f"\n下载直链：{manifest['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
