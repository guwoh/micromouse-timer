from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    size = 256
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, 251, 251), radius=54, fill="#17324d")
    draw.rounded_rectangle((104, 24, 152, 55), radius=9, fill="#ffc54a")
    draw.ellipse((43, 48, 213, 218), fill="#ffc54a")
    draw.ellipse((65, 70, 191, 196), fill="#17324d")
    draw.line((128, 133, 128, 87), fill="white", width=13)
    draw.line((128, 133, 163, 152), fill="white", width=13)
    draw.ellipse((119, 124, 137, 142), fill="white")

    assets = Path(__file__).resolve().parents[1] / "assets" / "icons"
    assets.mkdir(parents=True, exist_ok=True)
    image.save(assets / "micromouse.png")
    image.save(
        assets / "micromouse.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
