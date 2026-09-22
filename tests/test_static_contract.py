# -*- coding: utf-8 -*-
"""静态资产契约：双语字典对齐、CSS 变量有定义、圆角只走角色刻度。

这三条本次会话靠一次性脚本临时验过，回归靠肉眼守不住。
"""
import json
import re
from pathlib import Path

import pytest

from conftest import STATIC_DIR

JS_FILES = sorted(STATIC_DIR.glob("*.js"))
UI_JS = (STATIC_DIR / "ui.js").read_text(encoding="utf-8")
CSS = re.sub(r"/\*.*?\*/", "", (STATIC_DIR / "style.css").read_text(encoding="utf-8"), flags=re.S)

KEY_RE = re.compile(r"'([A-Za-z0-9._-]+)'\s*:")


def _dict_block(lang: str) -> str:
    m = re.search(rf"\n  {lang}: \{{\n(.*?)\n  \}},\n", UI_JS, re.S)
    assert m, f"ui.js 里找不到 {lang} 字典块"
    return m.group(1)


@pytest.fixture(scope="module")
def dicts():
    return set(KEY_RE.findall(_dict_block("zh"))), set(KEY_RE.findall(_dict_block("en")))


def test_zh_en_keys_match(dicts):
    zh, en = dicts
    assert zh - en == set(), f"这些 key 只有中文有翻译：{sorted(zh - en)}"
    assert en - zh == set(), f"这些 key 只有英文有翻译：{sorted(en - zh)}"


def _used_keys():
    """扫所有 JS 里的 t('x.y')；拼接出来的前缀（t('run.lg'+k)）单独登记。"""
    exact, prefixes = set(), set()
    for f in JS_FILES:
        src = re.sub(r"//[^\n]*", "", f.read_text(encoding="utf-8"))
        for m in re.finditer(r"(?<![A-Za-z0-9_$])t\(\s*'([^']+)('?\s*\+)", src):
            (prefixes if m.group(2).startswith("'") and m.group(2)[1:].strip().startswith("+")
             else exact).add(m.group(1))
        for m in re.finditer(r"(?<![A-Za-z0-9_$])t\(\s*'([^']+)'\s*[,)]", src):
            exact.add(m.group(1))
    return exact, {p for p in prefixes if p not in exact}


KEYISH = re.compile(r"'([a-z][a-z0-9]*(?:\.[A-Za-z0-9_]+)+)'")
# 长得很像 i18n key、其实不是的字符串（codex 事件类型等）。新增要写明理由。
NOT_KEYS = {
    "item.completed", "thread.started", "turn.started", "turn.completed", "turn.failed",
    "run.lg",                      # t('run.lg'+Kind) 的动态前缀
}


def _keyish_literals():
    """所有裸字面量里像 key 的。t(a?'x.y':'x.z') 这种三元里的键，
    只扫 t('...') 会漏 —— 上一轮就是这样误删了 sb.tagBuiltin / sb.tagMine。"""
    out = set()
    for f in JS_FILES + [STATIC_DIR / "index.html"]:
        if f.name == "ui.js":
            continue
        out |= set(KEYISH.findall(f.read_text(encoding="utf-8")))
    return out


def test_no_untranslated_key_reaches_the_page(dicts):
    """页面上任何被当作文案取的字符串，字典里都得有；否则 UI 会直接印出 key。"""
    zh, _ = dicts
    stray = _keyish_literals() - zh - NOT_KEYS
    assert stray == set(), f"这些字符串像 key 但字典里没有，会原样显示：{sorted(stray)}"


def test_every_used_key_exists(dicts):
    zh, _ = dicts
    exact, prefixes = _used_keys()
    missing = {k for k in exact if k not in zh}
    assert not missing, f"用到但字典里没有：{sorted(missing)}"
    for p in sorted(prefixes):
        assert any(k.startswith(p) for k in zh), f"动态前缀 {p} 在字典里一个 key 都没有"


def test_no_dead_key_outside_allowlist(dicts):
    """字典里留了没人用的 key：加条目前先想清楚是不是真的需要文案。
    判定必须并上 _keyish_literals()，不然三元里的引用会被当成死键删掉。"""
    zh, _ = dicts
    exact, prefixes = _used_keys()
    used = (exact | _keyish_literals()
            | {k for k in zh if any(k.startswith(p) for p in prefixes)})
    dead = zh - used
    assert dead == set(), f"字典里再没人用的 key：{sorted(dead)}"


# ---------------- CSS ----------------

def test_every_used_css_var_is_defined():
    defined = set(re.findall(r"(--[\w-]+)\s*:", CSS))
    # 带兜底值的 var(--x, fallback) 允许不在 CSS 里定义：那是 JS 运行时写进来的
    # （如更新胶囊的 --p 进度），缺了也只是走兜底，不会破样式。
    used = set(re.findall(r"var\((--[\w-]+)\)(?!\s*,)", CSS))
    assert used - defined == set(), f"用了没定义的变量：{sorted(used - defined)}"


