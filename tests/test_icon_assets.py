# -*- coding: utf-8 -*-
"""图标资产本身的清晰度契约。

这些是"图标看着发虚"真正的守门条件：ico 少了某一档，Windows 在 150% 缩放下
就会拿 32 强缩成 24；黑底白字标的竖笔一旦掉到 2 列以下，任务栏上先没的就是它。
两者都不会被别的测试碰到。
"""
import io
import struct
from pathlib import Path

import pytest

Image = pytest.importorskip("PIL.Image")

BASE = Path(__file__).resolve().parents[1]
ASSETS = BASE / "assets"
STATIC = BASE / "static"

# 20/24/40 是给 125%/150%/175% 缩放用的，缺哪一档哪一档就是系统帮你硬缩
ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]


def _frames():
    data = (ASSETS / "loom.ico").read_bytes()
    count = struct.unpack("<H", data[4:6])[0]
    out = {}
    for i in range(count):
        o = 6 + i * 16
        w, h, _cc, _r, _pl, bpp, size, off = struct.unpack("<BBBBHHII", data[o:o + 16])
        payload = data[off:off + size]
        slot = w or 256
        img = Image.open(io.BytesIO(payload)).convert("RGBA")
        out[slot] = (img, payload, bpp)
    return out


def test_ico_declares_every_size_it_actually_carries():
    frames = _frames()
    assert sorted(frames) == ICO_SIZES, (
        f"ico 档位不对，缺的会被系统强行缩放：{set(ICO_SIZES) ^ set(frames)}")
    for slot, (img, payload, bpp) in frames.items():
        assert img.size == (slot, slot), f"{slot}x{slot} 槽里装的是 {img.size}"
        assert bpp == 32, f"{slot}x{slot} 不是 32 位"
        assert payload[:8] == b"\x89PNG\r\n\x1a\n", f"{slot}x{slot} 不是 PNG 载荷"


@pytest.mark.parametrize("n", [16, 20, 24, 32, 40])
def test_small_marks_read_as_an_l(n):
    """黑底白字标在任务栏上的可读条件：竖笔至少 2 列、横脚至少是竖笔的两倍宽、
    记号高度占画面一半以上，而且竖笔与横脚左端对齐（否则就成了 T 或 I）。
    缩略图糊掉通常不是"认不出是 L"，而是竖笔先没 —— 所以盯的是最窄那一行。"""
    px = _frames()[n][0].load()

    def light(x, y):
        r, g, b, a = px[x, y]
        return a >= 40 and r > 200 and g > 200 and b > 200

    rows = [[x for x in range(n) if light(x, y)] for y in range(n)]
    glyph = [r for r in rows if r]
    assert len(glyph) >= n * 0.5, f"{n}px 上记号只占 {len(glyph)} 行高，太小了"
    stem = min(len(r) for r in glyph)
    foot = max(len(r) for r in glyph)
    assert stem >= 2, f"{n}px 竖笔只有 {stem} 列，任务栏上会先没"
    assert foot >= stem * 2, f"{n}px 横脚 {foot} 列 / 竖笔 {stem} 列，读不出是 L"
    assert glyph[0][0] == glyph[-1][0],         f"{n}px 竖笔左端 {glyph[0][0]} 与横脚左端 {glyph[-1][0]} 不齐"


def test_small_favicons_are_exported_for_the_browser_tab():
    """16/32 的 PNG 兜底必须在，标签页那格矢量原图会糊。"""
    for name in ("favicon-16.png", "favicon-32.png"):
        p = STATIC / name
        assert p.is_file(), f"缺 {p}，先跑 make_icon.py"
        img = Image.open(p)
        n = int(p.stem.split("-")[1])
        assert img.size == (n, n)


def test_sidebar_logo_is_the_small_variant_not_the_master():
    """侧栏那格只有 20 CSS px，必须指向小尺寸变体。"""
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "logo-sm.svg" in html
    assert (STATIC / "logo-sm.svg").is_file(), "先跑 make_icon.py 生成 logo-sm.svg"


def test_generated_small_svg_matches_the_snapped_table():
    """logo-sm.svg 必须跟 SMALL[20] 同源，改了一头另一头不许偷偷漂。"""
    import make_icon

    svg = (STATIC / "logo-sm.svg").read_text(encoding="utf-8")
    g = make_icon.SMALL[20]
    for x0, y0, x1, y1 in (g["stem"], g["foot"]):
        frag = f'<rect x="{x0}" y="{y0}" width="{x1 - x0 + 1}" height="{y1 - y0 + 1}" fill="#FFFFFF"/>'
        assert frag in svg, f"logo-sm.svg 与 SMALL[20] 漂了，缺：{frag}"
