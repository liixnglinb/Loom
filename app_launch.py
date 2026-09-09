# -*- coding: utf-8 -*-
"""FlowForge 智模流水线 · 桌面应用启动入口（纯桌面形态）。

形态：pywebview 原生窗口（Win10/11 自带 WebView2 内核）承载界面——
  独立任务栏图标、关闭窗口即退出程序。**没有浏览器模式**：
  pywebview/WebView2 不可用时弹窗给出明确指引并退出，绝不打开浏览器。

其他行为：
  - 单实例：重复启动时把已有窗口拉到前台，而不是再开一份。
  - 端口被其他程序占用：弹窗提示换端口（MODELFLOW_PORT 环境变量）。
  - GUI 子系统（console=False）：stdout/stderr 为 None 时重定向内存流；
    启动异常弹原生错误框并落盘 data/boot-error.log。

安全说明：本启动器不发任何 HTTP 请求——端口就绪用 TCP 连接探测，
窗口 URL 为常量回环地址（端口经 int 强校验）。
"""
import io
import os
import socket
import sys
import threading
import time

from app.tray import Tray

WINDOW_TITLE = "FlowForge 智模流水线"


def _fix_streams():
    """GUI 子系统下 stdout/stderr 为 None：重定向到内存流，防 print/日志 AttributeError。"""
    try:
        if sys.stdout is None:
            sys.stdout = io.StringIO()
        if sys.stderr is None:
            sys.stderr = io.StringIO()
    except Exception:
        pass


def _alert(msg: str):
    """原生 MessageBox——没有控制台也能把错误递到用户眼前。"""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, msg, "FlowForge", 0x10)
    except Exception:
        pass


def _port_occupied(port: int) -> bool:
    s = socket.socket()
    s.settimeout(0.4)
    r = s.connect_ex(("127.0.0.1", port)) == 0
    s.close()
    return r


def _focus_existing_window() -> bool:
    """把已运行的 FlowForge 窗口拉到前台（单实例语义）。"""
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


def _wait_port_open(port: int, timeout: float = 30.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if _port_occupied(port):
            return True
        time.sleep(0.4)
    return False


def _serve(port: int):
    """在后台线程跑 uvicorn（随窗口关闭一起退出）。"""
    import uvicorn
    import app.main as app_main
    uvicorn.run(app_main.app, host="127.0.0.1", port=port, log_level="warning")


def _validated_port() -> int:
    port = int(os.environ.get("MODELFLOW_PORT", "8000"))
    if not (0 < port < 65536):
        raise ValueError("MODELFLOW_PORT 取值非法（1-65535）")
    return port


def _open_window(port: int):
    """pywebview 原生窗口（唯一形态）。阻塞直到进程退出。

    桌面细节：背景固定白色（防 WebView2 初始化黑闪）；启动时窗口先隐藏，
    就绪后显示；强制浅色标题栏；标题栏「×」子类化为最小化到托盘；
    右下角常驻托盘图标（打开/隐藏/退出）。
    """
    import webview

    def _show_and_theme():
        time.sleep(0.35)                      # 等 WebView2 完成首帧
        try:
            window.show()
        except Exception:
            pass
        try:
            import ctypes
            hwnd = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
            if hwnd:
                light = ctypes.c_int(0)       # FALSE = 浅色标题栏
                for attr in (20, 19):         # DWMWA_USE_IMMERSIVE_DARK_MODE（新旧版本属性号）
                    if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                            hwnd, attr, ctypes.byref(light), 4) == 0:
                        break
                _hook_close_to_hide(hwnd)     # × = 最小化到托盘
                _restore_window_rect(hwnd)    # 恢复上次关闭时的窗口位置/大小
        except Exception:
            pass
        _TRAY.start()                         # 右下角托盘图标常驻
        threading.Thread(target=_tray_tip_once, daemon=True).start()

    window = webview.create_window(
        WINDOW_TITLE,
        "http://127.0.0.1:" + str(int(port)),
        width=1440, height=900, min_size=(1100, 700),
        background_color="#FFFFFF",
        hidden=True,
    )
    global _WIN
    _WIN = window

    threading.Thread(target=_show_and_theme, daemon=True).start()
    webview.start()          # 阻塞直到托盘「退出」触发 os._exit
    time.sleep(0.5)
    if _TRAY:
        _TRAY.destroy()
    os._exit(0)              # 兜底：窗口被真正销毁（系统注销等）才走到这里


