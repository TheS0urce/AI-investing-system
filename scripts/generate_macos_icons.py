from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = ROOT / "scripts" / "macos_apps" / "icons"

SPECS = {
    "AI Investing Start API": {
        "bg": ("#0b5f4a", "#27d07d"),
        "symbol": "play",
        "accent": "#d7ff71",
    },
    "AI Investing Health": {
        "bg": ("#123c69", "#2bd3ff"),
        "symbol": "pulse",
        "accent": "#ffffff",
    },
    "AI Investing Dashboard": {
        "bg": ("#30236f", "#ff8f5a"),
        "symbol": "chart",
        "accent": "#f7f1d5",
    },
    "AI Investing Daily Ops": {
        "bg": ("#1f4d3a", "#f0c84b"),
        "symbol": "check",
        "accent": "#ffffff",
    },
    "AI Investing Stop API": {
        "bg": ("#5f1515", "#ff4f4f"),
        "symbol": "stop",
        "accent": "#fff0d6",
    },
}


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded_rect_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
    return mask


def gradient(size: int, c1: str, c2: str) -> Image.Image:
    start = hex_to_rgb(c1)
    end = hex_to_rgb(c2)
    img = Image.new("RGB", (size, size))
    pixels = img.load()
    for y in range(size):
        for x in range(size):
            t = (x * 0.65 + y * 0.35) / size
            pixels[x, y] = tuple(int(start[i] * (1 - t) + end[i] * t) for i in range(3))
    return img


def draw_start(draw: ImageDraw.ImageDraw, accent: str) -> None:
    draw.rounded_rectangle((220, 650, 804, 745), radius=46, fill=(255, 255, 255, 42))
    draw.polygon([(375, 290), (375, 585), (635, 438)], fill=accent)
    draw.arc((245, 210, 780, 745), 210, 510, fill=(255, 255, 255, 165), width=34)
    draw.arc((185, 150, 840, 805), 210, 510, fill=(255, 255, 255, 70), width=18)


def draw_health(draw: ImageDraw.ImageDraw, accent: str) -> None:
    pts = [(135, 540), (270, 540), (330, 405), (425, 655), (515, 295), (610, 540), (890, 540)]
    draw.line(pts, fill=accent, width=38, joint="curve")
    draw.ellipse((380, 200, 645, 465), outline=(255, 255, 255, 85), width=26)
    draw.ellipse((425, 245, 600, 420), fill=(255, 255, 255, 35))
    draw.rounded_rectangle((215, 685, 810, 770), radius=42, fill=(0, 0, 0, 52))


def draw_dashboard(draw: ImageDraw.ImageDraw, accent: str) -> None:
    draw.rounded_rectangle((190, 220, 835, 735), radius=58, fill=(0, 0, 0, 72), outline=(255, 255, 255, 95), width=18)
    bars = [(285, 565, 360, 650), (430, 480, 505, 650), (575, 380, 650, 650)]
    for box in bars:
        draw.rounded_rectangle(box, radius=26, fill=accent)
    draw.line([(275, 405), (415, 465), (550, 335), (740, 430)], fill="#5dfff2", width=28, joint="curve")
    draw.ellipse((720, 405, 765, 450), fill="#5dfff2")


def draw_stop(draw: ImageDraw.ImageDraw, accent: str) -> None:
    draw.rounded_rectangle((255, 255, 770, 770), radius=112, fill=(0, 0, 0, 80), outline=accent, width=34)
    draw.rounded_rectangle((365, 365, 660, 660), radius=46, fill=accent)
    draw.arc((190, 190, 835, 835), 25, 335, fill=(255, 255, 255, 90), width=24)


def draw_check(draw: ImageDraw.ImageDraw, accent: str) -> None:
    draw.rounded_rectangle((205, 215, 820, 760), radius=70, fill=(0, 0, 0, 70), outline=(255, 255, 255, 80), width=16)
    draw.line([(300, 525), (445, 665), (735, 350)], fill=accent, width=58, joint="curve")
    draw.arc((245, 250, 780, 785), 205, 500, fill=(255, 255, 255, 110), width=24)
    for x, height in ((330, 95), (455, 145), (580, 210), (705, 155)):
        draw.rounded_rectangle((x, 300 + (220 - height), x + 54, 520), radius=20, fill=(255, 255, 255, 48))


def render_icon(name: str, spec: dict[str, object]) -> Image.Image:
    size = 1024
    img = gradient(size, *spec["bg"]).convert("RGBA")
    overlay = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    draw.ellipse((-155, -115, 470, 510), fill=(255, 255, 255, 55))
    draw.ellipse((565, 610, 1220, 1235), fill=(0, 0, 0, 45))
    draw.rounded_rectangle((116, 116, 908, 908), radius=190, outline=(255, 255, 255, 70), width=10)

    symbol = spec["symbol"]
    accent = spec["accent"]
    if symbol == "play":
        draw_start(draw, accent)
    elif symbol == "pulse":
        draw_health(draw, accent)
    elif symbol == "chart":
        draw_dashboard(draw, accent)
    elif symbol == "check":
        draw_check(draw, accent)
    elif symbol == "stop":
        draw_stop(draw, accent)

    label = name.replace("AI Investing ", "").upper()
    font = load_font(58)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    draw.text(((size - text_w) / 2, 825), label, font=font, fill=(255, 255, 255, 210))

    img = Image.alpha_composite(img, overlay)
    mask = rounded_rect_mask(size, 190)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def make_iconset(name: str, image: Image.Image) -> Path:
    iconset = ASSET_DIR / f"{name}.iconset"
    iconset.mkdir(parents=True, exist_ok=True)
    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for filename, size in sizes.items():
        image.resize((size, size), Image.Resampling.LANCZOS).save(iconset / filename)
    return iconset


def main() -> int:
    dest_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Applications" / "AI Investment"
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    for name, spec in SPECS.items():
        image = render_icon(name, spec)
        image.save(ASSET_DIR / f"{name}.png")
        iconset = make_iconset(name, image)
        icns_path = ASSET_DIR / f"{name}.icns"
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns_path)], check=True)

        app_icon = dest_dir / f"{name}.app" / "Contents" / "Resources" / "applet.icns"
        if app_icon.exists():
            app_icon.write_bytes(icns_path.read_bytes())

    print(f"Generated icons in: {ASSET_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
