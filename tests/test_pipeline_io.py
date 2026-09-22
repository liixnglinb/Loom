# -*- coding: utf-8 -*-
"""流程导出 / 导入这一对：导出的文件必须能原样导回来。

后端早有 export、前端一直没人接，接上之后最怕的是两边字段对不上 ——
导出带着库内字段（id/builtin/时间戳），导入端就会把它们当未知键丢掉，
看着能用，其实换一次机器就变了味。

以前这几条直接借出厂模板 auto-workflow 当素材；软件不再带默认内容了，
所以素材由本文件自己造一条，测的还是同一件事。
"""
import pytest

from conftest import db  # noqa: F401  (先装沙箱再 import app)

FLOW = "io-fixture-flow"
STEPS = [
    {"key": "clarify", "label": "需求解析", "skill": "sk-a", "skill_src": "",
     "out": "REQUIREMENTS.md", "checkpoint": True, "role": "executor",
     "engine": "", "model": "", "extra_prompt": ""},
    {"key": "execute", "label": "逐项执行", "skill": "sk-b", "skill_src": "claude",
     "out": "EXECUTION.md", "checkpoint": False, "role": "executor", "engine": "claude",
     "model": "m1", "extra_prompt": "只写要点"},
]


@pytest.fixture(scope="module", autouse=True)
def fixture_flow():
    db.create_pipeline(FLOW, label="回环素材", desc="导出/导入用的假流程",
                       g="custom", steps=STEPS)
    yield FLOW
    db.delete_pipeline(FLOW)


def _names(client):
    return {p["name"] for p in client.get("/api/pipelines").json()["pipelines"]}


def test_export_returns_only_interchange_fields(client, fixture_flow):
    r = client.get(f"/api/pipelines/{fixture_flow}/export")
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) == {"name", "label", "desc", "emoji", "g", "steps"}, sorted(body)
    assert body["name"] == fixture_flow
    assert isinstance(body["steps"], list) and body["steps"]
    assert "id" not in body and "builtin" not in body and "created_at" not in body


def test_export_sets_a_download_filename(client, fixture_flow):
    cd = client.get(f"/api/pipelines/{fixture_flow}/export").headers["content-disposition"]
    assert f'filename="loom-{fixture_flow}.json"' in cd, cd


def test_export_unknown_pipeline_is_404(client):
    assert client.get("/api/pipelines/no-such-flow/export").status_code == 404


def test_exported_file_imports_back_unchanged(client, fixture_flow):
    src = client.get(f"/api/pipelines/{fixture_flow}/export").json()
    assert src["steps"], "源流程没有步骤，测不出什么"
    dst = dict(src, name="roundtrip-flow", label="回环测试")
    r = client.post("/api/pipelines", json=dst)
    assert r.status_code == 200, r.text
    assert "roundtrip-flow" in _names(client)
    back = client.get("/api/pipelines/roundtrip-flow/export").json()
    assert back["steps"] == src["steps"], "步骤在导出→导入之间被改了"
    assert back["label"] == "回环测试"
    db.delete_pipeline("roundtrip-flow")


def test_import_onto_an_existing_name_is_rejected(client, fixture_flow):
    """撞名要报错，前端靠这个返回决定「另存为 xxx-copy」的确认框。"""
    src = client.get(f"/api/pipelines/{fixture_flow}/export").json()
    r = client.post("/api/pipelines", json=src)
    assert r.status_code == 400
    assert "已存在" in r.json()["detail"]


def test_steps_survive_the_normalize_roundtrip(client, fixture_flow):
    """步骤里没在 normalize_steps 白名单内的字段会被裁掉，
    裁掉之后不能再被当成"导出丢了东西"，所以这里只比白名单内的键。"""
    keep = {"key", "label", "skill", "skill_src", "out", "checkpoint", "role",
            "engine", "model", "extra_prompt"}
    src = client.get(f"/api/pipelines/{fixture_flow}/export").json()["steps"]
    assert all(set(s) <= keep for s in src), [sorted(set(s) - keep) for s in src]


def test_the_skill_source_survives_the_roundtrip(client, fixture_flow):
    """技能来自哪一家，是导出文件里必须带走的一件事 ——
    丢了它，换台机器导入回来那些步骤就会去 Loom 自己的目录里找一个不存在的技能。"""
    src = client.get(f"/api/pipelines/{fixture_flow}/export").json()
    by = {s["key"]: s for s in src["steps"]}
    assert by["execute"]["skill_src"] == "claude"
    dst = dict(src, name="src-flow", label="来源回环")
    assert client.post("/api/pipelines", json=dst).status_code == 200
    back = {s["key"]: s for s in
            client.get("/api/pipelines/src-flow/export").json()["steps"]}
    assert back["execute"]["skill_src"] == "claude"
    assert back["clarify"]["skill_src"] == ""
    db.delete_pipeline("src-flow")


def test_archive_hides_but_deletes_nothing(client, dbsession):
    """归档只是从侧栏收起来。步骤、运行、工作区都得原样在 ——
    这条钉的是"归档不是删除的别名"。"""
    from app import runner
    dbsession.create_pipeline("arch-me", label="要归档", steps=[{"key": "a", "out": "A.md"}])
    dbsession.create_run("run-archme01", "arch-me", steps=[{"key": "a", "status": "done"}])
    runner.workspace_dir("run-archme01")
    r = client.post("/api/pipelines/arch-me/archive", json={"archived": True})
    assert r.status_code == 200, r.text
    p = [x for x in client.get("/api/pipelines").json()["pipelines"] if x["name"] == "arch-me"][0]
    assert p["archived"] == 1 and p["runs"] == 1
    assert p["last_run"]["id"] == "run-archme01"
    assert dbsession.get_pipeline("arch-me")["steps"], "步骤被归档弄没了"
    assert dbsession.get_run("run-archme01"), "运行记录被归档弄没了"
    assert runner.workspace_dir("run-archme01").is_dir(), "工作区被归档弄没了"
    client.post("/api/pipelines/arch-me/archive", json={"archived": False})
    p2 = [x for x in client.get("/api/pipelines").json()["pipelines"] if x["name"] == "arch-me"][0]
    assert p2["archived"] == 0
    client.post("/api/pipelines/arch-me/archive", json={"archived": True})
    assert client.post("/api/pipelines/nope-nope/archive", json={"archived": True}).status_code == 404
    dbsession.delete_run("run-archme01")
    dbsession.delete_pipeline("arch-me")
    import shutil
    shutil.rmtree(runner._ws_path("run-archme01"), ignore_errors=True)


def test_last_run_is_the_newest_per_pipeline(client, dbsession, fresh_runs):
    dbsession.create_pipeline("lr-a", steps=[{"key": "a"}])
    dbsession.create_pipeline("lr-b", steps=[{"key": "b"}])
    for i in range(3):
        dbsession.create_run(f"run-lr{i}", "lr-a", steps=[])
    dbsession.create_run("run-lrb0", "lr-b", steps=[])
    by = {p["name"]: p for p in client.get("/api/pipelines").json()["pipelines"]}
    assert by["lr-a"]["last_run"]["id"] == "run-lr2", "取的不是最近一次"
    assert by["lr-b"]["last_run"]["id"] == "run-lrb0"
    assert by["lr-a"]["runs"] == 3
    conn = dbsession.get_conn()
    conn.execute("DELETE FROM runs WHERE pipeline IN ('lr-a','lr-b')")
    conn.execute("DELETE FROM pipeline_definitions WHERE name IN ('lr-a','lr-b')")
    conn.commit(); conn.close()
