#!/usr/bin/env python3
"""生成应用图标 assets/icon.ico：渐变圆角方块 + 白色播放三角。

纯标准库（zlib+struct 手写 PNG），无新依赖。改配色/形状后重跑：
    python scripts/make_icon.py
"""
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "assets" / "icon.ico"
SIZES = [256, 48, 32, 16]
# 主题色（与 style.css 变量一致）
C1 = (0x06, 0xb6, 0xd4)   # cyan
C2 = (0x7c, 0x5c, 0xff)   # purple
WHITE = (0xff, 0xff, 0xff)
BG = (7, 11, 20, 255)     # --bg 不透明底


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def inside_rounded(x, y, s, r):
    """点是否在圆角矩形内。"""
    if 0 <= x < s and 0 <= y < s:
        cx = min(max(x, r), s - 1 - r)
        cy = min(max(y, r), s - 1 - r)
        return (x - cx) ** 2 + (y - cy) ** 2 <= r * r or (r <= x < s - r) or (r <= y < s - r)
    return False


def in_triangle(px, py, s):
    """居中白色播放三角（固定比例顶点）。"""
    ax, ay = s * 0.38, s * 0.28           # 顶点
    bx, by = s * 0.38, s * 0.72           # 左下
    cx, cy = s * 0.74, s * 0.5            # 右尖

    def side(x1, y1, x2, y2):
        return (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)

    d1 = side(ax, ay, bx, by)
    d2 = side(bx, by, cx, cy)
    d3 = side(cx, cy, ax, ay)
    return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))


def render(size):
    r = max(2, size // 5)
    rows = []
    for y in range(size):
        row = bytearray([0])  # PNG filter type 0
        for x in range(size):
            if not inside_rounded(x, y, size, r):
                row += bytes(BG)
                continue
            t = (x + y) / (2 * size - 2)  # 对角线渐变
            base = lerp(C1, C2, t)
            if in_triangle(x, y, size):
                row += bytes(WHITE) + b"\xff"
            else:
                row += bytes(base) + b"\xff"
        rows.append(bytes(row))
    return b"".join(rows)


def png_chunk(tag, data):
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def make_png(size):
    raw = render(size)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # 8bit RGBA
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b""))


def make_ico(images):
    """ICO 容器：目录 + 内嵌 PNG（Vista+ 支持）。"""
    header = struct.pack("<HHH", 0, 1, len(images))
    entries, body = b"", b""
    offset = 6 + 16 * len(images)  # 数据区在目录表之后
    for size, png in images:
        w = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", w, w, 0, 0, 1, 32, len(png), offset)
        body += png
        offset += len(png)
    return header + entries + body


def main():
    OUT.parent.mkdir(exist_ok=True)
    images = [(s, make_png(s)) for s in SIZES]
    OUT.write_bytes(make_ico(images))
    print(f"icon written: {OUT} ({OUT.stat().st_size} bytes, sizes={SIZES})")


if __name__ == "__main__":
    main()
