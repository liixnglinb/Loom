# -*- coding: utf-8 -*-
"""更新器：版本比较、清单解析、sha256 校验、装自身的边界。

清单在 COS 上，测试一律 monkeypatch 掉 requests.get —— 网络状态不该
决定测试结论。真正打外网那条链路用一次性脚本验。
"""
import hashlib

import pytest

from app import db, updater


@pytest.fixture(autouse=True)
def _clean_url():
    db.set_setting("update_url", "")
    updater._set(phase="idle", latest="", url="", notes="", asset="", sha256="",
                 size=0, got=0, path="", error="", checked_at="")
    yield
    db.set_setting("update_url", "")
    updater._set(phase="idle", latest="", url="", notes="", asset="", sha256="",
                 size=0, got=0, path="", error="", checked_at="")


class _JsonResp:
    status_code = 200

    def __init__(self, payload):
        self._p = payload

    def json(self):
        return self._p


class _StreamResp:
    status_code = 200

    def __init__(self, chunks):
        self._c = chunks

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=0):
        return iter(self._c)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.mark.parametrize("latest,local,newer", [
    ("v1.1.0", "1.0.0", True),
    ("1.0.1", "1.0.0", True),
    ("v1.0.0", "1.0.0", False),
    ("1.0.0", "1.0.1", False),
    ("v2.0", "1.9.9", True),
    ("", "1.0.0", False),
    # 已知取舍：按"抠数字"比较，非版本号的标签会被它的数字段支配。
    # release-7 -> (7,) 会赢过 (1,0,0)。发版请用版本号做 version，别指望这里兜住。
    ("release-7", "1.0.0", True),
    ("build.20240101", "1.0.0", True),
])
def test_version_compare(latest, local, newer):
    assert updater.is_newer(latest, local) is newer


def test_norm_tag_strips_the_leading_v(client):
    """清单里习惯写 v1.2.3，界面又自己加 v —— 不剥就显示成 vv1.2.3。
    但只该剥 v+数字，否则 vault-client 会被削成 ault-client。"""
    assert updater.norm_tag("v2.34.2") == "2.34.2"
    assert updater.norm_tag("V1.0") == "1.0"
    assert updater.norm_tag("1.0") == "1.0"
    assert updater.norm_tag("vault-client") == "vault-client"
    assert updater.norm_tag("v") == "v"
    assert updater.norm_tag("") == ""


def test_update_is_live_without_any_configuration(client):
    """换了 COS 直链之后没有"未配置"这个状态了：默认地址就是可用地址。
    胶囊该在软件一启动就开始检查，而不是等用户去填东西。"""
    s = client.get("/api/update").json()
    assert s["configured"] is True
    assert s["update_url"] == updater.DEFAULT_UPDATE_URL
    assert s["update_url"].endswith("/latest.json")


def test_check_parses_the_manifest(client, monkeypatch):
    def fake_get(url, **kw):
        assert url.endswith("/latest.json")
        return _JsonResp({"version": "9.9.9", "url": "https://x/Loom-9.9.9-setup.exe",
                          "file": "Loom-9.9.9-setup.exe", "sha256": "ab" * 32,
                          "size": 1234, "notes": "测试说明"})
    monkeypatch.setattr(updater.requests, "get", fake_get)
    d = client.post("/api/update/check").json()
    assert d["phase"] == "available"
    assert d["latest"] == "9.9.9" and d["asset"] == "Loom-9.9.9-setup.exe"
    assert d["size"] == 1234 and d["sha256"] == "ab" * 32
    assert d["url"] == "https://x/Loom-9.9.9-setup.exe"


def test_check_current_when_manifest_matches_local(client, monkeypatch):
    monkeypatch.setattr(updater.requests, "get", lambda url, **kw: _JsonResp(
        {"version": updater.APP_VERSION, "url": "https://x/a.exe"}))
    d = client.post("/api/update/check").json()
    assert d["phase"] == "current"
    assert d["url"] == "", "已是最新就不该留一个可下载地址"


def test_check_rejects_non_https_package_url(client, monkeypatch):
    monkeypatch.setattr(updater.requests, "get", lambda url, **kw: _JsonResp(
        {"version": "9.9.9", "url": "http://x/a.exe"}))
    d = client.post("/api/update/check").json()
    assert d["phase"] == "error" and "https" in d["error"]


