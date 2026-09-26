# -*- coding: utf-8 -*-
"""发布脚本的自检：上传之前，清单必须和真正要传的那个文件对得上。

更新器现在完全信任 latest.json 做安全判定（sha256 不符就拒装、file 与 url
对不上就拒下）。所以一份手改过或忘了重新生成的清单传上去，代价是所有人
「检查更新通过、点安装就报错」，而且只有已装过旧版的人才会碰到 —— 本地测不出来。
"""
import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "upload_cos", Path(__file__).resolve().parent.parent / "upload_cos.py")
upload_cos = importlib.util.module_from_spec(_spec)
sys.modules["upload_cos"] = upload_cos
_spec.loader.exec_module(upload_cos)

SHA = "a" * 64
BASE = "https://modelflow-1447874637.cos.ap-guangzhou.myqcloud.com"
GOOD = {
    "version": "1.2.4",
    "file": "Loom-1.2.4-setup.exe",
    "url": BASE + "/Loom-1.2.4-setup.exe",
    "sha256": SHA,
    "size": 78643210,
    "notes": "修了 X，加了 Y",
}


def _errs(m=None, sha=SHA, size=78643210):
    return upload_cos.consistency_errors(dict(m or GOOD), sha, size, BASE)


def test_a_matching_manifest_passes():
    assert _errs() == []


def test_stale_sha_is_caught_before_upload():
    """清单没跟着新包重新生成，是最常见的一种错。"""
    e = _errs(sha="b" * 64)
    assert any("sha256" in x for x in e), e


def test_size_mismatch_is_caught():
    e = _errs(size=123)
    assert any("size" in x for x in e), e


def test_file_and_version_must_agree():
    """make_release 按版本号命名；这两个不一致就说明有人在中间手动改过清单。"""
    e = _errs({**GOOD, "file": "Loom-1.2.3-setup.exe"})
    assert any("version" in x for x in e), e


def test_url_must_point_at_the_file_and_the_bucket():
    e = _errs({**GOOD, "url": BASE + "/Loom-9.9.9-setup.exe"})
    assert any("不是 file" in x or "指向" in x for x in e), e
    e = _errs({**GOOD, "url": "https://elsewhere.test/Loom-1.2.4-setup.exe"})
    assert any("不在我们要传的桶" in x for x in e), e
    assert not any(x.startswith("url 必须") for x in e), e     # https 那关是过的
    e = _errs({**GOOD, "url": "http://x/Loom-1.2.4-setup.exe"})
    assert any("https" in x for x in e), e


def test_path_traversal_in_file_is_caught():
    e = _errs({**GOOD, "file": "../Loom-1.2.4-setup.exe",
               "url": BASE + "/../Loom-1.2.4-setup.exe"})
    assert any("纯文件名" in x for x in e), e


def test_empty_notes_is_caught():
    """notes 会渲染进更新浮层：空的就是一块白，而发版时 --notes 忘写太常见了。"""
    assert any("notes" in x for x in _errs({**GOOD, "notes": "   "}))


def test_missing_version_is_caught():
    assert any("version" in x for x in _errs({**GOOD, "version": ""}))


def test_the_sha_helper_hashes_a_real_file(tmp_path):
    f = tmp_path / "x.bin"
    f.write_bytes(b"hello")
    assert upload_cos.sha256_of(f) == \
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