def test_t_lookup_keeps_intentionally_empty_strings():
    """有些描述是故意留空的（某些分区不要副标题）。用 || 取字典会把空串
    当成缺失，直接把 'set.appearanceD' 这种 key 吐到页面上。"""
    body = re.search(r"function t\(key, params\) \{(.*?)\n\}", UI_JS, re.S)
    assert body, "找不到 t() 实现"
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", body.group(1), flags=re.S)
    assert "||" not in code, "t() 又用 || 取字典了，空文案会被渲染成 key 本身"


def test_no_hardcoded_hex_outside_token_blocks():
    """颜色一律走 var()，否则深色模式必破；只有 :root / html[data-*] 里能写字面色。"""
    bad, in_tokens = [], False
    for ln in CSS.splitlines():
        s = ln.strip()
        if s.endswith("{"):
            head = s[:-1].strip()
            in_tokens = head.startswith(":root") or head.startswith("html[")
        elif s == "}":
            in_tokens = False
        elif not in_tokens and re.search(r"#[0-9a-fA-F]{3,8}\b", s):
            bad.append(s[:80])
    assert not bad, f"这些规则写死了色值，切主题会破：{bad[:6]}"


RADIUS_SCALE = {"--r-1", "--r-2", "--r-3", "--r-4", "--r-5", "--r-pill"}


FONT_CSS = (STATIC_DIR / "fonts" / "fonts.css").read_text(encoding="utf-8")
# 八档：micro/meta/sub/body/lead + 两个展示档 + 数据大字。曾经还有 --fs-h3，
# 唯一的用户是列表页 .page-head h1，那整块早没人引用了，删掉后这一档就空了 ——
# 刻度上留一个没人站的格子，只会被下一个人随手填个新数值。
# --fs-stat 是这一轮按参考图像素量出来的（统计条那排数字字高 ≈20px）：
# lead 14.3 太小、h2 23.4 太大，只有 .st-strip b 用着。
FS_TOKENS = {"micro", "meta", "sub", "body", "lead", "h2", "h1", "stat"}


def test_font_faces_declare_one_standard_weight_each():
    """@font-face 里重复写 font-weight 时后一条生效。MiSans 子集原本先写 400
    再写原生的 330，结果全站正文都掉进 Demibold 字面、600/650/700 全挤成 Bold，
    英文看着就发糊。四档必须正好是 400/500/600/700。"""
    rules = re.findall(r"@font-face\s*\{(.*?)\}", FONT_CSS, re.S)
    assert rules, "没读到 @font-face"
    weights = []
    for r in rules:
        ws = re.findall(r"font-weight\s*:\s*([\d.]+)", r)
        assert len(ws) == 1, f"有条规则写了 {len(ws)} 个 font-weight：{ws}"
        weights.append(ws[0])
    assert set(weights) == {"400", "500", "600", "700"}, f"字面档位不对：{sorted(set(weights))}"


def test_css_never_asks_for_an_undeclared_weight():
    """请求一个没声明的字重会走 CSS 的字重匹配算法，结果反直觉
    （要 400 会给 450），所以 style.css 里只准出现已声明的四档。"""
    declared = {float(x) for x in re.findall(r"@font-face\s*\{[^}]*?font-weight\s*:\s*([\d.]+)",
                                             FONT_CSS, re.S)}
    used = {float(x) for x in re.findall(r"font-weight\s*:\s*(\d+)", CSS)}
    assert used <= declared, f"用了没声明的字重：{sorted(used - declared)}"


def test_font_sizes_go_through_the_scale():
    """字号只准取 --fs-* 那 8 档；em 是相对父级、clamp 是展示标题，另算。"""
    used, bare = set(), []
    for m in re.finditer(r"font-size\s*:\s*([^;}]+)", CSS):
        val = m.group(1).strip()
        used |= set(re.findall(r"var\((--fs-[\w-]+)\)", val))
        if re.fullmatch(r"[0-9.]+rem", val):
            bare.append(val)
    assert used <= {f"--fs-{k}" for k in FS_TOKENS}, f"字号令牌不在刻度里：{sorted(used)}"
    assert not bare, f"又出现了裸 rem 字号，请归到 var(--fs-*)：{bare[:8]}"


def test_every_fs_token_is_defined_and_used():
    defined = set(re.findall(r"(--fs-[\w-]+)\s*:", CSS))
    used = set(re.findall(r"var\((--fs-[\w-]+)\)", CSS))
    assert defined == {f"--fs-{k}" for k in FS_TOKENS}, f"档位定义不齐：{sorted(defined)}"
    assert defined - used == set(), f"定义了却没人用的档位：{sorted(defined - used)}"


