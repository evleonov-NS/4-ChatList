"""Генерация app.ico для ChatList — иконка в стиле AI / нейросеть + чат."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ICON_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]

# Палитра ChatList (themes.py)
COLOR_BG_TOP = (244, 162, 97)       # #F4A261
COLOR_BG_BOTTOM = (231, 111, 81)    # #E76F51
COLOR_RING = (255, 248, 243)        # #FFF8F3
COLOR_BUBBLE = (255, 255, 255, 235)
COLOR_NODE = (255, 255, 255, 255)
COLOR_NODE_CORE = (42, 33, 28)      # #2A211C
COLOR_LINK = (255, 221, 184, 220)   # мягкое свечение связей
COLOR_SPARK = (255, 248, 243, 255)


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _gradient_background(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(1, size // 16)
    radius = max(2, size // 5)

    for y in range(pad, size - pad):
        t = (y - pad) / max(1, size - 2 * pad - 1)
        row_color = (
            _lerp(COLOR_BG_TOP[0], COLOR_BG_BOTTOM[0], t),
            _lerp(COLOR_BG_TOP[1], COLOR_BG_BOTTOM[1], t),
            _lerp(COLOR_BG_TOP[2], COLOR_BG_BOTTOM[2], t),
            255,
        )
        draw.line([(pad, y), (size - pad - 1, y)], fill=row_color)

    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [pad, pad, size - pad - 1, size - pad - 1],
        radius=radius,
        fill=255,
    )
    img.putalpha(mask)
    return img


def _draw_spark(draw: ImageDraw.ImageDraw, x: int, y: int, arm: int) -> None:
    draw.line([(x - arm, y), (x + arm, y)], fill=COLOR_SPARK, width=max(1, arm // 3))
    draw.line([(x, y - arm), (x, y + arm)], fill=COLOR_SPARK, width=max(1, arm // 3))
    d = arm // 2
    draw.line([(x - d, y - d), (x + d, y + d)], fill=COLOR_SPARK, width=1)
    draw.line([(x - d, y + d), (x + d, y - d)], fill=COLOR_SPARK, width=1)


def _draw_chat_bubble(draw: ImageDraw.ImageDraw, size: int) -> None:
    cx, cy = size // 2, size * 11 // 24
    bw = size * 2 // 5
    bh = size // 4
    left = cx - bw // 2
    top = cy - bh // 2
    right = cx + bw // 2
    bottom = cy + bh // 2
    radius = max(2, bh // 3)

    draw.rounded_rectangle(
        [left, top, right, bottom],
        radius=radius,
        fill=COLOR_BUBBLE,
    )
    tail = [
        (cx - bw // 6, bottom - 1),
        (cx - bw // 4, bottom + max(2, bh // 3)),
        (cx + bw // 12, bottom - 1),
    ]
    draw.polygon(tail, fill=COLOR_BUBBLE)

    dot_r = max(1, size // 40)
    gap = max(2, size // 18)
    dots_y = cy
    for offset in (-gap, 0, gap):
        x0 = cx + offset - dot_r
        y0 = dots_y - dot_r
        draw.ellipse(
            [x0, y0, x0 + 2 * dot_r, y0 + 2 * dot_r],
            fill=COLOR_NODE_CORE,
        )


def _draw_neural_net(draw: ImageDraw.ImageDraw, size: int) -> None:
    cx, cy = size // 2, size * 17 // 24
    node_r = max(2, size // 18)
    link_w = max(1, size // 64)

    nodes = [
        (cx, cy - size // 6),
        (cx - size // 5, cy),
        (cx + size // 5, cy),
        (cx - size // 7, cy + size // 7),
        (cx + size // 7, cy + size // 7),
        (cx, cy + size // 6),
    ]
    links = [
        (0, 1), (0, 2), (0, 5),
        (1, 3), (2, 4), (3, 5), (4, 5),
        (1, 2), (3, 4),
    ]

    for i, j in links:
        x1, y1 = nodes[i]
        x2, y2 = nodes[j]
        draw.line([(x1, y1), (x2, y2)], fill=COLOR_LINK, width=link_w)

    for x, y in nodes:
        draw.ellipse(
            [x - node_r, y - node_r, x + node_r, y + node_r],
            fill=COLOR_NODE,
        )
        inner = max(1, node_r // 2)
        draw.ellipse(
            [x - inner, y - inner, x + inner, y + inner],
            fill=COLOR_NODE_CORE if size >= 32 else COLOR_NODE,
        )


def _draw_ring(draw: ImageDraw.ImageDraw, size: int) -> None:
    pad = max(1, size // 16)
    radius = max(2, size // 5)
    width = max(1, size // 32)
    draw.rounded_rectangle(
        [pad, pad, size - pad - 1, size - pad - 1],
        radius=radius,
        outline=COLOR_RING,
        width=width,
    )


def render_icon(size: int) -> Image.Image:
    img = _gradient_background(size)
    draw = ImageDraw.Draw(img)

    if size >= 48:
        _draw_neural_net(draw, size)
        _draw_chat_bubble(draw, size)
        if size >= 64:
            _draw_spark(draw, size * 7 // 8, size // 8, max(2, size // 16))
    elif size >= 32:
        cx, cy = size // 2, size // 2
        r = size // 6
        draw.rounded_rectangle(
            [cx - r, cy - r - 2, cx + r, cy + r - 2],
            radius=max(2, r // 2),
            fill=COLOR_BUBBLE,
        )
        dot = max(1, size // 10)
        for dx in (-dot * 2, 0, dot * 2):
            draw.ellipse(
                [cx + dx - dot, cy - dot, cx + dx + dot, cy + dot],
                fill=COLOR_NODE_CORE,
            )
        nr = max(1, size // 10)
        for ox, oy in ((-size // 5, size // 6), (size // 5, size // 6)):
            draw.ellipse(
                [cx + ox - nr, cy + oy - nr, cx + ox + nr, cy + oy + nr],
                fill=COLOR_NODE,
            )
    else:
        cx, cy = size // 2, size // 2
        draw.ellipse(
            [cx - 2, cy - 2, cx + 2, cy + 2],
            fill=COLOR_BUBBLE,
        )
        draw.ellipse(
            [cx - 1, cy - 1, cx + 1, cy + 1],
            fill=COLOR_NODE_CORE,
        )

    _draw_ring(draw, size)
    return img


def create_ico(output_path: Path | None = None) -> Path:
    output = output_path or Path(__file__).resolve().parent / "assets" / "app.ico"
    output.parent.mkdir(parents=True, exist_ok=True)

    images = [render_icon(width) for width, _ in ICON_SIZES]
    images[0].save(
        output,
        format="ICO",
        sizes=ICON_SIZES,
        append_images=images[1:],
    )

    preview = output.with_suffix(".preview.png")
    render_icon(256).save(preview, format="PNG")
    return output


def main() -> None:
    path = create_ico()
    print(f"Создано: {path}")
    print(f"Превью: {path.with_suffix('.preview.png')}")
    print(f"Размеры: {', '.join(f'{w}x{h}' for w, h in ICON_SIZES)}")


if __name__ == "__main__":
    main()
