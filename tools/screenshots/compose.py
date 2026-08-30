"""시뮬레이터 캡처 한 장을 스토어 스크린샷 한 장으로 합성한다: 배경 + 기기 프레임 + 캡처 + 문구.

치수는 캔버스 폭 1320px 기준(헤드라인 88, 부제 56, 자간 -3%, 문구와 기기 사이 96)이고 캔버스 폭에 비례해 바꾼다.
색, 폰트, 기기, 장면은 oube.config.json 의 screenshots 항목에서 읽는다.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import app_root

BEZEL_DIR = Path(__file__).resolve().parent / "bezels"
DEFAULT_STYLE = {
    "background": {"top": [93, 104, 138], "bottom": [62, 70, 96]},
    "noise": True,
    "headlineColor": [255, 242, 239],
    "subheadlineColor": [255, 242, 239],
}
NOISE_SEED = 247391
CHAR_WRAP_LANGUAGES = {"ja", "zh"}


def style_of(config: dict) -> dict:
    return {**DEFAULT_STYLE, **config["screenshots"].get("style", {})}


def make_background(width: int, height: int, style: dict) -> Image.Image:
    background = style["background"]
    if isinstance(background, dict):
        top = np.array(background["top"], dtype=np.float32)[None, None, :]
        bottom = np.array(background["bottom"], dtype=np.float32)[None, None, :]
        y = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
        pixels = np.broadcast_to(top * (1 - y) + bottom * y, (height, width, 3)).copy()
    else:
        pixels = np.broadcast_to(np.array(background, dtype=np.float32), (height, width, 3)).copy()
    if style["noise"]:
        rng = np.random.default_rng(NOISE_SEED)
        pixels = pixels + rng.normal(0, 1.25, (height, width, 1))
    return Image.fromarray(np.clip(pixels, 0, 255).astype(np.uint8))


def longest_run(mask):
    best = (0, -1)
    start = None
    for index, value in enumerate(mask):
        if value and start is None:
            start = index
        elif not value and start is not None:
            if index - 1 - start > best[1] - best[0]:
                best = (start, index - 1)
            start = None
    if start is not None and len(mask) - 1 - start > best[1] - best[0]:
        best = (start, len(mask) - 1)
    return best


def detect_screen(alpha):
    height, width = alpha.shape
    x0, x1 = longest_run(alpha[height // 2] < 16)
    y0, y1 = longest_run(alpha[:, width // 4] < 16)
    return x0, y0, x1, y1


def font_spec(config: dict, locale: str) -> dict:
    fonts = config["screenshots"]["fonts"]
    return fonts.get(locale) or fonts["default"]


def load_font(config: dict, root: Path, locale: str, weight: str, size: float) -> ImageFont.FreeTypeFont:
    spec = font_spec(config, locale)
    pixel_size = round(size)
    if "variable" in spec:
        font = ImageFont.truetype(str(root / spec["variable"]), pixel_size)
        font.set_variation_by_axes([600 if weight == "semibold" else 400])
        return font
    return ImageFont.truetype(str(root / spec[weight]), pixel_size)


def wraps_by_character(locale: str) -> bool:
    return locale.split("-")[0] in CHAR_WRAP_LANGUAGES


def wrap_paragraph(draw, text, font, max_width, locale):
    if not text:
        return [""]
    if wraps_by_character(locale):
        units = list(text)
        separator = ""
    else:
        units = text.split()
        separator = " "

    lines = []
    current = ""
    for unit in units:
        candidate = f"{current}{separator if current else ''}{unit}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = unit
    if current:
        lines.append(current)
    return lines


def wrap_text(draw, text, font, max_width, locale):
    lines = []
    for paragraph in text.split("\n"):
        lines.extend(wrap_paragraph(draw, paragraph, font, max_width, locale))
    return lines


def draw_letter_spaced(draw, text, font, center_x, y, fill, spacing):
    widths = [draw.textlength(character, font=font) for character in text]
    total_width = sum(widths) + spacing * max(0, len(text) - 1)
    x = center_x - total_width / 2
    for character, width in zip(text, widths):
        draw.text((x, y), character, font=font, fill=tuple(fill), anchor="la")
        x += width + spacing


# .png 로 끝나면 앱 폴더 기준 경로(앱 전용 베젤), 아니면 패키지에 들어 있는 베젤 이름
def bezel_path(device_config: dict, root: Path) -> Path:
    name = device_config["bezel"]
    if name.endswith(".png"):
        return root / name
    return BEZEL_DIR / f"{name}.png"


def load_frame(device_config: dict, root: Path) -> Image.Image:
    frame = Image.open(bezel_path(device_config, root)).convert("RGBA")
    rotation = device_config.get("rotateBezel", 0)
    if rotation:
        frame = frame.rotate(rotation, expand=True)
    return frame


def compose(
    shot_path, output_path, device: str, locale: str, scene: dict, config: dict, root: Path | None = None
):
    root = root or app_root()
    device_config = config["screenshots"]["devices"][device]
    style = style_of(config)
    width, height = device_config["canvas"]
    copy = scene["copy"][locale]

    canvas = make_background(width, height, style)
    draw = ImageDraw.Draw(canvas)

    frame_source = load_frame(device_config, root)
    source_width, source_height = frame_source.size
    device_width = int(width * device_config["frameWidthFraction"])
    scale = device_width / source_width
    frame = frame_source.resize((device_width, round(source_height * scale)), Image.Resampling.LANCZOS)
    frame_width, frame_height = frame.size
    device_x = (width - frame_width) // 2

    canvas_scale = width / 1320
    headline_size = 88 * canvas_scale
    subhead_size = 56 * canvas_scale
    headline_font = load_font(config, root, locale, "semibold", headline_size)
    subhead_font = load_font(config, root, locale, "regular", subhead_size)
    headline_line_height = sum(headline_font.getmetrics())
    subhead_line_height = sum(subhead_font.getmetrics())
    caption_gap = 32 * canvas_scale
    device_gap = 96 * canvas_scale
    max_text_width = width * 0.86

    headline_lines = wrap_text(draw, copy["headline"], headline_font, max_text_width, locale)
    subhead_lines = wrap_text(draw, copy["subheadline"], subhead_font, max_text_width, locale)
    if len(headline_lines) > 2 or len(subhead_lines) > 2:
        raise ValueError(f"문구가 두 줄을 넘습니다: {locale}/{scene['id']}")

    caption_height = (
        len(headline_lines) * headline_line_height + caption_gap + len(subhead_lines) * subhead_line_height
    )

    if device_config["anchor"] == "center":
        content_height = caption_height + device_gap + frame_height
        caption_y = (height - content_height) / 2
        device_y = round(caption_y + caption_height + device_gap)
    else:
        device_y = height - frame_height - device_x
        caption_y = device_y - device_gap - caption_height

    if caption_y < 0 or device_y + frame_height > height:
        raise ValueError(f"레이아웃이 캔버스를 넘습니다: {device}/{locale}/{scene['id']}")

    # 베젤의 투명한 화면 영역을 floodfill 로 찾아 마스크로 쓴다. 프레임 안쪽 끝까지 채우므로 틈이 생기지 않는다
    alpha = np.array(frame.getchannel("A"))
    screen_x0, screen_y0, screen_x1, screen_y1 = detect_screen(alpha)
    seed = ((screen_x0 + screen_x1) // 2, (screen_y0 + screen_y1) // 2)
    transparent = Image.fromarray(np.where(alpha < 250, 255, 0).astype("uint8")).copy()
    ImageDraw.floodfill(transparent, seed, 100, thresh=0)
    screen_mask = Image.fromarray(((np.array(transparent) == 100) * 255).astype("uint8"))
    screen_bounds = screen_mask.getbbox()
    if not screen_bounds:
        raise ValueError(f"베젤에서 화면 영역을 찾을 수 없습니다: {device}")

    device_image = Image.new("RGBA", (frame_width, frame_height), (0, 0, 0, 0))
    screenshot = ImageOps.fit(
        Image.open(shot_path).convert("RGB"),
        (screen_bounds[2] - screen_bounds[0], screen_bounds[3] - screen_bounds[1]),
        method=Image.Resampling.LANCZOS,
    )
    device_image.paste(screenshot, (screen_bounds[0], screen_bounds[1]), screen_mask.crop(screen_bounds))
    device_image.alpha_composite(frame)
    canvas.paste(device_image, (device_x, device_y), device_image)

    text_y = caption_y
    for line in headline_lines:
        draw_letter_spaced(
            draw, line, headline_font, width // 2, text_y, style["headlineColor"], -0.03 * headline_size
        )
        text_y += headline_line_height
    text_y += caption_gap
    for line in subhead_lines:
        draw_letter_spaced(
            draw, line, subhead_font, width // 2, text_y, style["subheadlineColor"], -0.03 * subhead_size
        )
        text_y += subhead_line_height

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path)
    return output_path
