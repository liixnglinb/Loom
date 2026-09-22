# -*- coding: utf-8 -*-
"""生成 assets/loom.ico 与配套 PNG（和 static/logo.svg 同一套几何数值）。

为什么用代码画而不是转 SVG：本机没有 cairosvg / inkscape，而这个图标只有
圆角方块 + 两个矩形，按 SVG 里的坐标复画比引一个渲染依赖更可控。

小尺寸不是从大图缩出来的。16/20/24/32/40 各自按目标像素网格硬对齐来画：
一根 2px 的笔画缩到半像素上，任务栏里就是一条灰边。每档的圆角和笔画宽度
都是各自定过整数的，见 SMALL。
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
# 黑底 + 白字标 L。底不是纯黑而是极浅的自上而下渐变：纯 #000 压在深色任务栏上
# 会整颗消失，留一点顶亮底暗才有边界。
TOP = (0x1F, 0x1F, 0x1F)
BOT = (0x00, 0x00, 0x00)
LIGHT = (0xFF, 0xFF, 0xFF)
# 母版几何（viewBox 120）：竖笔 + 横脚两个矩形拼，交集处重叠不会露缝
STEM = (34, 26, 50, 94)
FOOT = (34, 78, 88, 94)

ICO_SIZES = [16, 20, 24, 32, 40, 48, 64, 128, 256]

# 小尺寸全部按整数像素各自定，坐标是 (x0,y0,x1,y1) 闭区间。
# 为什么不一律缩放原几何：16px 上母版那 14/120 的笔画只剩 1.87px，落在半个像素上，
# 任务栏里就是一条灰边。每一档的笔画都取整数（16/20 用 2px，24 用 3px，32/40 用 5~6px），
# 并且让 L 的包围盒在画布里光学居中（L 左重，所以整体比几何中心略偏右）。
SMALL = {
    16: dict(tile_r=3, stem=(4, 3, 5, 12), foot=(4, 11, 12, 12)),
    20: dict(tile_r=4, stem=(5, 4, 7, 16), foot=(5, 14, 15, 16)),
    24: dict(tile_r=5, stem=(6, 4, 9, 19), foot=(6, 16, 18, 19)),
    32: dict(tile_r=7, stem=(9, 6, 13, 26), foot=(9, 22, 24, 26)),
    40: dict(tile_r=9, stem=(11, 7, 17, 33), foot=(11, 28, 30, 33)),
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
    k = size / 120.0 * samples
    for x0, y0, x1, y1 in (STEM, FOOT):
        d.rectangle([x0 * k, y0 * k, x1 * k - 1, y1 * k - 1], fill=LIGHT + (255,))
    if samples > 1:
        img = img.resize((size, size), Image.LANCZOS)
    return img


def build_snapped(n: int) -> Image.Image:
    """小尺寸：外轮廓可以软（那是跟透明背景交界，本来就该有），里面全部硬边、
    全部落在网格上。缩放原几何会同时毁掉这两件事 —— 轮廓带出一圈灰边，
    笔画又全都压在半个像素上。"""
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
    for box in (g["stem"], g["foot"]):
        d.rectangle(box, fill=LIGHT + (255,))
    return img


def render(n: int) -> Image.Image:
    if n in SMALL:
        return build_snapped(n)
    # 64 起五官有六七个像素可给，回到矢量那套几何，圆角也才够十几级
    return build(n, samples=2 if n >= 64 else 1)


def svg_snapped(n: int) -> str:
    """把 SMALL[n] 那套整数几何写成 SVG —— 侧边栏那颗只有 20 CSS px，标签页那档
    在 150% 缩放下约 24 个设备像素，缩放母版会让笔画落在半个像素上。
    大图那套原样留在 logo.svg，这里只是同一个记号的小尺寸版本。"""
    g = SMALL[n]
    body = [f'<rect width="{n}" height="{n}" rx="{g["tile_r"]}" fill="url(#loom)"/>']
    for x0, y0, x1, y1 in (g["stem"], g["foot"]):
        body.append(f'<rect x="{x0}" y="{y0}" width="{x1 - x0 + 1}"'
                    f' height="{y1 - y0 + 1}" fill="#FFFFFF"/>')
    parts = body + ['</svg>']
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="{0}" height="{0}" viewBox="0 0 {0} {0}">'
            '<defs><linearGradient id="loom" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="{0}">'
            '<stop offset="0" stop-color="#1F1F1F"/><stop offset="1" stop-color="#000000"/>'
            '</linearGradient></defs>').replace("{0}", str(n)) + "".join(parts)


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
    # favicon.svg 以前是手写的母版几何，不在这条流水线里 —— 于是标签页上一直是
    # 眼距 9/120 那张糊脸（Chromium 优先用 SVG，PNG 兜底根本轮不到）。
    # 现在由同一张 SMALL 表生成，改图标只需要改一处。
    (static / "favicon.svg").write_text(svg_snapped(16), encoding="utf-8")

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
