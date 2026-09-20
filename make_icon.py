# -*- coding: utf-8 -*-
"""生成 assets/loom.ico 与配套 PNG（和 static/logo.svg 同一套几何数值）。

为什么用代码画而不是转 SVG：本机没有 cairosvg / inkscape，而这个图标只有
圆角方块 + 圆 + 渐变四样东西，按 SVG 里的坐标复画比引一个渲染依赖更可控。

小尺寸不是从大图缩出来的。16/20/24 这三档改成按目标像素网格硬对齐来画：
一张 8~11px 的卡里塞两只眼睛，缩放出来的边会落在像素中间，任务栏上就是一团糊的。
每档的圆角、卡片、眼睛、圆点都是各自定过整数的，见 SMALL。
 ICO 一次写 16/20/24/32/40/48/64/128/256 九档 —— 少了 20/24/40，
Windows 在 125%/150%/175% 缩放下就没得挑，只能把 32 强行缩成 24，那才是"图标发虚"的主因。
"""
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
OUT = BASE / "assets"
SIZE = 1024                      # 大图的画布，圆角边缘靠它才不会锯齿
TOP = (0x5B, 0x96, 0xF9)
BOT = (0x2C, 0x62, 0xD6)
LIGHT = (0xF2, 0xF6, 0xFD)

ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]

# 小尺寸全部按整数像素各自定，坐标是 (x0,y0,x1,y1) 闭区间。
# 为什么不一律缩放原几何：两只眼睛在 viewBox 里只差 9/120，缩到 32px 就只剩 2.4px，
# 中间那道"鼻梁"会糊成一整条嘴 —— 小图必须把眼距拉开，这是画法问题不是分辨率问题。
SMALL = {
    16: dict(tile_r=3, card=(2, 6, 10, 14), card_r=2,
             eye=(3, 9, 4, 10), eye2=(8, 9, 9, 10), dot=None),
    20: dict(tile_r=4, card=(2, 7, 13, 18), card_r=3,
             eye=(4, 11, 6, 13), eye2=(9, 11, 11, 13), dot=None),
    24: dict(tile_r=5, card=(3, 9, 15, 21), card_r=4,
             eye=(5, 13, 7, 15), eye2=(11, 13, 13, 15), dot=(17, 4, 21, 8)),
    32: dict(tile_r=7, card=(3, 11, 19, 27), card_r=6,
             eye=(5, 17, 8, 20), eye2=(14, 17, 17, 20), dot=(21, 4, 28, 11)),
    40: dict(tile_r=9, card=(4, 14, 25, 35), card_r=8,
             eye=(7, 22, 11, 26), eye2=(18, 22, 22, 26), dot=(26, 5, 35, 14)),
}


def grad(y: float) -> tuple:
    """按 viewBox 高度（0~120）取渐变颜色，userSpaceOnUse 就是这个语义。"""
    t = max(0.0, min(1.0, y / 120.0))
    return tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOT))


def s(v: float, size: int = SIZE) -> float:
    return v * size / 120.0


