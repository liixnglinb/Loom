# -*- coding: utf-8 -*-
"""技能这一整条链：软件不再随包带出厂技能，可写目录就是唯一的那一份。

出厂库撤掉之后最怕两件事：一是 BASE/skills 那支扫描还留着（旧版本装过的目录里
那份只读副本会悄悄复活，界面上还多一个没人用得上的"内置·只读"），
二是读口的校验比写口松（写口 _skill_dir_safe 卡得很死，读口曾经拿原始 name 拼路径）。
"""
import pytest

from app import paths  # noqa: E402  (conftest 已经先把数据目录挪进沙箱)

BODY = "---\nname: demo-skill\n---\n\n# 演示技能\n\n正文一段。"


@pytest.fixture
def demo(client):
    r = client.post("/api/skills", json={"name": "demo-skill", "content": BODY})
    assert r.status_code == 200, r.text
    yield "demo-skill"
    client.delete("/api/skills/demo-skill")


def test_listing_shape_has_no_source_column(client, demo):
    """source（user/bundled）这个字段没了：只剩一个取值就没有区分意义，
    留着只会让前端继续留一条永远走不到的只读分支。"""
    skills = client.get("/api/skills").json()["skills"]
    mine = [s for s in skills if s["name"] == "demo-skill"]
    assert len(mine) == 1
    assert set(mine[0]) == {"name", "desc", "chars"}, sorted(mine[0])
    assert mine[0]["desc"] == "演示技能"


def test_stale_factory_skills_dir_stays_invisible(client, demo, monkeypatch, tmp_path):
    """装过 1.0.0 的目录里还留着 skills/ff-*：那一份不能再出现在列表里。"""
    ghost = tmp_path / "skills" / "ff-legacy"
    ghost.mkdir(parents=True)
    (ghost / "SKILL.md").write_text(BODY.replace("demo-skill", "ff-legacy"), encoding="utf-8")
    monkeypatch.setattr(paths, "BASE", tmp_path)
    names = [s["name"] for s in client.get("/api/skills").json()["skills"]]
    assert "demo-skill" in names and "ff-legacy" not in names
    assert client.get("/api/skills/ff-legacy").status_code == 404
    assert client.post("/api/skills/ff-legacy/duplicate",
                       json={"name": "legacy-copy"}).status_code == 404


@pytest.mark.parametrize("name", [
    "..%2F..%2Fsettings", "%2e%2e", "Demo-Skill", "demo skill", "a" * 65,
])
def test_read_side_is_as_strict_as_the_write_side(client, name):
    """写口只认 [a-z0-9][a-z0-9_-]{0,63}；读口以前拿原始 name 直接拼路径，
    等于两个口子一严一松。现在共用同一个校验。"""
    assert client.get(f"/api/skills/{name}").status_code == 404


def test_duplicate_copies_within_the_user_dir(client, demo):
    r = client.post(f"/api/skills/{demo}/duplicate", json={"name": "demo-copy"})
    assert r.status_code == 200, r.text
    assert "demo-copy" in [s["name"] for s in client.get("/api/skills").json()["skills"]]
    assert client.get("/api/skills/demo-copy").json()["content"] == BODY + "\n"
    client.delete("/api/skills/demo-copy")


def test_get_skill_is_readable_by_anyone_with_the_id(client, demo):
    """详情页现在恒为可编辑 —— 这条钉住的是形状本身：
    既然只剩一个取值，界面就不该再为另一个取值留分支。"""
    d = client.get(f"/api/skills/{demo}").json()
    assert d["editable"] is True
    assert d["content"] == BODY + "\n"


def test_skill_content_is_capped_on_both_write_paths(client):
    """SKILL.md 是**整篇**塞进每一步的提示词的（runner.compose_skill_prompt）。
    没上限的话一张贴进来的大表就能把某一步的上下文全吃掉 —— 智能体要么直接
    报错，要么把这一步的预算全花在复读上。超限要在写盘之前拒掉。"""
    from app.main import _SKILL_WRITE_MAX_BYTES
    big = "字" * (_SKILL_WRITE_MAX_BYTES)      # 一字 3 字节，稳超上限

    r = client.post("/api/skills", json={"name": "cap-new", "content": big})
    assert r.status_code == 413, r.status_code
    assert "KB" in r.json()["detail"]
    assert not (paths.USER_SKILLS_DIR / "cap-new").exists(), "拒了却还是把目录建出来了"

    assert client.post("/api/skills", json={"name": "cap-ok", "content": "小"}).status_code == 200
    r2 = client.put("/api/skills/cap-ok", json={"name": "cap-ok", "content": big})
    assert r2.status_code == 413, r2.status_code
    kept = (paths.USER_SKILLS_DIR / "cap-ok" / "SKILL.md").read_text(encoding="utf-8")
    assert kept.strip() == "小", f"拒掉的写入把原文覆盖掉了：{kept[:40]}"
    client.delete("/api/skills/cap-ok")


def test_imported_package_respects_the_same_cap(client):
    """导入那条路吃的是别人写的包，更得判 —— 超限的包整个不收。"""
    import io
    import zipfile

    from app.main import _SKILL_WRITE_MAX_BYTES
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("big-skill/SKILL.md",
                    "---\nname: big-skill\n---\n\n" + "字" * _SKILL_WRITE_MAX_BYTES)
    r = client.post("/api/skills/import",
                    files={"file": ("big.zip", buf.getvalue(), "application/zip")})
    assert r.status_code == 413, r.status_code
    assert not (paths.USER_SKILLS_DIR / "big-skill").exists()


def test_import_reads_in_chunks_not_all_at_once():
    """那个 200MB 上限以前是 raw = await file.read() 之后才判 len —— 也就是
    **先把整个文件读进内存再决定要不要拒绝**。一台 16GB 的机器上，一个 2GB 的
    包会先把它顶到 swapping 才被拒。分块累加才是真有上限。"""
    import inspect
    import re

    from app import main
    # 只扫真代码：那句"以前是 raw = await file.read()"的注释会把这条断言撞红，
    # 而它描述的恰恰是被修掉的旧写法。
    src = "\n".join(l for l in inspect.getsource(main.import_skill).splitlines()
                    if not l.strip().startswith("#"))
    assert not re.search(r"await file\.read\(\s*\)", src), \
        "又变回一次性读完了：无参 read() 会把整个上传先吃进内存"
    assert re.search(r"await file\.read\(\s*1 << 20\s*\)", src), "没按块读"