_TRAY = None
_WIN = None            # pywebview 窗口对象（托盘「设置」直接跳路由）
_PORT = 0              # 服务端口（构造设置页 URL 用）

_ORIG_WNDPROC = {}


def _tray_tip_once():
    """首次启动后弹一条托盘气泡：引导找不到图标的用户去 ^ 溢出区拖出固定。仅提示一次。"""
    try:
        time.sleep(1.8)                       # 等托盘线程建窗+注册图标完成
        from app import db as _adb
        if _adb.get_setting("tray_tip_done", "") == "1":
            return
        _adb.set_setting("tray_tip_done", "1")
        _TRAY.notify(
            "FlowForge 已启动",
            "应用已在后台运行。若右下角图标被折叠，请点击任务栏 ^ 箭头，"
            "把「FlowForge 智模流水线」图标拖出固定即可。")
    except Exception:
        pass


def _restore_window_rect(hwnd):
    """启动时恢复上次关闭保存的窗口位置/大小（window_rect: x,y,w,h）。"""
    try:
        from app import db as _adb
        val = _adb.get_setting("window_rect", "")
        if not val:
            return
        x, y, w, h = (int(t.strip()) for t in val.split(","))
        if w < 200 or h < 200:                # 明显非法值直接忽略
            return
        import ctypes
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, x, y, w, h, 0x0004 | 0x0010)   # SWP_NOZORDER | SWP_NOACTIVATE
    except Exception:
        pass


def _hook_close_to_hide(hwnd) -> bool:
    """子类化窗口：把标题栏「×」从“退出”改为“最小化到托盘”（WM_CLOSE → 隐藏）。

    窗口过程必须持有引用（Python GC 会回收 ctypes 回调导致崩溃）。
    """
    try:
        import ctypes
        from ctypes import wintypes as wt
        user32 = ctypes.windll.user32
        user32.SetWindowLongPtrW.argtypes = (wt.HWND, ctypes.c_int, ctypes.c_void_p)
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        user32.CallWindowProcW.argtypes = (ctypes.c_void_p, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)
        user32.CallWindowProcW.restype = ctypes.c_longlong

        WndProc = ctypes.WINFUNCTYPE(ctypes.c_longlong, wt.HWND, wt.UINT,
                                     ctypes.c_void_p, ctypes.c_void_p)

        def proc(h, msg, w, l):
            if msg == 0x0010:                       # WM_CLOSE → 记录位置 + 隐藏到托盘
                try:
                    rc = wt.RECT()
                    user32.GetWindowRect(h, ctypes.byref(rc))
                    from app import db as _adb
                    _adb.set_setting("window_rect", "%d,%d,%d,%d" % (
                        rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top))
                except Exception:
                    pass
                user32.ShowWindow(h, 0)             # SW_HIDE
                return 0
            old = _ORIG_WNDPROC.get(int(h or 0))
            wi = w.value if isinstance(w, ctypes.c_void_p) else (w or 0)
            li = l.value if isinstance(l, ctypes.c_void_p) else (l or 0)
            if old:
                return user32.CallWindowProcW(old, h, msg, wi, li)
            return user32.DefWindowProcW(h, msg, wi, li)

        callback = WndProc(proc)
        old = user32.SetWindowLongPtrW(hwnd, -4, ctypes.cast(callback, ctypes.c_void_p))
        _ORIG_WNDPROC[int(hwnd or 0)] = old
        # 强引用防止回调被回收
        _HOOK_CALLBACKS.append(callback)
        return True
    except Exception:
        return False


_HOOK_CALLBACKS = []


def _exit_with_webview2_hint(err: Exception):
    """WebView2 缺失等环境问题：给出明确指引后退出，绝不打开浏览器。"""
    _alert("桌面窗口组件（WebView2）初始化失败。\n\n"
           "请安装 Microsoft Edge WebView2 运行时后重新启动：\n"
           "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
           "错误信息：" + str(err)[:150])
    try:
        from app import paths
        (paths.DATA_DIR / "boot-error.log").write_text(
            "webview init failed: " + str(err), encoding="utf-8")
    except Exception:
        pass
    os._exit(1)