def build(size: int = SIZE, samples: int = 4) -> Image.Image:
    """矢量那套几何画在 size 画布上，samples>1 时超采样一次，边缘才是干净的。"""
    ss = size * samples
    img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    strip = Image.new("RGBA", (ss, ss))
    d = ImageDraw.Draw(strip)
    for y in range(ss):
        d.line([(0, y), (ss, y)], fill=grad(y * 120 / ss) + (255,))
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, ss - 1, ss - 1], radius=s(27, ss), fill=255)
    img.paste(strip, (0, 0), mask)

    d = ImageDraw.Draw(img)
    k = size / 120.0
    d.rounded_rectangle([12 * k * samples, 42 * k * samples,
                         (12 + 62) * k * samples, (42 + 62) * k * samples],
                        radius=22 * k * samples, fill=LIGHT + (255,))
    # 眼睛取底色的渐变值，视觉上就是"挖穿"，和 SVG 里 fill=url(#loom) 等价
    hole = grad(71) + (255,)
    for cx in (31, 55):
        d.ellipse([(cx - 7.5) * k * samples, (71 - 7.5) * k * samples,
                   (cx + 7.5) * k * samples, (71 + 7.5) * k * samples], fill=hole)
    d.ellipse([(93 - 13) * k * samples, (27 - 13) * k * samples,
               (93 + 13) * k * samples, (27 + 13) * k * samples], fill=LIGHT + (255,))
    if samples > 1:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def build_snapped(n: int) -> Image.Image:
    """小尺寸：外轮廓可以软（那是跟透明背景交界，本来就该有），里面全部硬边、
    全部落在网格上。缩放原几何会同时毁掉这两件事 —— 轮廓带出一圈灰边，
    五官又全都压在半个像素上。"""
    g = SMALL[n]
    k = 4
    tile = Image.new("RGBA", (n * k, n * k), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.rounded_rectangle([0, 0, n * k - 1, n * k - 1], radius=g["tile_r"] * k, fill=(255, 255, 255, 255))
    strip = Image.new("RGBA", (n * k, n * k))
    sd = ImageDraw.Draw(strip)
    for y in range(n * k):
        sd.line([(0, y), (n * k, y)], fill=grad((y + 0.5) * 120 / (n * k)) + (255,))
    tile.paste(strip, (0, 0), tile.split()[3])
    # 整数倍 BOX 降采样就是纯面积平均，不会像 LANCZOS 那样在轮廓外侧振出一圈灰边
    img = tile.resize((n, n), Image.BOX)
    d = ImageDraw.Draw(img)

    cx0, cy0, cx1, cy1 = g["card"]
    d.rounded_rectangle([cx0, cy0, cx1, cy1], radius=g["card_r"], fill=LIGHT + (255,))
    hole = grad((cy0 + cy1 + 1) / 2 * 120 / n) + (255,)
    for box in (g["eye"], g["eye2"]):
        if box:
            d.rectangle(box, fill=hole)
    if g["dot"]:
        d.ellipse(list(g["dot"]), fill=LIGHT + (255,))
    return img


def render(n: int) -> Image.Image:
    if n in SMALL:
        return build_snapped(n)
    # 64 起五官有六七个像素可给，回到矢量那套几何，圆角也才够十几级
    return build(n, samples=2 if n >= 64 else 1)


def svg_snapped(n: int) -> str:
    """把 SMALL[n] 那套整数几何写成 SVG —— 侧边栏那颗只有 20 CSS px，
    在 150% 缩放下也就 30 个设备像素，矢量原图 9/120 的眼距会被糊成一条嘴。
    大图那套原样留在 logo.svg / loom-256.png，这里只是同一张脸的小尺寸版本。"""
    g = SMALL[n]
    cx0, cy0, cx1, cy1 = g["card"]
    eyes = [b for b in (g["eye"], g["eye2"]) if b]
    hole = grad((cy0 + cy1 + 1) / 2 * 120 / n)
    body = [
        f'<rect width="{n}" height="{n}" rx="{g["tile_r"]}" fill="url(#loom)"/>',
        f'<rect x="{cx0}" y="{cy0}" width="{cx1 - cx0 + 1}" height="{cy1 - cy0 + 1}"'
        f' rx="{g["card_r"]}" fill="#F2F6FD"/>',
    ]
    for x0, y0, x1, y1 in eyes:
        w, h = x1 - x0 + 1, y1 - y0 + 1
        body.append(f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}"'
                    f' rx="{min(w, h) // 2}" fill="rgb{hole}"/>')
    if g["dot"]:
        x0, y0, x1, y1 = g["dot"]
        body.append(f'<circle cx="{(x0 + x1 + 1) / 2:g}" cy="{(y0 + y1 + 1) / 2:g}"'
                    f' r="{(x1 - x0 + 1) / 2:g}" fill="#F2F6FD"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="{0}" height="{0}" viewBox="0 0 {0} {0}">'
            '<defs><linearGradient id="loom" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{0}">'
            '<stop offset="0" stop-color="#5B96F9"/><stop offset="1" stop-color="#2C62D6"/>'
            '</linearGradient></defs>' + "\n".join(body) + '</svg>').replace("{0}", str(n))


def main() -> int:
    OUT.mkdir(exist_ok=True)
    big = build()
    big.save(OUT / "loom-1024.png")
    for n, name in ((256, "loom-256.png"), (64, "logo-64.png"), (48, "favicon-48.png")):
        render(n).save(OUT / name)
    for n in (16, 24, 32):
        render(n).save(OUT / f"favicon-{n}.png")
    # 浏览器标签页那 16/32 也从这里出：static/favicon.svg 在 150% 缩放下
    # 只有约 24 个设备像素，矢量那套眼距会糊成一整条嘴，得给 PNG 兜底。
    static = BASE / "static"
    for n in (16, 32):
        render(n).save(static / f"favicon-{n}.png")
    (static / "logo-sm.svg").write_text(svg_snapped(20), encoding="utf-8")

    frames = [render(n) for n in ICO_SIZES]
    head = struct.pack("<HHH", 0, 1, len(frames))
    body, offset = b"", 6 + 16 * len(frames)
    for n, fr in zip(ICO_SIZES, frames):
        import io
        buf = io.BytesIO()
        fr.save(buf, format="PNG", optimize=True)
        data = buf.getvalue()
        head += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32,
                            len(data), offset)
        body += data
        offset += len(data)
    (OUT / "loom.ico").write_bytes(head + body)

    for f in sorted(OUT.iterdir()):
        print(f"{f.name:18s} {f.stat().st_size/1024:6.1f} KB")
    print("ico 内各档:", " ".join(f"{n}" for n in ICO_SIZES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
