# -*- coding: utf-8 -*-
"""data/updates 的清理：装完留下的 60MB 安装包要有一个人删它。"""
import os
from pathlib import Path

import pytest

from app import paths, updater


def _touch(root: Path, rel: str, data: bytes = b"x"):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


@pytest.fixture
def udir(tmp_path, monkeypatch):
    root = tmp_path / "updates"
    root.mkdir()
    monkeypatch.setattr(updater, "updates_dir", lambda: root)
    return root


def test_sweep_removes_leftover_packages_and_the_bat(udir):
    old = _touch(udir, "Loom-1.2.0-setup.exe", b"meh")
    bat = _touch(udir, "update.bat", b"@echo off")
    part = _touch(udir, "Loom-1.2.1-setup.exe.tmp", b"half")
    assert updater.sweep_leftovers() == 3
    assert not old.exists() and not bat.exists() and not part.exists()


def test_sweep_keeps_the_package_that_is_waiting_to_be_installed(udir, monkeypatch):
    """已下好、还没点安装的那一个不能删 —— 用户重启后还得能装上，
    而且 check() 之后 STATE["path"] 指的是它。"""
    keep = _touch(udir, "Loom-1.3.0-setup.exe", b"genuine")
    _touch(udir, "Loom-1.2.9-setup.exe", b"old")
    monkeypatch.setattr(updater, "snapshot",
                        lambda: {"path": str(keep), "phase": "ready"})
    assert updater.sweep_leftovers() == 1
    assert keep.is_file()


def test_sweep_leaves_unrelated_files_and_subdirectories_alone(udir):
    """这个目录今天只有包和脚本，将来未必。删只按后缀删、且不递归 ——
    一次"顺手清理"扫进子目录，删掉的可能是别人放的东西。"""
    note = _touch(udir, "README.txt", b"keep me")
    sub = _touch(udir, "sub/inner.exe", b"not mine")
    assert updater.sweep_leftovers() == 0
    assert note.is_file() and sub.is_file()


def test_sweep_survives_a_locked_file(udir, monkeypatch):
    """杀软还在扫那个 exe 时会撞 sharing violation。启动路径上不能因为清不干净
    就抛出来 —— 弹个框只会让人以为软件坏了，而这件事本来就该静默。"""
    left = _touch(udir, "Loom-1.2.0-setup.exe")

    def boom(self, *a, **k):
        raise OSError("being used by another process")

    monkeypatch.setattr(Path, "unlink", boom)
    assert updater.sweep_leftovers() == 0
    assert left.is_file(), "删不掉也要留在原地，别先把记账删了"


def test_apply_batch_deletes_the_package_after_a_good_install():
    """批处理以前只 del 自己，安装包留在原地。"""
    bat = updater.BAT_TMPL.format(setup=r"C:\data\updates\Loom-1.2.4-setup.exe")
    assert 'del "C:\\data\\updates\\Loom-1.2.4-setup.exe"' in bat
    assert "%~f0" in bat, "脚本自己也要删掉"
    # 装失败（errorlevel 非 0）时必须留着现场，别把唯一能重装的那个文件删了
    assert "neq 0" in bat
