# -*- coding: utf-8 -*-
"""数据层的并发与查询计划：这几条不是性能偏好，是"偶发 500"的成因。

默认 journal_mode=delete 下，跑任务那条线程每步要写好几回落库，而页面每
400ms 轮询一次事件、设置页随时在读 runs —— 读写互相把对方堵死，表现就是
sqlite3.OperationalError: database is locked 冒成接口的 500。
"""
import threading
import time

import pytest

from app import db


def _plan(sql):
    conn = db.get_conn()
    try:
        return " ".join(str(r[-1]) for r in conn.execute("EXPLAIN QUERY PLAN " + sql))
    finally:
        conn.close()


def test_connections_run_in_wal_with_a_busy_timeout():
    """三个 PRAGMA 少一个都退回原样：journal_mode 是库级持久的，但每个新连接
    都要设 busy_timeout 和 synchronous，否则那条连接照样立刻抛锁。"""
    conn = db.get_conn()
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert int(conn.execute("PRAGMA busy_timeout").fetchone()[0]) >= 5000
        assert int(conn.execute("PRAGMA synchronous").fetchone()[0]) == 1
    finally:
        conn.close()


def test_the_runs_list_queries_are_indexed():
    """没索引时这两条都是 SCAN runs + USE TEMP B-TREE FOR ORDER BY：4000 条实测
    1.39ms/0.32ms，走索引是 0.09ms/0.08ms。数字本身不重要，"扫全表排序"才重要。"""
    names = {r[1] for r in db.get_conn().execute("PRAGMA index_list('runs')")}
    assert "idx_runs_created" in names and "idx_runs_pipeline" in names

    p = _plan("SELECT * FROM runs ORDER BY created_at DESC, id DESC LIMIT 50")
    assert "idx_runs_created" in p, p
    assert "TEMP B-TREE" not in p, f"还在建临时排序树：{p}"

    p = _plan("SELECT * FROM runs WHERE pipeline='p7' "
              "ORDER BY created_at DESC, id DESC LIMIT 50")
    assert "idx_runs_pipeline" in p, p
    assert "TEMP B-TREE" not in p, f"还在建临时排序树：{p}"


def test_a_writer_and_two_readers_do_not_throw_locked(dbsession):
    """打不了真锁就别说 WAL 有用：三个线程同时读写，任何一次 OperationalError
    都会把这条测试打红。写完还要对得上数，别让"没报错"掩盖丢写。"""
    errs = []
    stop = threading.Event()

    def writer():
        try:
            for i in range(120):
                dbsession.create_run(f"run-wl{i:06d}", "wal-flow", f"第 {i} 次")
                dbsession.update_run(f"run-wl{i:06d}", status="done")
        except Exception as e:            # noqa: BLE001 - 这条测试就是要抓异常
            errs.append(repr(e))
        finally:
            stop.set()

    def reader():
        # 读侧不带 try：SQLite 的读锁冲突同样会抛，抛了就是这条测试该红
        while not stop.is_set():
            dbsession.list_runs(None, 50)
            dbsession.run_status_counts()
            time.sleep(0.001)

    ts = [threading.Thread(target=writer)] + \
         [threading.Thread(target=reader) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=30)
    assert not any(t.is_alive() for t in ts), "有线程卡死了"

    got = [r["id"] for r in dbsession.list_runs(None, 500)
           if (r["id"] or "").startswith("run-wl")]
    try:
        assert errs == [], f"读写撞锁了：{errs[:2]}"
        assert len(got) == 120, f"写了 120 条，库里只有 {len(got)} 条"
    finally:
        for rid in got:
            dbsession.delete_run(rid)