def test_mono_font_mode_actually_starts_monospace():
    """等宽档若把 MiSansWeb 排在最前，拉丁字母就永远轮不到等宽字体。"""
    mono = re.search(r'html\[data-font="mono"\]\s*\{\s*--font-ui\s*:\s*([^;]+);', CSS)
    assert mono, "找不到等宽档"
    assert mono.group(1).strip().startswith("var(--font-mono)"), mono.group(1).strip()


def test_slider_readout_shares_the_css_root_size():
    """滑块读数说「13px」是从 CSS 的 1rem 基准换算来的。
    基准改了不改常量，读数就一直在报一个界面上不存在的字号。"""
    m = re.search(r"html\{font-size:calc\((\d+(?:\.\d+)?)px \* var\(--text-scale\)\)", CSS)
    assert m, "html 的 font-size 不再是 calc(<n>px * var(--text-scale))，读数逻辑得一起改"
    j = re.search(r"const ROOT_PX = (\d+(?:\.\d+)?);", APP_JS)
    assert j, "app.js 里找不到 ROOT_PX 常量"
    assert float(m.group(1)) == float(j.group(1)), f"CSS {m.group(1)}px ≠ JS {j.group(1)}"


def test_appearance_controls_read_from_the_option_maps():
    """滑块的档位、APP 的当前值、落盘的键名三处同名。改了任一处而没改另两处，
    滑块会静默停在 0 档，或者拖了却没人存。"""
    for key, table in (("textSize", "TEXT_SIZES"), ("uiZoom", "ZOOMS"), ("contentWidth", "WIDTHS")):
        assert f"{key}: () => Object.keys(window.AP_OPTS.{table})" in APP_JS, f"{key} 滑块没走 {table}"
        assert f"'{key}'" in UI_JS, f"loadAppearance 的白名单里没有 {key}"
    for key in ("THEMES", "ACCENTS"):
        assert f"window.AP_OPTS.{key}.map" in APP_JS, f"{key} 磁贴/色板没走 AP_OPTS"


APP_JS = (STATIC_DIR / "app.js").read_text(encoding="utf-8")
INDEX_HTML = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

# 路由 view -> 该高亮哪个导航项。曾经 pipelines / pipeline-edit 还写着 'home'
# （那是「工作流」还没独立成导航项时的遗留），点进去高亮就停在工作台。
NAV_OF_VIEW = {
    "skills": "skills", "skill-edit": "skills",
    "pipelines": "pipelines", "pipeline-edit": "pipelines",
    "runs": "runs", "run": "runs",
    "settings": "settings",
}


def test_router_highlights_the_matching_nav_item():
    calls = dict(re.findall(r"view==='([\w-]+)'\)\s*await run\([^,]+,\s*'([\w-]+)'\)", APP_JS))
    wrong = {v: (calls.get(v), want) for v, want in NAV_OF_VIEW.items() if calls.get(v) != want}
    assert not wrong, f"路由高亮键不对 {wrong}"
    # 只认导航项那种三件套；下拉框配置（ffSelect 的 {id, icon, onChange}）同形不同职
    nav_ids = set(re.findall(r"\{id:'([\w-]+)',\s*icon:'[\w-]+',\s*label:t\('nav\.", APP_JS))
    assert nav_ids == {"pipelines", "skills", "runs"}, f"导航项变了：{nav_ids}"
    # 工作台已删（和「新建任务」弹层重复）；旧链接 #/home 由路由兜到工作流
    assert "home" not in nav_ids, "工作台不该再是导航项"
    assert "renderHome" not in APP_JS, "工作台的渲染代码还在"
    stray = set(calls.values()) - nav_ids - {"settings"}
    assert stray == set(), f"高亮键指向了不存在的导航项：{sorted(stray)}"


def test_every_settings_section_has_a_subtitle_key():
    """页头副标题走的是 t('set.'+id+'D') 这种拼接键 —— 宽前缀让
    test_every_used_key_exists 恒过（'set.' 当然有 key），缺哪一条就只会
    在界面上把原始键名印出来。这里按分区清单逐个点名，堵住这个口径。"""
    zh, en = _dict_block("zh"), _dict_block("en")
    ids = re.findall(r"\['([\w-]+)',\s*'set\.", APP_JS)
    assert ids, "没从 SET_SECTIONS 里解析出分区 id"
    for i in sorted(set(ids)):
        assert f"'set.{i}D'" in zh, f"分区 {i} 没有 set.{i}D，页头会印出原始键名"
        assert f"'set.{i}D'" in en, f"分区 {i} 的英文副标题缺失"


