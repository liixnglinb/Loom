# -*- coding: utf-8 -*-
"""图标资产本身的清晰度契约。

这些是"图标看着发虚"真正的守门条件：ico 少了某一档，Windows 在 150% 缩放下
就会拿 32 强缩成 24；小尺寸里两只眼睛隔得太近，任务栏上就糊成一条嘴。
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
def test_small_faces_keep_the_two_eyes_apart(n):
    """沿每一行看卡片内部：必须正好挖出两段洞，且中间隔着 >=2 列卡片色。

    只数"有没有暗像素"是不够的 —— 底板本身也是暗的，所以只在卡片两端之间找洞；
    眼距太窄时两段洞仍然在，但中间那段短到读不出是两只眼睛。
    """
    img = _frames()[n][0]
    px = img.load()

    def light(x, y):
        r, g, b, a = px[x, y]
        return a >= 40 and r > 200 and g > 200 and b > 200

    def solid(x, y):
        return px[x, y][3] >= 40

    best = None
    for y in range(n):
        run = [x for x in range(n) if light(x, y)]
        if len(run) < 4:
            continue
        holes = [x for x in range(run[0], run[-1] + 1)
                 if not light(x, y) and solid(x, y)]
        groups, cur = [], []
        for x in holes:
            if cur and x == cur[-1] + 1:
                cur.append(x)
            else:
                if cur:
                    groups.append(cur)
                cur = [x]
        if cur:
            groups.append(cur)
        if len(groups) != 2:
            continue
        left, right = groups
        bridge = right[0] - left[-1] - 1
        if not all(light(x, y) for x in range(left[-1] + 1, right[0])):
            continue
        cand = (bridge, min(len(left), len(right)))
        if best is None or cand > best:
            best = cand
    assert best is not None, f"{n}px 上找不到分得开的两只眼睛"
    bridge, eye_w = best
    assert bridge >= 2, f"{n}px 两眼之间只剩 {bridge} 列，糊成一条嘴了"
    assert eye_w >= 2, f"{n}px 眼睛只有 {eye_w} 列，撑不住"


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
    cx0, cy0, cx1, cy1 = g["card"]
    assert f'<rect x="{cx0}" y="{cy0}" width="{cx1 - cx0 + 1}" height="{cy1 - cy0 + 1}"' in svg
    for box in (g["eye"], g["eye2"]):
        assert f'<rect x="{box[0]}" y="{box[1]}"' in svg