def test_check_survives_http_error_and_garbage(client, monkeypatch):
    class _Bad:
        status_code = 403

        def json(self):
            raise ValueError("not json")
    monkeypatch.setattr(updater.requests, "get", lambda url, **kw: _Bad())
    d = client.post("/api/update/check").json()
    assert d["phase"] == "error" and "403" in d["error"]

    monkeypatch.setattr(updater.requests, "get", lambda url, **kw: _JsonResp({}))
    d2 = client.post("/api/update/check").json()
    assert d2["phase"] == "error" and "version" in d2["error"]


def test_check_does_not_clobber_an_in_flight_download(client, monkeypatch):
    """下载飞行中做一次强制检查，会把 got 清 0、把正在写的包路径抹掉：
    进度条当场跳回原点，后台线程还在往原路径写 —— 状态被踩了一脚。"""
    dest = "updates/Loom-9.9.9-setup.exe.part"
    updater._set(phase="downloading", url="https://x/Loom-9.9.9-setup.exe",
                 asset="pkg.exe", latest="9.9.9", size=42, path=dest, got=17, error="")

    def _boom(*a, **k):
        raise AssertionError("下载中不该再去打网络")

    monkeypatch.setattr(updater.requests, "get", _boom)
    d = updater.check(force=True)
    assert d["phase"] == "downloading" and d["got"] == 17, "下载状态被强制检查覆盖了"
    assert d["path"] == dest


def test_manifest_url_must_be_https_or_empty(client):
    for bad in ("http://x/latest.json", "ftp://x", "not a url"):
        assert client.post("/api/update/url", json={"url": bad}).status_code == 400, bad
    assert client.post("/api/update/url", json={"url": ""}).status_code == 200
    assert db.get_setting("update_url") == ""
    assert client.get("/api/update").json()["update_url"] == updater.DEFAULT_UPDATE_URL


def test_download_accepts_a_matching_sha256(client, tmp_path):
    blob = b"Loom installer bytes" * 7
    dest = tmp_path / "Loom-x-setup.exe"
    updater._set(phase="downloading", got=0, error="", path=str(dest))
    orig = updater.requests.get
    updater.requests.get = lambda url, **kw: _StreamResp([blob])
    try:
        updater._download("https://x/a.exe", dest, len(blob), hashlib.sha256(blob).hexdigest())
    finally:
        updater.requests.get = orig
    assert updater.STATE["phase"] == "ready"
    assert updater.STATE["got"] == len(blob)


def test_download_rejects_a_tampered_file(client, tmp_path):
    """sha 不匹配必须删掉落盘文件并报 error —— 半截安装包最坏的地方是"看起来成功了"。"""
    blob = b"Loom installer bytes" * 7
    dest = tmp_path / "Loom-x-setup.exe"
    updater._set(phase="downloading", got=0, error="", path=str(dest))
    orig = updater.requests.get
    updater.requests.get = lambda url, **kw: _StreamResp([blob])
    try:
        updater._download("https://x/a.exe", dest, len(blob), "0" * 64)
    finally:
        updater.requests.get = orig
    assert updater.STATE["phase"] == "error"
    assert "sha256" in updater.STATE["error"]
    assert not dest.exists(), "校验失败的包留在盘上，下次会被误当可用更新"


def test_download_still_checks_byte_count(client, tmp_path):
    blob = b"abc" * 100
    dest = tmp_path / "p.exe"
    updater._set(phase="downloading", got=0, error="", path=str(dest))
    orig = updater.requests.get
    updater.requests.get = lambda url, **kw: _StreamResp([blob])
    try:
        updater._download("https://x/a.exe", dest, len(blob) + 5, "")
    finally:
        updater.requests.get = orig
    assert updater.STATE["phase"] == "error" and "字节数" in updater.STATE["error"]


def test_apply_refuses_outside_a_packaged_build(client):
    """源码运行没有可替换的 exe —— 必须明说，不能演一遍"正在安装"。"""
    r = client.post("/api/update/apply")
    assert r.status_code == 400
    assert "源码" in r.json()["detail"]


