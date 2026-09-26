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
    """批处理以前只 del 自己，安装包留在原地。
    只看真执行的行：模板的注释里就写着旧写法（timeout / start /wait / neq 0），
    整段扫字符串等于测了段散文 —— 这个坑这轮已经踩过三次了。"""
    lines = [l for l in updater.BAT_TMPL.format(setup="S").splitlines()
             if l.strip() and not l.strip().startswith("rem")]
    code = "\n".join(lines)
    assert 'del "S"' in code
    assert "%~f0" in code, "脚本自己也要删掉"
    # 装失败（退出码非 0）时必须留着现场：那是用户唯一还能重装一次的东西
    assert "if errorlevel 1 goto :keep" in code, code
    assert "timeout" not in code, "timeout 在标准输入被重定向时不睡，等主进程退场是假的"
    assert "start " not in code, "别回到 start /wait：它不返回时退出码是空的"
    assert "ping -n 4" in code, "等待要用 ping 才真睡得着"


# ==================== 那段安装批处理：真的跑一遍 ====================
# 1.2.4 刚发出去就拿当前模板实测过一轮。真 PE 桩下"删/留"两支其实都对，
# 量出来的真问题是**等待没发生**：timeout /t 3 在标准输入被重定向时（我们用
# DETACHED_PROCESS 起，正是这种）直接报错返回，整段脚本 0.69 秒就往下走，
# 而主进程 0.8 秒后才 os._exit —— 安装器是在换一个还没退出的程序。
# 现在换成 ping 计时 + 安装器直接当子进程调用（少一个会骗人的环节：
# start /wait 对批处理桩根本不返回，%errorlevel% 留空，那行 if 当场语法错）。
# 桩必须是**真 PE**：拿 .cmd 当桩测出来的"没删"是仪器的锅 —— 批处理里直接写
# foo.cmd（不带 call）是交出控制权、永不返回，而真安装器是 exe。

import subprocess
import time


def _coreutils(label):
    import shutil
    return shutil.which(label)


_needs = (_coreutils("true"), _coreutils("false"))
pytestmark_stub = pytest.mark.skipif(
    os.name != "nt" or not all(_needs),
    reason="要在 Windows 上跑 cmd，且得有 true/false 两个真 PE 当桩")


def _run_bat(tmp_path, stub_src):
    setup = tmp_path / "Loom-9.9.9-setup.exe"
    setup.write_bytes(Path(stub_src).read_bytes())
    bat = tmp_path / "update.bat"
    bat.write_text(updater.BAT_TMPL.format(setup=str(setup)), encoding="mbcs")
    flags = 0x00000008 | 0x00000200 | 0x08000000
    devnull = subprocess.DEVNULL
    t0 = time.perf_counter()
    subprocess.run(["cmd", "/C", str(bat)], creationflags=flags, cwd=str(tmp_path),
                   stdin=devnull, stdout=devnull, stderr=devnull, timeout=90)
    for _ in range(25):      # 复制来的真 exe 可能被杀软短暂占用，多等一会儿再判
        if not setup.exists():
            break
        time.sleep(0.2)
    return setup.exists(), bat.exists(), time.perf_counter() - t0


@pytest.mark.skipif(os.name != "nt" or not all(_needs),
                    reason="要在 Windows 上跑 cmd，且得有 true/false 两个真 PE 当桩")
def test_batch_deletes_the_package_after_a_successful_install(tmp_path):
    gone_setup, gone_bat, dt = _run_bat(tmp_path, _coreutils("true"))
    assert not gone_setup, "装成功了，那个 36MB 的包还留在 data/updates 里"
    assert not gone_bat, "装成功了，批处理自己该跟着删掉"
    # 那三秒是"等主进程退场"的窗口。timeout 在被重定向时不睡，实测 0.02s 就往下走，
    # 于是安装器会在我们还没退出的时候就动手换文件 —— 用 ping 之后必须真睡到。
    assert dt >= 2.0, f"等待没真的发生（{dt:.2f}s），3 秒退场窗口是假的"


@pytest.mark.skipif(os.name != "nt" or not all(_needs),
                    reason="要在 Windows 上跑 cmd，且得有 true/false 两个真 PE 当桩")
def test_batch_keeps_everything_when_the_install_fails(tmp_path):
    """装失败不能把现场一起删了 —— 那是用户唯一还能重装一次的东西。"""
    gone_setup, gone_bat, _ = _run_bat(tmp_path, _coreutils("false"))
    assert gone_setup, "装失败了还把安装包删了"
    assert gone_bat, "装失败了还把脚本删了（虽然它自己没跑到删那行）"
