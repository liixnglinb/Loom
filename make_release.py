# -*- coding: utf-8 -*-
"""ModelFlow 发布辅助（2026-08-28 安装包单形态版）：版本号 → 打包 → 计算摘要 → 生成清单。

形态（便携版已停售，仅安装包）：
  安装版  release/ModelFlow-{v}-setup.exe    ← PyInstaller onedir + Inno Setup
  清单    release/latest.json                ← {version,url,sha256,notes}

用法：
  python make_release.py --version 0.5.4 --notes "..."    # 全量（onedir + Inno + 清单）
  python make_release.py --skip-build                     # 只重新生成清单
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
REL = BASE / "release"
URL_BASE = "https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com"


def _find_iscc() -> Path:
    """定位 Inno Setup 编译器（不写死用户名，按环境推导）。"""
    p = shutil.which("ISCC")
    if p:
        return Path(p)
    cands = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        cands.append(Path(local) / "Programs" / "Inno Setup 6" / "ISCC.exe")
    pf = os.environ.get("ProgramFiles(x86)")
    if pf:
        cands.append(Path(pf) / "Inno Setup 6" / "ISCC.exe")
    for c in cands:
        try:
            if c.exists():
                return c
        except OSError:
            continue
    return Path("")


ISCC = _find_iscc()


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_onedir():
    """onedir 装机版目录树（给 Inno 用）。"""
    shutil.rmtree(BASE / "dist_app", ignore_errors=True)
    r = subprocess.run([sys.executable, "-m", "PyInstaller", "ModelFlow-dir.spec",
                        "--noconfirm", "--distpath", "dist_app"], cwd=str(BASE))
    if r.returncode != 0:
        sys.exit("PyInstaller（装机版）失败")
    exe = BASE / "dist_app" / "ModelFlow" / "ModelFlow.exe"
    if not exe.exists():
        sys.exit("找不到 dist_app/ModelFlow/ModelFlow.exe")
    stray = exe.parent / "data"
    if stray.exists():
        sys.exit("dist_app/ModelFlow/data 不应存在（会把测试数据打进安装包），请检查")
    return exe


def build_setup(version: str) -> Path:
    """Inno Setup 编译安装包。"""
    if not ISCC.exists():
        sys.exit(f"找不到 ISCC：{ISCC}（winget install JRSoftware.InnoSetup）")
    r = subprocess.run(
        [str(ISCC), "/DMyAppVersion=" + version, "installer.iss"], cwd=str(BASE))
    if r.returncode != 0:
        sys.exit("Inno Setup 编译失败")
    out = REL / f"ModelFlow-{version}-setup.exe"
    if not out.exists():
        sys.exit(f"未生成 {out.name}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", help="覆盖版本号（同时写回 app/version.py）")
    ap.add_argument("--notes", default="", help="更新说明（写入清单）")
    ap.add_argument("--skip-build", action="store_true", help="跳过打包，只重建清单")
    a = ap.parse_args()

    vp = BASE / "app" / "version.py"
    if a.version:
        vp.write_text(f'# -*- coding: utf-8 -*-\n"""ModelFlow 版本号（发版时由 make_release.py 或手动修改）。"""\nAPP_VERSION = "{a.version}"\n', encoding="utf-8")
    ns: dict = {}
    exec(vp.read_text(encoding="utf-8"), ns)
    ver = ns["APP_VERSION"]
    print(f"[release] version = {ver}")

    REL.mkdir(exist_ok=True)

    if not a.skip_build:
        build_onedir()
        setup = build_setup(ver)
    else:
        setup = REL / f"ModelFlow-{ver}-setup.exe"
        if not setup.exists():
            sys.exit(f"未找到 {setup.name}（--skip-build 需已有产物）")

    setup_sha = sha256_of(setup)
    print(f"[release] 安装版 = {setup.name}  ({setup.stat().st_size/1048576:.1f} MB)")
    print(f"[release]   sha256 = {setup_sha}")

    notes = a.notes or f"ModelFlow {ver}"
    (REL / "latest.json").write_text(
        json.dumps({"version": ver, "url": f"{URL_BASE}/ModelFlow-{ver}-setup.exe",
                    "sha256": setup_sha, "notes": notes},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[release] latest.json:\n{(REL/'latest.json').read_text(encoding='utf-8')}")

    # 本地保留规则：安装包只留最新两个（与服务器 files/ 清理策略一致）
    setups = sorted(REL.glob("ModelFlow-*-setup.exe"),
                    key=lambda f: [int(x) for x in
                                   re.findall(r"(\d+)", f.stem.split("-setup")[0])])
    for old in setups[:-2]:
        old.unlink()
        print(f"[release] 清理旧安装包 {old.name}（本地只留最新两个）")

    print("""
下一步：  python upload_cos.py    （上传 setup.exe + latest.json 到腾讯云 COS，并生成授权码门禁下载页）
          下载页 https://lxlrwxs.top/modelflow/  管理后台 /modelflow/admin/
验证：    curl https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com/latest.json
""")


if __name__ == "__main__":
    main()
