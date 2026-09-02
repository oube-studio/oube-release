"""한 기기, 한 언어의 캡처 전부를 합성하고 모아보기 시트를 만든다."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import app_root, load_config

from screenshots.compose import compose, style_of


def make_contact_sheet(paths, output_path: Path, device: str, style: dict) -> None:
    background = style["background"]
    fill = tuple(background["bottom"] if isinstance(background, dict) else background)
    outline = tuple(background["top"] if isinstance(background, dict) else style["headlineColor"])
    columns = 3
    gap = 18
    thumb_width = 330 if device == "iphone" else 420
    thumbnails = []
    for path in paths:
        image = Image.open(path).convert("RGB")
        thumb_height = round(image.height * thumb_width / image.width)
        thumbnails.append(image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS))

    rows = (len(thumbnails) + columns - 1) // columns
    cell_height = max(image.height for image in thumbnails)
    sheet = Image.new(
        "RGB",
        (columns * thumb_width + (columns + 1) * gap, rows * cell_height + (rows + 1) * gap),
        fill,
    )
    draw = ImageDraw.Draw(sheet)
    for index, image in enumerate(thumbnails):
        x = gap + (index % columns) * (thumb_width + gap)
        y = gap + (index // columns) * (cell_height + gap)
        sheet.paste(image, (x, y))
        draw.rounded_rectangle(
            (x - 1, y - 1, x + image.width, y + image.height), radius=6, outline=outline, width=2
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", required=True)
    parser.add_argument("--locale", required=True)
    args = parser.parse_args()

    root = app_root()
    config = load_config()
    if args.device not in config["screenshots"]["devices"]:
        sys.exit(f"설정에 없는 기기입니다: {args.device}")
    if args.locale not in config["locales"]:
        sys.exit(f"설정에 없는 언어입니다: {args.locale}")

    captures = root / "store-assets" / "captures" / args.device
    final = root / "store-assets" / "final" / args.device / args.locale
    outputs = []
    for index, scene in enumerate(config["screenshots"]["scenes"], 1):
        if args.locale not in scene["copy"]:
            sys.exit(f"문구가 없습니다: {args.locale}/{scene['id']}")
        number = f"{index:02d}"
        capture = captures / f"{args.locale}-{number}-{scene['id']}.png"
        if not capture.exists():
            sys.exit(f"캡처가 없습니다: {capture}")
        output = final / f"{number}-{scene['id']}.png"
        try:
            outputs.append(compose(capture, output, args.device, args.locale, scene, config, root))
        except ValueError as error:
            sys.exit(str(error))
        print(output)

    contact_sheet = root / "store-assets" / "contact-sheets" / f"{args.device}-{args.locale}.png"
    make_contact_sheet(outputs, contact_sheet, args.device, style_of(config))
    print(contact_sheet)


if __name__ == "__main__":
    main()