def test_settings_is_not_duplicated_in_the_main_nav():
    """设置只有一个入口：左下角那一行弹层里的「设置」。外层齿轮按钮已撤，
    同一格现在归更新胶囊。"""
    items = re.search(r"const items = \[(.*?)\];", APP_JS, re.S).group(1)
    assert "id:'settings'" not in items, "主导航里又加回设置了，和左下角入口重复"
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "sbSettingsBtn" not in html, "外层设置按钮又回来了"
    assert "sbUpdate" in html, "左下角那一格应该留给更新胶囊"
    assert "nav.go('settings')" in APP_JS, "弹层里的设置入口没了"


def test_border_radius_only_uses_the_scale():
    used, literal = set(), []
    for m in re.finditer(r"border-radius\s*:\s*([^;}]+)", CSS):
        val = m.group(1)
        used |= set(re.findall(r"var\((--[\w-]+)", val))
        if "var(--" not in val and "50%" not in val:
            literal.append(val.strip()[:60])
    assert used <= RADIUS_SCALE, f"圆角变量不在角色刻度里：{sorted(used - RADIUS_SCALE)}"
    assert not literal, f"圆角写了字面值，请改用 var(--r-*)：{literal[:6]}"


def test_no_class_in_markup_without_a_rule():
    """模板里写了个 CSS 没有的类名，页面不会报错，只会静默少一层样式 ——
    本次就是这样写出过一个 .pl-row-sub，量出来字号还是正文 13px。
    只认完整的字面量片段（${} 抠掉、结尾带连字符的丢掉），宁可漏报不误报。"""
    used = set()
    for f in JS_FILES + [STATIC_DIR / "index.html"]:
        for m in re.finditer(r'class="([^"]*)"', f.read_text(encoding="utf-8")):
            v = re.sub(r"\$\{[^{}]*\}", " ", m.group(1))
            used |= {t for t in v.split() if re.fullmatch(r"[a-zA-Z][\w-]*[a-zA-Z0-9]", t)}
    defined = set(re.findall(r"\.([a-zA-Z][\w-]*)", CSS))
    missing = used - defined
    assert not missing, f"这些类名在 style.css 里没有规则：{sorted(missing)}"


def test_no_static_inline_typography_or_spacing():
    """字号/内边距写进 style="" 就绕过了刻度和令牌测试（.85rem 这种就是这么漏掉的）。
    动态算出来的宽度（style="width:${pct}%"）不在此列。"""
    bad = []
    for f in JS_FILES:
        for m in re.finditer(r'style="([^"]*)"', f.read_text(encoding="utf-8")):
            if re.search(r"(font-size|padding|margin|line-height|color|border-radius)\s*:", m.group(1)):
                bad.append(f"{f.name}: {m.group(0)[:60]}")
    assert not bad, f"这些内联样式该落到 class 上：{bad}"


def test_font_sizes_have_a_readable_floor():
    """1rem = 13px，0.72rem 已经到 9.4px，再小就是给视力好的程序员设计的。"""
    small = [m.group(1) for m in re.finditer(r"font-size\s*:\s*([0-9.]+)rem", CSS)
             if float(m.group(1)) < 0.72]
    assert not small, f"这些字号小到读不动：{small}"


@pytest.mark.parametrize("name", ["logo.svg", "favicon.svg"])
def test_brand_svg_is_self_contained(name):
    svg = (STATIC_DIR / name).read_text(encoding="utf-8")
    assert svg.lstrip().startswith("<svg")
    assert "currentColor" not in svg, "图标 SVG 不能依赖 currentColor，<img> 里不生效"
    for gid in re.findall(r"url\(#([\w-]+)\)", svg):
        assert f'id="{gid}"' in svg, f"{name} 引用了不存在的渐变 {gid}"


# ---------------- 侧栏折叠轨道 ----------------

RAIL_HIDDEN = {
    ".sb-name": "侧栏品牌字", ".sb-new span": "新建任务", ".sb-item span": "主导航",
    ".sb-group>span": "分组标题", ".sb-gcount": "在跑计数",
    ".sb-gadd": "分组加号（和顶栏创建流程重复，轨道里两个加号分不清）",
    ".sb-garch": "归档切换（图标按钮，56px 轨道里和加号挤成一行）",
    ".sb-more": "行菜单（图标按钮，轨道里整行只剩一个图标）",
    ".sb-rname": "行标题",
    ".sb-rtag": "行右侧标签", ".sb-empty": "空态文案", ".sb-me-name": "引擎名",
    ".sb-me-chev": "齿轮后的箭头", ".sb-up-tx": "更新胶囊文字",
    ".sb-group:has(+ .sb-empty)": "空分组（轨道里只剩一条孤线，是噪声）",
}


def _rail_block():
    m = re.search(r"@media \(min-width:861px\)\{(.*?)\n\}", CSS, re.S)
    assert m, "找不到折叠轨道那一段（改动请连同本测试一起想清楚）"
    return m.group(1)


