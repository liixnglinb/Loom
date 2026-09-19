# -*- coding: utf-8 -*-
"""Loom 织流 · 打包后的桌面入口（源码运行仍用 python run.py）。

形态：后台线程跑 uvicorn，前台优先开 pywebview 原生窗口（Win10/11 的 WebView2）。
**开不出原生窗口就退回默认浏览器** —— 软件本体是个本地 Web 应用，
窗口壳只是体验差异，不该成为启动失败的理由。

其他行为：
  - 单实例：端口已被占用时，把已有窗口拉到前台，而不是再起一份服务。
  - 冻结态 console=False 时 stdout/stderr 是 None：先重定向到内存流，
    否则任何一句 print 都会 AttributeError 把启动打断。
  - 启动异常弹原生消息框并落盘 data/boot-error.log，用户看得见、你查得到。

端口取 LOOM_PORT 环境变量（默认 8000），int 强校验后才拼进 URL。
"""
import io
import os
import socket
import sys
import threading
import time

WINDOW_TITLE = "织流 Loom"
DEFAULT_PORT = 8000


def _fix_streams():
    try:
        if sys.stdout is None:
            sys.stdout = io.StringIO()
        if sys.stderr is None:
            sys.stderr = io.StringIO()
    except Exception:
        pass


def _alert(msg: str):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, msg, WINDOW_TITLE, 0x10)
    except Exception:
        pass


def _log_exc(kind, exc):
    try:
        import traceback
        from app import paths
        (paths.DATA_DIR / "boot-error.log").write_text(
            f"[{kind}] {exc}\n\n{traceback.format_exc()}", encoding="utf-8")
    except Exception:
        pass


def _port_busy(port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.4)
    busy = s.connect_ex(("127.0.0.1", port)) == 0
    s.close()
    return busy


def _focus_existing() -> bool:
    try:
        import ctypes
        hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 9)          # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            return True
    except Exception:
        pass
    return False


def _validated_port() -> int:
    raw = os.environ.get("LOOM_PORT") or str(DEFAULT_PORT)
    port = int(raw)
    if not 0 < port < 65536:
        raise ValueError("LOOM_PORT 取值非法（1-65535）")
    return port


def _serve(port: int):
    import uvicorn
    from app.main import app
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


def _wait_ready(port: int, timeout: float = 40.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if _port_busy(port):
            return True
        time.sleep(0.4)
    return False


def _open_in_browser(port: int):
    import webbrowser
    webbrowser.open(f"http://127.0.0.1:{int(port)}")


def _run_window(port: int) -> bool:
    """开原生窗口；返回 False 表示这条路口前不可用，调用方退回浏览器。"""
    try:
        import webview
        webview.create_window(WINDOW_TITLE, f"http://127.0.0.1:{int(port)}",
                              width=1440, height=900, min_size=(980, 620))
        webview.start()
        return True
    except Exception as e:
        _log_exc("webview", e)
        return False


def main():
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _fix_streams()
    try:
        port = _validated_port()
    except ValueError as e:
        _alert(str(e))
        return 2

    if _port_busy(port):
        if _focus_existing():
            return 0
        _alert(f"端口 {port} 已被其他程序占用，Loom 起不来。\n\n"
               f"可以：① 结束占用该端口的程序；② 设置环境变量 LOOM_PORT 换端口后重试。")
        return 1

    url = f"http://127.0.0.1:{port}"
    print(f"Loom 织流 启动 {url}")
    try:
        threading.Thread(target=_serve, args=(port,), daemon=True).start()
    except Exception as e:
        _log_exc("serve", e)
        _alert("本地服务线程启动失败。\n\n详情见安装目录 data\\boot-error.log")
        return 1

    if not _wait_ready(port):
        _alert("本地服务启动超时（40 秒）。\n\n详情见安装目录 data\\boot-error.log")
        return 1
    time.sleep(0.6)                      # 端口通了再留一拍给应用完成初始化

    if _run_window(port):
        return 0
    # 原生窗口不可用：开浏览器，主线程挂住不让守护线程随进程退出
    _open_in_browser(port)
    threading.Event().wait()


if __name__ == "__main__":
    sys.exit(main())
