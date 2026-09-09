# -*- coding: utf-8 -*-
"""系统托盘图标（Windows 通知区域 / 任务栏右下角）。

纯 ctypes 实现，零第三方依赖：运行时从当前可执行文件提取图标（ExtractIconExW），
右键菜单提供【打开窗口 / 隐藏窗口 / 退出】，左键单击切换窗口显隐。

实现要点（避免踩坑）：
  - 隐藏窗口与消息循环必须在**同一线程**创建/运行：Windows 消息只投递到
    创建窗口的线程队列；跨线程建窗会让托盘回调消息（WM_APP）永远无人处理。
  - Shell_NotifyIcon 回调中 wParam=鼠标消息码，lParam=屏幕坐标，事件判定读 wParam。
  - 隐藏窗口标题独立于主窗口标题，否则按标题 FindWindowW 找主窗口时会误命中托盘窗。
  - c_void_p 参数先转 int 再位运算，否则回调内抛 TypeError 整个事件失效。

用法（在应用主流程里）：
    from app.tray import Tray
    tray = Tray("FlowForge 智模流水线", on_open=show_win, on_hide=hide_win, on_quit=quit_app)
    tray.start()            # 起专用线程（建窗 + 消息循环）
    # 退出时：
    tray.destroy()
"""
import ctypes
import ctypes.wintypes
import sys
import threading
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

# 显式原型，避免 ctypes 默认推断导致句柄溢出
user32.CreateWindowExW.argtypes = [
    ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
user32.CreateWindowExW.restype = ctypes.c_void_p
user32.RegisterClassW.argtypes = [ctypes.c_void_p]
user32.RegisterClassW.restype = ctypes.c_uint16
shell32.Shell_NotifyIconW.argtypes = [ctypes.c_uint, ctypes.c_void_p]
shell32.Shell_NotifyIconW.restype = ctypes.c_int
shell32.ExtractIconExW.argtypes = [ctypes.c_wchar_p, ctypes.c_int, ctypes.c_void_p,
                                   ctypes.c_void_p, ctypes.c_uint]
shell32.ExtractIconExW.restype = ctypes.c_uint
user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
user32.PostMessageW.restype = ctypes.c_int
user32.GetCursorPos.argtypes = [ctypes.c_void_p]
user32.TrackPopupMenu.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
user32.DefWindowProcW.restype = ctypes.c_longlong
user32.AppendMenuW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_wchar_p]
user32.AppendMenuW.restype = ctypes.c_int
user32.LoadImageW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint,
                              ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.LoadImageW.restype = ctypes.c_void_p
user32.ModifyMenuW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                               ctypes.c_uint, ctypes.c_wchar_p]
user32.ModifyMenuW.restype = ctypes.c_int

WM_APP = 0x8000
WM_NULL = 0x0000
WM_CLOSE = 0x0010
WM_CONTEXTMENU = 0x007B
NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004
NOTIFYICON_VERSION_4 = 4
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_INFO = 0x00000001

WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONUP = 0x0205
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002

IDM_SHOW = 40001
IDM_HIDE = 40002
IDM_QUIT = 40003
IDM_WS = 40004          # 打开工作区目录
IDM_SETTINGS = 40005    # 直达设置页
IDM_AUTOSTART = 40006   # 开机自启（勾选态）

MF_CHECKED = 0x0008
MF_STRING = 0x0000
MF_SEPARATOR = 0x0800
TPM_RIGHTBUTTON = 0x0002

GWL_WNDPROC = -4

# LoadImageW / LoadIconW 标志
LR_LOADFROMFILE = 0x00000010
IMAGE_ICON = 1

# 系统默认图标（LoadIconW 的第一个参数为 NULL 时使用）
IDI_APPLICATION = 32512

# explorer.exe 每次（重）启动都会广播此消息：托盘图标必须重注册，否则图标消失
_TASKBAR_CREATED = user32.RegisterWindowMessageW("TaskbarCreated")


class NOTIFYICONDATAW(ctypes.Structure):
    """Vista 版布局（cbSize 足大即可，字段顺序不可错）。"""
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("hWnd", ctypes.c_void_p),
        ("uID", ctypes.c_uint),
        ("uFlags", ctypes.c_uint),
        ("uCallbackMessage", ctypes.c_uint),
        ("hIcon", ctypes.c_void_p),
        ("szTip", ctypes.c_wchar * 128),
        ("dwState", ctypes.c_ulong),
        ("dwStateMask", ctypes.c_ulong),
        ("szInfo", ctypes.c_wchar * 256),
        ("uVersion", ctypes.c_uint),
        ("szInfoTitle", ctypes.c_wchar * 64),
        ("dwInfoFlags", ctypes.c_ulong),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", ctypes.c_void_p),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p),
        ("lpszClassName", ctypes.c_wchar_p),
    ]


