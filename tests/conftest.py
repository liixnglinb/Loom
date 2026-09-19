# -*- coding: utf-8 -*-
"""测试沙箱：把数据目录整体挪到临时目录，绝不碰用户真实的 modex-data。

paths.* 是模块级常量、db 在 import 时就建表，所以引导必须写在 conftest
模块顶层 —— 任何测试文件 import app.* 之前先把它换掉。
"""
import copy
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
STATIC_DIR = ROOT / "static"

_HOME = Path(tempfile.mkdtemp(prefix="loom-test-"))

from app import paths  # noqa: E402

paths.DATA_DIR = _HOME
paths.DB_DIR = _HOME / "db"
paths.USER_SKILLS_DIR = _HOME / "skills"
paths.EXPORT_DIR = _HOME / "export"
paths.WORKSPACES_DIR = _HOME / "workspaces"
for _p in (paths.DB_DIR, paths.USER_SKILLS_DIR, paths.EXPORT_DIR, paths.WORKSPACES_DIR):
    _p.mkdir(parents=True, exist_ok=True)

from app import db  # noqa: E402

db.DB_DIR = paths.DB_DIR
db.DB_PATH = paths.DB_DIR / "flowforge.db"
db.init_db()

from app import agents, runner  # noqa: E402

agents.clear_bin_cache()


@pytest.fixture(scope="session")
def app_module():
    # 放在 fixture 里 import：内置库播种要等沙箱目录就位
    from app import main
    return main


@pytest.fixture(scope="session")
def client(app_module):
    from fastapi.testclient import TestClient
    return TestClient(app_module.app)


@pytest.fixture
def dbsession():
    return db


@pytest.fixture
def workspaces():
    return paths.WORKSPACES_DIR


@pytest.fixture(autouse=True)
def _restore_settings():
    """settings 是全库单例，且 get_setting 带进程内缓存：跑完连缓存一起还原。"""
    before = copy.deepcopy(db.get_all_settings())
    yield
    conn = db.get_conn()
    conn.execute("DELETE FROM settings")
    conn.commit()
    conn.close()
    db._SETTING_CACHE.clear()
    for k, v in before.items():
        db.set_setting(k, v)
    db._SETTING_CACHE.clear()


@pytest.fixture
def fresh_runs():
    conn = db.get_conn()
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()
    runner._BUSES.clear()
    runner._CANCEL.clear()
    return db.list_runs
