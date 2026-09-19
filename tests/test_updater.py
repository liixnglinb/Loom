# -*- coding: utf-8 -*-
"""更新器：版本比较、仓库校验、未配置时的行为。

真打 GitHub 的那条链路（check/download）用一次性脚本验过；这里只钉住
不需要网络的纯逻辑，避免测试依赖外网。
"""
import pytest

from app import db, updater


@pytest.fixture(autouse=True)
def _clean_repo():
    db.set_setting("update_repo", "")
    db.set_setting("update_asset", "")
    yield
    db.set_setting("update_repo", "")
    db.set_setting("update_asset", "")


@pytest.mark.parametrize("latest,local,newer", [
    ("v1.1.0", "1.0.0", True),
    ("1.0.1", "1.0.0", True),
    ("v1.0.0", "1.0.0", False),
    ("1.0.0", "1.0.1", False),
    ("v2.0", "1.9.9", True),
    ("", "1.0.0", False),
    # 已知取舍：标签按"抠数字"比较，所以非版本号的标签会被它的数字段支配。
    # release-7 -> (7,) 会赢过 (1,0,0)。发版请用版本号做 tag，别指望这里兜住。
    ("release-7", "1.0.0", True),
    ("build.20240101", "1.0.0", True),
])
def test_version_compare(latest, local, newer):
    assert updater.is_newer(latest, local) is newer


def test_stats_do_not_report_live_workspaces_as_orphans(client, dbsession, workspaces, fresh_runs):
    """误报孤儿 = 递刀让人删掉活跃工作区。目录名就是 run id，不能再剥前缀。

    只断言自己那个目录：别的用例留下的工作区在清表后确实是真孤儿，
    不该由本用例负责沙箱整洁。
    """
    rid = "run-orphancheck01"
    dbsession.create_run(rid, "some-flow", steps=[{"key": "a"}])
    ws = workspaces / rid
    (ws / "_turn_logs").mkdir(parents=True)
    (ws / "out.md").write_text("x" * 50, encoding="utf-8")
    s = client.get("/api/stats").json()
    names = [o["name"] for o in s["orphans"]]
    assert rid not in names, f"活跃工作区被误判成孤儿：{names}"
    assert s["workspace_bytes"] >= 50
    # 记录一删，就该认得出来
    dbsession.delete_run(rid)
    s2 = client.get("/api/stats").json()
    assert rid in [o["name"] for o in s2["orphans"]]
    import shutil; shutil.rmtree(ws, ignore_errors=True)


def test_norm_tag_strips_the_leading_v(client):
    """GitHub 标签习惯写 v1.2.3，界面又自己加 v —— 不剥就显示成 vv1.2.3。
    但只该剥 v+数字，否则 vault-client 会被削成 ault-client。"""
    assert updater.norm_tag("v2.34.2") == "2.34.2"
    assert updater.norm_tag("V1.0") == "1.0"
    assert updater.norm_tag("1.0") == "1.0"
    assert updater.norm_tag("vault-client") == "vault-client"
    assert updater.norm_tag("v") == "v"
    assert updater.norm_tag("") == ""


def test_unconfigured_is_explicit_idle(client):
    """没配仓库时必须是清楚的 idle/configured=False，不能报错误导用户。"""
    s = updater.snapshot()
    assert s["phase"] == "idle" and s["configured"] is False and s["url"] == ""
    d = client.get("/api/update").json()
    assert d["configured"] is False
    assert d["active_runs"] == 0


def test_download_without_url_does_not_start_thread(client):
    r = client.post("/api/update/download").json()
    assert r["phase"] == "error" and r["got"] == 0


def test_repo_shape_validated(client):
    for bad in ("just-a-name", "a/b/c", "owner/", "/repo", "http://x/y"):
        assert client.post("/api/update/repo", json={"repo": bad}).status_code == 400, bad
    assert client.post("/api/update/repo", json={"repo": "psf/requests"}).status_code == 200
    assert db.get_setting("update_repo") == "psf/requests"
    assert client.post("/api/update/repo", json={"repo": ""}).status_code == 200
    assert db.get_setting("update_repo") == ""


def test_check_against_bad_repo_reports_error_not_crash(client):
    """仓库不存在 / 无发布：必须是 error + 人话，不能 500。"""
    db.set_setting("update_repo", "this-owner-really-does-not-exist/zzz-nope")
    d = client.post("/api/update/check").json()
    assert d["phase"] == "error"
    assert d["error"]
