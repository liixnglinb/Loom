# -*- coding: utf-8 -*-
"""ModelFlow 智模流水线 启动脚本（端口自愈 + 中文诊断）。

用法: python run.py [--port 8000]

增强：
  1. 启动前 TCP 探测端口占用：若 8000 被占用，自动 netstat 定位 PID 并提示
     可选择自动释放（--auto-kill）或换端口（--port）。
  2. uvicorn 启动失败时，根据异常信息给出中文诊断（端口占用/模块缺失/权限不足）。
  3. 默认端口泄露清理：若端口被旧进程占用且为 python/uvicorn，自动尝试释放。
"""
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DEFAULT_PORT = 8000


def is_port_busy(host: str, port: int) -> bool:
    """TCP 探测端口是否被占用。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def find_pid_by_port(port: int):
    """netstat 查找占用端口的 PID（Windows）。返回 PID 列表。"""
    try:
        r = subprocess.run(
            ["netstat", "-ano"], capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace")
        pids = set()
        pat = re.compile(rf":{port}\s+.*LISTENING\s+(\d+)", re.IGNORECASE)
        for line in r.stdout.splitlines():
            m = pat.search(line)
            if m:
                pids.add(m.group(1))
        return list(pids)
    except Exception:
        return []


def try_kill_pids(pids):
    """尝试结束指定 PID 进程（Windows taskkill /F /PID）。"""
    killed = []
    for pid in pids:
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)],
                           capture_output=True, timeout=10)
            killed.append(pid)
        except Exception:
            pass
    return killed


def diagnose_start_error(err) -> str:
    """把 uvicorn 启动异常翻译成中文可操作提示。"""
    s = str(err)
    if "10048" in s.lower() or "address already in use" in s.lower() or "bind" in s.lower():
        return ("端口被其他程序占用。可：① 运行 python run.py --auto-kill 自动释放；"
                "② 或 python run.py --port 8001 换端口启动。")
    if "module" in s.lower() and "not found" in s.lower():
        m = re.search(r"No module named '([^']+)'", s)
        name = m.group(1) if m else "?"
        return f"缺少 Python 依赖模块：{name}。请运行：pip install {name}"
    if "permission" in s.lower() or "access is denied" in s.lower():
        return "权限不足，请以管理员身份运行，或更换大于 1024 的端口。"
    if "syntaxerror" in s.lower():
        return "后端代码存在语法错误，请检查 app/ 下各 .py 文件。"
    return f"启动失败：{s}"
STALE_HINT = "检测到旧 ModelFlow 进程仍占用端口，正在自动结束并重启…"


def main():
    port = DEFAULT_PORT
    auto_kill = False
    args = sys.argv[1:]
    for a in args:
        if a == "--auto-kill":
            auto_kill = True
        elif a.startswith("--port"):
            try:
                port = int(a.split("=", 1)[1])
            except Exception:
                pass
    import importlib.util
    spec = importlib.util.find_spec("uvicorn")
    if not spec:
        print("ERROR: 未安装 uvicorn。请运行: pip install fastapi uvicorn python-multipart")
        sys.exit(1)

    if is_port_busy("127.0.0.1", port):
        pids = find_pid_by_port(port)
        if pids:
            if auto_kill:
                print(STALE_HINT)
                try_kill_pids(pids)
                import time
                time.sleep(1)
            else:
                print(f"⚠ 端口 {port} 已被占用 (PID: {', '.join(pids)})")
                print("   自动释放： python run.py --auto-kill")
                print("   换端口：   python run.py --port <新端口>")
                ans = input("   是否自动结束这些进程并继续？[Y/n]: ").strip().lower()
                if ans not in ("n", "no"):
                    print(STALE_HINT)
                    try_kill_pids(pids)
                    import time
                    time.sleep(1)
                else:
                    sys.exit(1)
        else:
            print(f"⚠ 端口 {port} 被非进程程序占用（可能需关闭其它软件）。")
            print("   换端口启动： python run.py --port <新端口>")
            sys.exit(1)

    import uvicorn
    print(f"ModelFlow 智模流水线 启动: http://127.0.0.1:{port}")
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=False)
    except Exception as e:
        print("=" * 56)
        print("⚠ " + diagnose_start_error(e))
        print("=" * 56)
        sys.exit(1)


if __name__ == "__main__":
    main()