def main():
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    _fix_streams()
    try:
        port = _validated_port()
    except ValueError as e:
        _alert(str(e))
        return

    # 单实例：已有实例在跑 → 把它的窗口拉到前台即可
    if _port_occupied(port):
        if _focus_existing_window():
            return
        _alert(f"端口 {port} 已被其他程序占用，无法启动。\n\n"
               f"如需换端口：设置环境变量 MODELFLOW_PORT 后重新启动。")
        return

    print("FlowForge 智模流水线 启动: http://127.0.0.1:" + str(port))
    try:
        threading.Thread(target=_serve, args=(port,), daemon=True).start()
    except Exception:
        import traceback
        err = traceback.format_exc()
        try:
            from app import paths
            (paths.DATA_DIR / "boot-error.log").write_text(err, encoding="utf-8")
        except Exception:
            pass
        _alert("服务线程启动失败，已退出。\n\n详情见安装目录 data\\boot-error.log")
        return

    if not _wait_port_open(port, timeout=30.0):
        _alert("服务启动超时，已退出。\n\n详情见安装目录 data\\boot-error.log")
        return
    time.sleep(1.2)          # 端口通了再留一拍给应用完成初始化

    global _TRAY, _WIN, _PORT
    _PORT = port

    def _show_win():
        """把已隐藏的主窗口拉回前台（托盘菜单/单击唤起）。"""
        import ctypes
        hw = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
        if hw:
            ctypes.windll.user32.ShowWindow(hw, 9)      # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hw)

    def _hide_win():
        """隐藏主窗口到托盘，后台服务继续运行。"""
        import ctypes
        hw = ctypes.windll.user32.FindWindowW(None, WINDOW_TITLE)
        if hw:
            ctypes.windll.user32.ShowWindow(hw, 0)      # SW_HIDE

    def _open_ws_dir():
        """托盘菜单项：打开工作区目录（资源管理器）。"""
        from app import paths
        import subprocess
        p = paths.WS_ROOT.resolve()
        if p.exists():
            subprocess.Popen(['explorer.exe', str(p)])

    def _open_settings():
        """托盘菜单项：直接跳到设置页，并显示窗口。"""
        _show_win()
        if _WIN:
            try:
                _WIN.load_url("http://127.0.0.1:%d/settings" % int(_PORT))
            except Exception:
                pass

    def _toggle_autostart():
        """托盘菜单项：切换开机自启（HKCU Run 注册表）。"""
        import winreg
        import os as _os
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                             winreg.KEY_ALL_ACCESS)
        cur = None
        try:
            cur, _ = winreg.QueryValueEx(key, "FlowForge")
        except FileNotFoundError:
            pass
        if getattr(sys, 'frozen', False):
            cmd = '"%s"' % sys.executable
        else:
            launch = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "app_launch.py")
            cmd = '"%s" "%s"' % (sys.executable, launch)
        if cur:
            winreg.DeleteValue(key, "FlowForge")
        else:
            winreg.SetValueEx(key, "FlowForge", 0, winreg.REG_SZ, cmd)
        winreg.CloseKey(key)

    def _get_autostart_enabled():
        """读取注册表判断当前开机自启状态（用于菜单勾选）。"""
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Run", 0,
                                winreg.KEY_READ)
            cur, _ = winreg.QueryValueEx(key, "FlowForge")
            winreg.CloseKey(key)
            return bool(cur)
        except Exception:
            return False

    def _quit_app():
        if _TRAY:
            _TRAY.destroy()
        os._exit(0)

    _TRAY = Tray(WINDOW_TITLE,
                 on_open=_show_win, on_hide=_hide_win, on_quit=_quit_app,
                 on_open_ws=_open_ws_dir, on_settings=_open_settings,
                 on_autostart=_toggle_autostart,
                 autostart_enabled=_get_autostart_enabled)

    try:
        _open_window(port)   # 阻塞直到托盘「退出」
    except Exception as e:
        _exit_with_webview2_hint(e)


if __name__ == "__main__":
    main()