# 窗口过程必须持有强引用，防止被 GC 回收导致崩溃
_WNDPROC_CACHE = []


class Tray:
    """常驻右下角托盘图标 + 右键菜单 + 左键切换显隐。"""

    # 隐藏窗口自己的标题：必须与主窗口标题不同，避免 FindWindowW 按主窗口标题
    # 查找时误命中托盘窗（托盘窗永远不可见，被查到会让「打开/隐藏窗口」失效）。
    _HIDDEN_TITLE = "FlowForgeTrayHidden"
    _CLASS_NAME = "FlowForgeTrayWnd"

    def __init__(self, title="FlowForge", on_open=None, on_hide=None, on_quit=None,
                 on_open_ws=None, on_settings=None, on_autostart=None,
                 autostart_enabled=None):
        self.title = title               # 主窗口标题（用于检测显隐 / 找主窗口）
        self.on_open = on_open or (lambda: None)
        self.on_hide = on_hide or (lambda: None)
        self.on_quit = on_quit or (lambda: None)
        self.on_open_ws = on_open_ws or (lambda: None)
        self.on_settings = on_settings or (lambda: None)
        self.on_autostart = on_autostart or (lambda: None)
        self.autostart_enabled = autostart_enabled or (lambda: False)
        self._hwnd = None                # 只由托盘线程读写
        self._class_atom = None
        self._running = False
        self._menu = None                # 菜单句柄（创建一次复用，退出时统一释放）
        self._menu_built = False
        self._last_menu_ts = 0.0         # 防抖：WM_RBUTTONUP 与 WM_CONTEXTMENU 双通道重复触发
        # 开机自启勾选态缓存：弹出菜单属于高频操作，若每次右键都实时查注册表，
        # 在杀软/系统繁忙时会被拖慢档一到几百毫秒 → 右键明显卡顿。改为带 TTL 缓存。
        self._auto_val = None            # 缓存的开机自启开关状态
        self._auto_ts = 0.0              # 上次查询时间戳（monotonic）
        self._auto_shown = None          # 上次实际写入菜单的勾选态（变化才 ModifyMenuW）

    # ---------------- 原生句柄 ----------------
    def _app_icon(self):
        """获取应用图标句柄：
          - 打包后（frozen）：从 FlowForge.exe 提取自带图标；
          - 源码运行：优先加载项目内 modelflow.ico（否则会显示成 python.exe 的图标）；
          - 全部失败：兜底系统默认应用图标，保证托盘一定有图标。
        """
        if getattr(sys, "frozen", False):
            hicon = ctypes.c_void_p()
            for idx in (0, 1, 2):               # 部分 exe 大图标在第一索引
                n = shell32.ExtractIconExW(sys.executable, idx, ctypes.byref(hicon), None, 1)
                if n >= 1 and hicon.value:
                    return hicon.value
            return user32.LoadIconW(None, IDI_APPLICATION) or 0
        # ---- 源码模式 ----
        try:
            import os as _os
            icon_file = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                      "modelflow.ico")
            if _os.path.exists(icon_file):
                h = user32.LoadImageW(None, icon_file, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
                if h:
                    return h
        except Exception:
            pass
        hicon = ctypes.c_void_p()
        for idx in (0, 1):
            n = shell32.ExtractIconExW(sys.executable, idx, ctypes.byref(hicon), None, 1)
            if n >= 1 and hicon.value:
                return hicon.value
        return user32.LoadIconW(None, IDI_APPLICATION) or 0

    def _create_hidden_window(self):
        WNDPROCTYPE = ctypes.WINFUNCTYPE(
            ctypes.c_longlong, ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_void_p, ctypes.c_void_p)

        def wnd_proc(hwnd, msg, wp, lp):
            try:
                if msg == WM_APP:
                    # 托盘事件码（鼠标消息）在 lParam 低 16 位；wParam 恒为 0
                    self._on_tray_event(self._as_uint(lp))
                    return 0
                if msg == WM_CONTEXTMENU:
                    # 键盘（菜单键/Shift+F10）选择图标快捷菜单时 Shell 发此消息
                    self._show_menu()
                    return 0
                if msg == WM_COMMAND:
                    self._on_command(self._as_uint(wp))
                    return 0
                if _TASKBAR_CREATED and msg == _TASKBAR_CREATED:
                    # explorer 重启：重注册图标，避免图标消失
                    hicon = self._app_icon()
                    if hicon:
                        self._add_icon(hicon)
                    return 0
                if msg == WM_CLOSE:
                    # 由 destroy() 在任意线程 PostMessage 触发，托盘线程内自销
                    self._del_icon()
                    user32.DestroyWindow(hwnd)
                    return 0
                if msg == WM_DESTROY:
                    self._del_icon()
                    user32.PostQuitMessage(0)
                    return 0
                return user32.DefWindowProcW(hwnd, msg, wp, lp)
            except Exception:
                # 任何回调异常都不能让托盘线程挂掉：吞掉并返回 0
                return 0

        proc = WNDPROCTYPE(wnd_proc)
        _WNDPROC_CACHE.append(proc)

        wc = WNDCLASSW()
        wc.lpfnWndProc = ctypes.cast(proc, ctypes.c_void_p)
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.lpszClassName = self._CLASS_NAME
        atom = user32.RegisterClassW(ctypes.byref(wc))
        self._class_atom = atom
        hwnd = user32.CreateWindowExW(
            0, self._CLASS_NAME, self._HIDDEN_TITLE, 0, 0, 0, 0, 0, None, None,
            wc.hInstance, None)
        self._hwnd = hwnd
        return hwnd

    def _add_icon(self, hicon):
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_APP
        nid.hIcon = hicon
        nid.szTip = self.title[:127]
        ok = shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))
        # NOTIFYICON_VERSION_4：Win10 1903+ 若不加会让图标被系统静默丢弃，
        # 且右键/左键按新版规范派发回调；设置失败不影响图标显示，尽力为之。
        if ok:
            v = NOTIFYICONDATAW()
            v.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            v.hWnd = self._hwnd
            v.uID = 1
            v.uVersion = NOTIFYICON_VERSION_4
            shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(v))
        return ok

    def _del_icon(self):
        if not self._hwnd:
            return
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self._hwnd
        nid.uID = 1
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))

    def notify(self, title="", text="", flags=0):
        """弹通知气泡（NIF_INFO）。用于首次启动引导：图标被折叠时提示从 ^ 展开固定。

        失败静默——气泡只是引导，不影响任何功能。
        """
        try:
            if not self._hwnd:
                return False
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = self._hwnd
            nid.uID = 1
            nid.uFlags = NIF_INFO
            nid.szInfoTitle = str(title)[:63]
            nid.szInfo = str(text)[:255]
            nid.dwInfoFlags = flags or NIIF_INFO
            return bool(shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid)))
        except Exception:
            return False

    # ---------------- 托盘交互 ----------------
    @staticmethod
    def _as_uint(v):
        """wParam/lParam 传进来可能是 c_void_p 或 int，统一转低 16 位 uint。"""
        if isinstance(v, ctypes.c_void_p):
            return (v.value or 0) & 0xFFFF
        return (v or 0) & 0xFFFF

    def _on_tray_event(self, code):
        if code in (WM_LBUTTONUP, WM_LBUTTONDBLCLK):
            self.toggle()
        elif code == WM_RBUTTONUP:
            self._show_menu()

    def _debounce_menu(self):
        """NOTIFYICON_VERSION_4 下鼠标右键只走回调（lParam=WM_RBUTTONUP）单通道；
        WM_CONTEXTMENU 仅键盘（菜单键）场景。防抖兜底防极端抖动，正常操作不受影响。
        """
        now = time.monotonic()
        if now - self._last_menu_ts < 0.15:
            return False
        self._last_menu_ts = now
        return True

    def _auto_enabled(self):
        """读取开机自启状态（带 5 秒缓存，避免每次右键都做注册表 I/O）。"""
        now = time.monotonic()
        if self._auto_val is None or (now - self._auto_ts) >= 5.0:
            try:
                self._auto_val = bool(self.autostart_enabled())
            except Exception:
                self._auto_val = False
            self._auto_ts = now
        return self._auto_val

    def toggle(self):
        """左键：窗口当前可见的最小化到托盘，隐藏的则唤出。"""
        hwnd = Tray.detect_hwnd(self.title)
        if hwnd and user32.IsWindowVisible(hwnd):
            self.on_hide()
        else:
            self.on_open()

    def _build_menu(self):
        """创建弹出菜单（可复用：只创建一次，后续仅勾选态变化时更新）。"""
        hmenu = user32.CreatePopupMenu()
        user32.AppendMenuW(ctypes.c_void_p(hmenu), MF_STRING, IDM_SHOW, "打开窗口")
        user32.AppendMenuW(ctypes.c_void_p(hmenu), MF_STRING, IDM_HIDE, "隐藏窗口")
        user32.AppendMenuW(ctypes.c_void_p(hmenu), MF_SEPARATOR, 0, None)
        user32.AppendMenuW(ctypes.c_void_p(hmenu), MF_STRING, IDM_WS, "打开工作区目录")
        user32.AppendMenuW(ctypes.c_void_p(hmenu), MF_STRING, IDM_SETTINGS, "设置")
        self._auto_shown = self._auto_enabled()
        ast = MF_STRING | (MF_CHECKED if self._auto_shown else 0)
        user32.AppendMenuW(ctypes.c_void_p(hmenu), ast, IDM_AUTOSTART, "开机自启")
        user32.AppendMenuW(ctypes.c_void_p(hmenu), MF_SEPARATOR, 0, None)
        user32.AppendMenuW(ctypes.c_void_p(hmenu), MF_STRING, IDM_QUIT, "退出")
        self._menu = ctypes.c_void_p(hmenu)
        self._menu_built = True

    def _show_menu(self):
        if not self._debounce_menu():
            return
        if not self._menu_built:
            self._build_menu()
        else:
            # 「开机自启」勾选态变化时才更新菜单：平时右键零额外开销
            val = self._auto_enabled()          # 读缓存，不落注册表
            if val is not self._auto_shown:
                self._auto_shown = val
                ast = MF_STRING | (MF_CHECKED if val else 0)
                user32.ModifyMenuW(self._menu, IDM_AUTOSTART, ast, IDM_AUTOSTART, "开机自启")
        pt = ctypes.wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self._hwnd)
        user32.TrackPopupMenu(self._menu, TPM_RIGHTBUTTON, pt.x, pt.y, 0, self._hwnd, None)
        user32.PostMessageW(self._hwnd, WM_NULL, 0, 0)

    def _on_command(self, idm):
        if idm == IDM_SHOW:
            self.on_open()
        elif idm == IDM_HIDE:
            self.on_hide()
        elif idm == IDM_WS:
            self.on_open_ws()
        elif idm == IDM_SETTINGS:
            self.on_settings()
        elif idm == IDM_AUTOSTART:
            # 切换后使勾选态缓存立即失效：下次弹菜单立刻重读注册表，保证勾选显示准确
            self._auto_val = None
            self._auto_ts = 0.0
            self._auto_shown = None
            self.on_autostart()
        elif idm == IDM_QUIT:
            self.on_quit()

    # ---------------- 生命周期 ----------------
    def start(self):
        if self._running:
            return
        self._running = True
        # 建窗与消息循环必须在同一线程：Windows 窗口消息只投递到创建窗口的线程
        threading.Thread(target=self._bootstrap, name="tray", daemon=True).start()

    def _bootstrap(self):
        h = self._create_hidden_window()
        if not h:
            self._running = False
            return
        try:
            self._build_menu()           # 预建右键菜单：每次右键秒开，无需现场建
        except Exception:
            self._menu_built = False
        hicon = self._app_icon()
        if hicon:
            self._add_icon(hicon)
        self._message_loop()

    def _message_loop(self):
        msg = ctypes.wintypes.MSG()
        while self._running:
            r = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if r in (0, -1):
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        # 循环退出（收到 WM_QUIT）：窗口已销毁，此时可安全注销窗口类
        if self._class_atom:
            user32.UnregisterClassW(self._CLASS_NAME, kernel32.GetModuleHandleW(None))
        self._class_atom = None

    def destroy(self):
        """任意线程可调用：发 WM_CLOSE 让托盘线程自己销毁窗口并退出消息循环。"""
        self._running = False
        h = self._hwnd
        if h:
            try:
                user32.PostMessageW(h, WM_CLOSE, 0, 0)
            except Exception:
                pass
        self._hwnd = None
        if self._menu:
            try:
                user32.DestroyMenu(self._menu)
            except Exception:
                pass
            self._menu = None
            self._menu_built = False

    @staticmethod
    def detect_hwnd(title):
        return user32.FindWindowW(None, title) or 0