def test_rail_hides_every_text_label():
    """轨道只有 56px，任何没藏起来的文字都会把侧栏撑破或自己被打断。
    双向锁：藏多了（那个类已经不存在了）也算漂移。"""
    block = _rail_block()
    hidden = set()
    for sels in re.findall(r"([^{}]*)\{display:none\}", block):
        for s in sels.split(","):
            s = re.sub(r'^\s*html\[data-sidebar="collapsed"\]\s*', "", s.strip())
            if s:
                hidden.add(s)
    missing = {k: v for k, v in RAIL_HIDDEN.items() if k not in hidden}
    assert not missing, f"折叠时这些文字没藏：{missing}"
    extra = hidden - set(RAIL_HIDDEN)
    assert not extra, f"轨道藏了清单外的类，请一并更新清单：{sorted(extra)}"


def test_rail_state_is_persisted_through_the_appearance_channel():
    """折叠态走的是 ui_ 外观通道。少一环就变成「重启回到展开」或「按了没反应」。"""
    assert "ui_sidebar:'sidebar'" in INDEX_HTML, "启动预取没读 ui_sidebar，会闪一下全宽侧栏"
    assert "document.documentElement.dataset.sidebar" in INDEX_HTML, "启动时没落 data-sidebar"
    assert "html.dataset.sidebar" in UI_JS, "applyAppearance 不落 data-sidebar"
    assert "'sidebar'" in UI_JS, "loadAppearance 的回退清单里没有 sidebar"
    assert "sidebar: 'expanded'" in UI_JS, "APP 缺 sidebar 默认值"
    assert "setAppearance({sidebar:" in APP_JS, "sbToggle 没把折叠态写回设置"


def test_rail_toggle_is_reachable_and_documented():
    """品牌位是 <button> 才谈得上键盘可达；Ctrl B 绑了就得出现在键位说明里。"""
    brand = re.search(r"<(button|a) class=\"sb-brand\"[^>]*>", INDEX_HTML)
    assert brand, "找不到品牌元素"
    assert brand.group(1) == "button", "品牌位用 <a> 没 href，键盘 Tab 到不了"
    assert 'onclick="sbToggle()"' in brand.group(0), "品牌位不再是侧栏开关"
    assert "k==='b'" in APP_JS, "Ctrl B 没绑"
    docs = set(re.findall(r"\['Ctrl (\S+)', t\('(sc\.[A-Za-z]+)'\)", APP_JS))
    bound = {c.lower() for c in re.findall(r"if\(k==='(.)'", APP_JS)}
    assert {k.lower() for k, _ in docs} <= bound, "键位说明里列了没绑的快捷键"
    assert bound <= {k.lower() for k, _ in docs}, "绑了快捷键却没写进键位说明"


def test_tooltip_host_honours_the_hidden_attribute():
    """.ff-tip 自己带 position:fixed，[hidden] 的 UA 规则一旦被 display 覆盖就再也藏不掉。"""
    assert 'id="ffTip"' in INDEX_HTML, "提示节点不在了"
    assert ".ff-tip[hidden]{display:none}" in CSS, "缺 .ff-tip[hidden]，收起可能失效"
    assert "data-tip-any" in APP_JS and "tipWants" in APP_JS, "轨道标签靠 tooltip 补回来"


# 展开态也只剩图标的按钮：没有 data-tip-any 就只在折叠时提示，等于平时没说明
TIP_ANY_IDS = ["sbBrand", "sbSearchBtn", "sbActBtn", "sbUpdate"]


def test_icon_only_buttons_tip_in_both_widths():
    for i in TIP_ANY_IDS:
        tag = re.search(r'<[^>]*id="%s"[^>]*>' % i, INDEX_HTML)
        assert tag, f"找不到 #{i}"
        assert "data-tip-any" in tag.group(0), f"#{i} 只有图标，提示却没标 data-tip-any"
    assert 'class="sb-gadd" data-tip-any="1"' in APP_JS, "分组加号同上"


def test_sidebar_stopped_using_native_title():
    """原生 title 和自研提示并存会出现两套样式、两种延迟，侧栏里只留一套。"""
    side = re.search(r'<aside class="sidebar">.*?</aside>', INDEX_HTML, re.S).group(0)
    assert "title=" not in side, f"侧栏里又用了原生 title：{re.findall(r'[\\w]*title=', side)}"


# ---------------- 内联事件处理器 ----------------

