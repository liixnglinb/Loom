# -*- coding: utf-8 -*-
"""生成 assets/loom.ico 与配套 PNG（和 static/logo.svg 同一套几何数值）。

为什么用代码画而不是转 SVG：本机没有 cairosvg / inkscape，而这个图标只有
圆角方块 + 圆 + 渐变四样东西，按 SVG 里的坐标复画比引一个渲染依赖更可控。
ICO 一次写 256/128/64/48/32/16 六档，Windows 任务栏、资源管理器、
安装向导和浏览器标签页各取所需，不会拿 256 去硬缩。
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
OUT = BASE / "assets"
SIZE = 1024                      # 先按 1024 画再降采样，圆角边缘才不会锯齿
TOP = (0x5B, 0x96, 0xF9)
BOT = (0x2C, 0x62, 0xD6)
LIGHT = (0xF2, 0xF6, 0xFD)


def grad(y: float) -> tuple:
    """按 viewBox 高度（0~120）取渐变颜色，userSpaceOnUse 就是这个语义。"""
    t = max(0.0, min(1.0, y / 120.0))
    return tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOT))


def s(v: float) -> float:
    return v * SIZE / 120.0


def build() -> Image.Image:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    # 竖向渐变铺满，再用圆角矩形当蒙版抠出来
    strip = Image.new("RGBA", (SIZE, SIZE))
    d = ImageDraw.Draw(strip)
    for y in range(SIZE):
        d.line([(0, y), (SIZE, y)], fill=grad(y * 120 / SIZE) + (255,))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=s(27), fill=255)
    img.paste(strip, (0, 0), mask)

    d = ImageDraw.Draw(img)
    d.rounded_rectangle([s(12), s(42), s(12) + s(62), s(42) + s(62)], radius=s(22), fill=LIGHT + (255,))
    # 眼睛取底色的渐变值，视觉上就是"挖穿"，和 SVG 里 fill=url(#loom) 等价
    for cx in (31, 55):
        c = grad(71) + (255,)
        d.ellipse([s(cx) - s(7.5), s(71) - s(7.5), s(cx) + s(7.5), s(71) + s(7.5)], fill=c)
    d.ellipse([s(93) - s(13), s(27) - s(13), s(93) + s(13), s(27) + s(13)], fill=LIGHT + (255,))
    return img


def main() -> int:
    OUT.mkdir(exist_ok=True)
    big = build()
    sizes = [256, 128, 64, 48, 32, 16]
    big.save(OUT / "loom-1024.png")
    big.resize((256, 256), Image.LANCZOS).save(OUT / "loom-256.png")
    big.resize((64, 64), Image.LANCZOS).save(OUT / "logo-64.png")
    big.resize((48, 48), Image.LANCZOS).save(OUT / "favicon-48.png")
    big.save(OUT / "loom.ico", format="ICO",
             sizes=[(n, n) for n in sizes], append_images=[
                 big.resize((n, n), Image.LANCZOS) for n in sizes[:-1]])
    for f in sorted(OUT.iterdir()):
        print(f"{f.name:16s} {f.stat().st_size/1024:6.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
