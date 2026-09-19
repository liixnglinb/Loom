# -*- coding: utf-8 -*-
"""流程导出 / 导入这一对：导出的文件必须能原样导回来。

后端早有 export、前端一直没人接，接上之后最怕的是两边字段对不上 ——
导出带着库内字段（id/builtin/时间戳），导入端就会把它们当未知键丢掉，
看着能用，其实换一次机器就变了味。
"""
from conftest import db  # noqa: F401  (先装沙箱再 import app)


def _names(client):
    return {p["name"] for p in client.get("/api/pipelines").json()["pipelines"]}


def test_export_returns_only_interchange_fields(client):
    r = client.get("/api/pipelines/auto-workflow/export")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"name", "label", "desc", "emoji", "g", "steps"}, sorted(body)
    assert body["name"] == "auto-workflow"
    assert isinstance(body["steps"], list) and body["steps"]
    assert "id" not in body and "builtin" not in body and "created_at" not in body


def test_export_sets_a_download_filename(client):
    cd = client.get("/api/pipelines/auto-workflow/export").headers["content-disposition"]
    assert 'filename="loom-auto-workflow.json"' in cd, cd


def test_export_unknown_pipeline_is_404(client):
    assert client.get("/api/pipelines/no-such-flow/export").status_code == 404


def test_exported_file_imports_back_unchanged(client):
    src = client.get("/api/pipelines/auto-workflow/export").json()
    assert src["steps"], "源流程没有步骤，测不出什么"
    dst = dict(src, name="roundtrip-flow", label="回环测试")
    r = client.post("/api/pipelines", json=dst)
    assert r.status_code == 200, r.text
    assert "roundtrip-flow" in _names(client)
    back = client.get("/api/pipelines/roundtrip-flow/export").json()
    assert back["steps"] == src["steps"], "步骤在导出→导入之间被改了"
    assert back["label"] == "回环测试"


def test_import_onto_an_existing_name_is_rejected(client):
    """撞名要报错，前端靠这个返回决定「另存为 xxx-copy」的确认框。"""
    src = client.get("/api/pipelines/auto-workflow/export").json()
    r = client.post("/api/pipelines", json=src)
    assert r.status_code == 400
    assert "已存在" in r.json()["detail"]


def test_steps_survive_the_normalize_roundtrip(client):
    """步骤里没在 normalize_steps 白名单内的字段会被裁掉，
    裁掉之后不能再被当成"导出丢了东西"，所以这里只比白名单内的键。"""
    keep = {"key", "label", "skill", "out", "checkpoint", "role", "engine", "model", "extra_prompt"}
    src = client.get("/api/pipelines/auto-workflow/export").json()["steps"]
    assert all(set(s) <= keep for s in src), [sorted(set(s) - keep) for s in src]