HANDLER_ATTR = re.compile(r"\bon[a-zA-Z]+\s*=\s*\\?[\"']([^\"']*)\\?[\"']")
CALL_HEAD = re.compile(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*[.(]")
# 内联表达式里的关键字，和浏览器塞进作用域的两个宿主名。
# 其余宿主对象（document / window / JSON …）一个都不预先放行：现在没人用，
# 以后谁用谁就地加，条目才不会烂成一串没人信的白名单。
EXPR_WORDS = {"if", "return", "typeof", "catch", "function", "in", "of"}
HOST_GLOBALS = EXPR_WORDS | {"event", "this"}


def _handler_globals():
    """内联 onclick="x()" 里的 x 是浏览器在全局作用域里查的。
    四个脚本各自是 IIFE，没导出到 window 的函数在外面根本不存在 ——
    产出面板那个「刷新」就是这么死的：按钮照画，点一下 ReferenceError，
    而 161 条测试一条都不会红。这里把整条链子焊上。"""
    exported = set()
    for f in JS_FILES:
        exported |= set(re.findall(r"window\.([A-Za-z_$][\w$]*)\s*=",
                                   f.read_text(encoding="utf-8")))
    used = {}
    for f in JS_FILES + [STATIC_DIR / "index.html"]:
        src = f.read_text(encoding="utf-8")
        for m in HANDLER_ATTR.finditer(src):
            # ${...} 在模板串生成时就求过值了，用的是闭包里的局部变量；
            # 处理器真正拿到的是替换后的字面量，不能把它当全局名来查。
            body = re.sub(r"\$\{[^{}]*\}", "", m.group(1))
            for c in CALL_HEAD.finditer(body):
                used.setdefault(c.group(1), set()).add(f.name)
    return exported, used


def test_inline_handlers_only_call_exported_globals():
    exported, used = _handler_globals()
    missing = {k: sorted(v) for k, v in used.items()
               if k not in exported and k not in HOST_GLOBALS}
    assert missing == {}, f"这些内联处理器调的函数没导出到 window：{missing}"


def test_handler_globals_allowlist_is_not_stale():
    """兜底名用上了就是废条目 —— 别让它越积越长，长到没人信。"""
    _, used = _handler_globals()
    stale = {n for n in HOST_GLOBALS if n not in used and n not in EXPR_WORDS}
    assert stale == set(), f"HOST_GLOBALS 里这些名字已经没人用了：{sorted(stale)}"


@pytest.mark.skipif(__import__("shutil").which("node") is None, reason="本机没有 node")
def test_every_static_script_actually_parses():
    """上面那些契约全靠正则扫源码，看不见语法错误。真踩过一次：把 Python 的
    "相邻字符串自动相连"当成 JS 写进字典，设置页整个白屏（t is not a function），
    而几百条测试一条都不红。语法这一关只能交给 JS 引擎自己判。"""
    import subprocess
    for f in JS_FILES:
        r = subprocess.run(["node", "--check", str(f)], capture_output=True, text=True)
        assert r.returncode == 0, f"{f.name} 过不了 node --check：{r.stderr[:400]}"


def test_stats_page_keeps_the_measured_rhythm():
    """这几条是 2026-09-22 对着参考截图逐像素量出来的（图像 px ÷1.5 = CSS px）。
    改回去不会弄坏任何功能，只会悄悄不像 —— 所以只能靠断言钉住。"""
    need = {
        ".st-strip>div{background:var(--bg-panel);padding:9px 10px":
            "顶部条卡上下 9px（整条量到 66，参考 65）",
        ".st-strip span{display:block;margin-top:6px;font-size:var(--fs-body)":
            "数字→标签 6px、标签 13px（参考 13）",
        ".hm-grid{display:flex;gap:3px 2px}":
            "横向节距 14 = 12 格 + 2 缝（参考 14.3），52 列才铺得下还留得住两侧内边距",
        ".hm-axis{display:flex;gap:2px;margin-top:15px}":
            "网格→月份轴 15px，且轴的节距必须跟格子一致，否则轴会逐列偏掉",
        ".hm-wrap{overflow-x:auto;padding:0 18px 2px}":
            "网格与卡片标题同一条左线（18px）",
        ".st-stats .st-block{margin-bottom:19px}":
            "统计页卡片之间 19px（别的分区仍走 28px）",
    }
    for frag, why in need.items():
        assert frag in CSS, f"{why}；这条被改动了：{frag}"


def test_durations_are_localised_in_js_not_hardcoded():
    """中文里 "7h 2m" 读不成一句话，参考图写的是 "7 小时 2 分钟"。
    单位取 unit.* 那几个键，别再退回硬编码的英文字母。"""
    body = re.search(r"function fmtDur\(ms\)\{(.*?)\n\}", APP_JS, re.S)
    assert body, "找不到 fmtDur"
    code = body.group(1)
    for k in ("unit.sec", "unit.min", "unit.hour"):
        assert f"t('{k}')" in code, f"fmtDur 的中文分支不再取 {k}"
    assert "'en'" in code, "英文分支（h/m/s）也得留着"


def test_sidebar_archive_view_always_offers_a_way_back():
    """归档视图里最后一条被取消归档后列表就空了 —— 切换钮要是跟着消失，
    人就困在「已归档」这一栏里出不来（只能刷新页面）。"""
    guard = re.search(r"const garch = \((.*?)\) \?", APP_JS, re.S)
    assert guard, "找不到侧栏归档切换钮的渲染条件"
    cond = guard.group(1)
    assert "SB_ARCH" in cond and "arch.length" in cond, f"条件该是「有归档项 或 正在归档视图」：{cond}"
    assert "sb.archivedEmpty" in APP_JS, "归档空态文案没了"


def test_sidebar_row_menu_matches_the_view_it_is_in():
    """项目视图：查看文件 / 新建任务 / 归档；归档视图：查看文件 / 取消归档 / 删除。
    「删除」只在归档视图里露 —— 先归档再删，两步隔开，正在用的流程不会被一键抹掉。"""
    body = re.search(r"window\.sbRowMore = function\(e, name\)\{(.*?)\n\};", APP_JS, re.S)
    assert body, "找不到 sbRowMore"
    code = body.group(1)
    for k in ("sb.viewFiles", "sb.newTaskHere", "sb.archive", "sb.unarchive", "c.delete"):
        assert f"t('{k}')" in code, f"行菜单少了 {k}"
    assert "ffActionMenu" in code, "行菜单没走公共外壳"
    assert "SB_ARCH" in code, "两套菜单被合成一套了"


def test_action_menu_closes_on_escape_before_the_other_popups():
    """.ff-menu 和侧栏搜索、进程浮层共用一条 Esc 处理链。动作菜单压在别人上面，
    必须第一个吃 Esc —— 顺序反了就会一路按下去把底下的弹窗一起带走。"""
    esc = APP_JS[APP_JS.index("if(e.key==='Escape'){"):]
    order = [m.group(1) for m in re.finditer(r"getElementById\('(ffMenu|sbFind|sbPop)'\)", esc)]
    assert order[:1] == ["ffMenu"], f"Esc 先关的不是动作菜单：{order[:3]}"


def test_archived_flows_stay_visible_in_the_workflows_list():
    """归档只把它们从侧栏那一栏撤走。工作流页要是也跟着藏，人就成了「东西不见了」，
    而且再没有入口把它捞回来 —— 所以行要留着、挂状态牌、⋯ 里给「取消归档」。"""
    ed = (STATIC_DIR / "editor.js").read_text(encoding="utf-8")
    assert "pl-arch-tag" in ed and "t('sb.archived')" in ed, "工作流页不再标已归档"
    assert "plArchive(name, false)" in ed, "工作流页的 ⋯ 少了取消归档"
    assert "plArchive(name, true)" in ed, "工作流页的 ⋯ 少了归档"
    assert ".pl-arch-tag{" in CSS and ".pl-card-row.archived" in CSS, "归档标记没有规则"


def test_menu_labels_that_overrun_get_an_ellipsis_not_a_clip():
    """.ff-mi 是 flex，text-overflow 对裸文本节点（匿名 flex 项）不生效 ——
    长流程名会被硬裁在边框上。标签必须包成 .ff-ml，且 min-width:0 才能收缩。"""
    assert '<span class="ff-ml">${esc(o.label)}</span>' in APP_JS, "菜单标签没包 .ff-ml"
    assert ".ff-mi .ff-ml{min-width:0;overflow:hidden;text-overflow:ellipsis}" in CSS, \
        ".ff-ml 的省略号规则被改动了"


def test_task_modal_checkpoint_hint_follows_the_picked_flow():
    """弹层里换流程，右边那行「含 N 个检查点」必须跟着换 —— 它一开始只按首选项算，
    之后再也不更新，于是显示的是另一条流程的检查点。"""
    body = re.search(r"function tkHint\(\)\{(.*?)\n\}", APP_JS, re.S)
    assert body, "找不到 tkHint"
    assert "tkMeta" in body.group(1), "tkHint 不再刷新检查点提示"
    assert 'id="tkMeta"' in APP_JS, "检查点提示没有挂载点"
    assert "TK_CPS" in APP_JS, "检查点计数表没了"


# ==================== 照参考实现（开源的 zai-org/ZCode）对齐的六条 ====================
# 这几处是 2026-09-22 读到 ZCode 真源码之后改的。以前只能对着截图量像素，
# 量不出"分档怎么算、填格往哪个方向、层级谁压谁"这类行为，所以只能靠断言钉住。

def test_heatmap_buckets_are_peak_relative_and_weeks_fill_bottom_up():
    """分位数分档会让每个轻活日都落在 1~2 档，一整年看过去永远满屏有色，
    恰好抹掉"哪天是我最好的一天"这个信号；周/累计档整列铺同一档也会被读成
    "这周每天都这么多"。所以：档位对峰值取比，填格自下而上。"""
    assert "Math.min(4, Math.max(1, Math.ceil(v / mx * 4)))" in APP_JS, "热力图分档不再按峰值等比"
    assert "Math.ceil(cv / mx * 7)" in APP_JS, "周/累计档不再按峰值算填几格"
    assert "i >= 7 - fill" in APP_JS, "填格方向反了（应当自下而上：周日在顶）"
    for gone in ("q(.25)", "q(.5)", "q(.75)"):
        assert gone not in APP_JS, f"分位数分档又回来了：{gone}"


def test_heatmap_ramp_mixes_in_oklab_into_a_solid_surface():
    """srgb 插值在低百分比上偏灰，四档前密后疏；混 transparent 会让格子随卡片底色变，
    明暗两套下深浅不等价。混进 --bg-sunken（也就是 0 档那格的实色）才接得上。"""
    for pct, n in ((18, 1), (36, 2), (58, 3), (82, 4)):
        frag = f".hm-l{n}{{background:color-mix(in oklab, var(--accent) {pct}%, var(--bg-sunken))}}"
        assert frag in CSS, f"色阶第 {n} 档被改动：{frag}"
    assert "in srgb, var(--accent)" not in CSS, "srgb 混色又回来了"


def test_z_index_goes_through_the_scale_and_orders_menu_on_top():
    """裸数字写 z-index 迟早撞车：以前提示(95)压在菜单(80)上，⋯ 一开，
    上一格留下的提示就糊在菜单第一项上。顺序规定是"正在操作的那层在最上"。"""
    assert CSS.count("z-index:") == CSS.count("z-index:var(--z-"),         "有 z-index 没走 --z-* 刻度"
    tok = dict(re.findall(r"--z-([a-z]+):([0-9]+);", CSS))
    want = ["sticky", "composer", "float", "modal", "toast", "tip", "menu"]
    assert set(tok) == set(want), f"层叠刻度变了：{sorted(tok)}"
    vals = [int(tok[k]) for k in want]
    assert vals == sorted(vals), f"层级顺序不是递增的：{dict(zip(want, vals))}"


def test_row_actions_survive_devices_without_hover():
    """⋯ 和行内按钮原本只认 :hover —— 触屏/平板模式压根没有 hover 这回事，
    等于把动作对这类设备整个藏掉。"""
    assert "@media (hover:none){.sb-more{display:inline-flex}.pl-row-ops{opacity:1}}" in CSS,         "没有 hover 的设备上行内动作不可达"


def test_pinyin_initial_table_actually_resolves():
    """搜索键拼的是"原文 + 首字母"，表错了不会报错、只会搜不到 ——
    所以让 JS 引擎真把表跑一遍，而不是断言那串字符还在。"""
    import subprocess
    js = ("const s=require('fs').readFileSync(process.argv[1],'utf8');"
          "const g=s.match(/const PY_GROUPS = \"([^\"]+)\";/)[1];"
          "const m={};g.split('|').forEach(x=>{const i=x.indexOf(':');"
          "for(const c of x.slice(i+1)) m[c]=x.slice(0,i).toLowerCase();});"
          "const w=JSON.parse(process.argv[2]);"
          "console.log(JSON.stringify(w.map(x=>[...x].map(c=>m[c]||'?').join(''))));")
    words = ["模型", "外观", "语言", "主题", "统计", "设置", "运行", "引擎", "密钥", "归档", "工作流"]
    want = ["mx", "wg", "yy", "zt", "tj", "sz", "yx", "yq", "my", "gd", "gzl"]
    r = subprocess.run(["node", "-e", js, str(STATIC_DIR / "app.js"), json.dumps(words)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[:400]
    assert json.loads(r.stdout) == want, r.stdout[:200]
    # 无 .st-row 的卡靠这份元素清单取标题文案；统计页的卡标题是 .st-pttl，
    # 漏了它这六张卡就对搜索完全隐形（"mxy" 搜不到「模型用量」）。
    frag = "querySelectorAll('.st-label,.hm-title,.spv-title,.st-pttl,.st-t,.st-d')"
    assert frag in APP_JS, f"搜索兜底的标题清单变了：{frag}"


def test_chart_palette_has_six_slots_and_merges_only_past_six():
    """六条模型以内全画 —— 第 7 档没颜色了，但"六条 + 其他"那种只剩一个
    "其他"的图例更难看。合并的触发条件是超过六条，切成 5 具名 + 其他。"""
    assert "const CHART_N = 6;" in APP_JS, "分类色档数变了，--chart-* 得同步"
    assert CSS.count("--chart-6:") == 2, "--chart-6 必须明暗各一份"
    assert ".st-c6{background:var(--chart-6)}" in CSS and ".st-s6{stroke:var(--chart-6)}" in CSS
    assert "rows.length > CHART_N ? CHART_N - 1 : rows.length" in APP_JS,         "合并规则不再是「超过六条才并」"