def test_apply_refuses_while_runs_are_active(client, dbsession):
    rid = "run-updateseed01"
    dbsession.create_run(rid, "auto-workflow", steps=[{"key": "a", "status": "running"}])
    conn = db.get_conn()
    conn.execute("UPDATE runs SET status='running' WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    r = client.post("/api/update/apply")
    assert r.status_code == 409
    assert "任务" in r.json()["detail"]
    dbsession.delete_run(rid)


_GOOD_MANIFEST = {"version": "9.9.9", "url": "https://x/Loom-9.9.9-setup.exe",
                  "file": "Loom-9.9.9-setup.exe", "sha256": "ab" * 32, "size": 1234}


@pytest.mark.parametrize("drop,patch,why", [
    ("sha256", {}, "清单不给 sha256"),
    ("size", {}, "清单不给大小"),
    (None, {"sha256": "zz" * 32}, "sha256 不是十六进制"),
    (None, {"file": r"..\..\Startup.exe"}, "文件名带相对路径"),
    (None, {"file": "totally-other.exe"}, "文件名与下载地址末段不符"),
])
def test_check_refuses_a_manifest_that_cannot_be_verified(client, monkeypatch,
                                                          drop, patch, why):
    """清单地址是用户可改的（update_set_url 只拦协议、不锁域名），而 sha256 与 file
    出自同一份清单。以前两个校验都是"有才校"，一份不写 sha256 的清单就能把任意 exe
    标成 ready；file 里塞 `..` 还能把包写到启动目录去。"""
    m = dict(_GOOD_MANIFEST)
    if drop:
        m.pop(drop)
    m.update(patch)
    monkeypatch.setattr(updater.requests, "get", lambda url, **kw: _JsonResp(m))
    d = client.post("/api/update/check").json()
    assert d["phase"] == "error", f"{why}：竟然进了 {d['phase']}，asset={d.get('asset')!r}"
    assert "拒绝" in (d["error"] or "")


def test_apply_rehashes_the_package_before_running_it(monkeypatch, tmp_path):
    """ready 只是内存里的一个标志：从校验通过到点安装之间可以隔任意久，
    期间文件被截断/被换掉、或是上次异常退出留下的同名残包，光判 is_file() 发现不了。"""
    exe = tmp_path / "Loom-9.9.9-setup.exe"
    exe.write_bytes(b"genuine installer bytes")
    updater._set(phase="ready", path=str(exe), frozen=True, size=23, got=23,
                 asset=exe.name, url="https://x/" + exe.name,
                 sha256="0" * 64, error="", latest="9.9.9")
    started = []
    monkeypatch.setattr(updater.subprocess, "Popen", lambda *a, **k: started.append(a))
    try:
        r = updater.apply_update()
        assert r["ok"] is False, "校验值对不上却照样装了"
        assert started == [], "校验没过就已经把安装器起起来了"
        assert not exe.exists(), "校验失败的残包必须删掉，别留在那儿等人再点一次"
    finally:
        updater._set(phase="idle", path="", frozen=False, sha256="", size=0, got=0,
                     asset="", url="", latest="", error="")


def test_apply_still_runs_when_the_hash_matches(monkeypatch, tmp_path):
    exe = tmp_path / "Loom-9.9.9-setup.exe"
    exe.write_bytes(b"genuine installer bytes")
    good = hashlib.sha256(exe.read_bytes()).hexdigest()
    updater._set(phase="ready", path=str(exe), frozen=True, size=23, got=23,
                 asset=exe.name, url="https://x/" + exe.name,
                 sha256=good, error="", latest="9.9.9")
    started = []
    monkeypatch.setattr(updater.subprocess, "Popen", lambda *a, **k: started.append(a))
    monkeypatch.setattr(updater.threading, "Timer",
                        lambda *a, **k: type("T", (), {"start": lambda s: None})())
    try:
        r = updater.apply_update()
        assert r["ok"] is True, r
        assert len(started) == 1, "校验过了却没把安装器起起来"
    finally:
        updater._set(phase="idle", path="", frozen=False, sha256="", size=0, got=0,
                     asset="", url="", latest="", error="")
