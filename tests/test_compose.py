"""합성기를 합성 베젤과 가짜 캡처로 끝까지 돌려 본다. 실제 앱 캡처 없이도 레이아웃 계산과 마스크 검출을 검사한다."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from screenshots.compose import compose, wrap_paragraph  # noqa: E402

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]


def find_font() -> str | None:
    return next((f for f in FONT_CANDIDATES if Path(f).exists()), None)


def make_bezel(path: Path, size=(400, 820), border=24) -> None:
    frame = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=60, fill=(20, 20, 20, 255))
    draw.rounded_rectangle(
        (border, border, size[0] - 1 - border, size[1] - 1 - border), radius=40, fill=(0, 0, 0, 0)
    )
    frame.save(path)


def make_capture(path: Path, size=(660, 1434)) -> None:
    image = Image.new("RGB", size, (30, 120, 200))
    ImageDraw.Draw(image).rectangle((40, 40, size[0] - 40, 300), fill=(250, 250, 250))
    image.save(path)


class ComposeTest(unittest.TestCase):
    def setUp(self):
        font = find_font()
        if not font:
            self.skipTest("테스트용 시스템 폰트를 찾지 못했습니다")
        self.root = Path(tempfile.mkdtemp(prefix="oube-compose-"))
        make_bezel(self.root / "bezel.png")
        make_capture(self.root / "capture.png")
        self.config = {
            "scheme": "demo",
            "ios": {"bundleId": "com.example.demo"},
            "android": {"package": "com.example.demo"},
            "locales": {"en": {"appStore": "en-US", "play": "en-US", "storefront": "us", "hl": "en"}},
            "screenshots": {
                "devices": {
                    "iphone": {
                        "simulatorName": "test",
                        "canvas": [660, 1434],
                        "bezel": "bezel.png",
                        "frameWidthFraction": 0.86,
                        "anchor": "bottom",
                    },
                    "ipad": {
                        "simulatorName": "test",
                        "canvas": [1032, 1376],
                        "bezel": "bezel.png",
                        "rotateBezel": 90,
                        "frameWidthFraction": 0.68,
                        "anchor": "center",
                    },
                },
                "style": {"background": [16, 16, 16], "noise": False},
                "fonts": {"default": {"regular": font, "semibold": font}},
                "scenes": [],
            },
        }
        os.environ["OUBE_APP_ROOT"] = str(self.root)
        (self.root / "oube.config.json").write_text(json.dumps(self.config), encoding="utf-8")

    def scene(self, headline="Track your day", subheadline="Steps, workouts and streaks in one place"):
        return {"id": "home", "copy": {"en": {"headline": headline, "subheadline": subheadline}}}

    def test_composes_both_anchors_at_canvas_size(self):
        for device, canvas in (("iphone", (660, 1434)), ("ipad", (1032, 1376))):
            output = compose(
                self.root / "capture.png",
                self.root / f"{device}.png",
                device,
                "en",
                self.scene(),
                self.config,
                self.root,
            )
            with Image.open(output) as image:
                self.assertEqual(image.size, canvas)
                # 캡처(파랑)가 프레임 화면창 안에 실제로 들어갔는지: 파랑에 가까운 픽셀이 충분히 많다
                pixels = np.asarray(image.convert("RGB"), dtype=np.int32)
                blue = np.abs(pixels - np.array([30, 120, 200])).sum(axis=2) < 30
                self.assertGreater(int(blue.sum()), 10_000, device)

    def test_rejects_captions_longer_than_two_lines(self):
        with self.assertRaises(ValueError):
            compose(
                self.root / "capture.png",
                self.root / "long.png",
                "iphone",
                "en",
                self.scene(headline=" ".join(["Enormous"] * 20)),
                self.config,
                self.root,
            )

    def test_wraps_cjk_by_character_and_latin_by_word(self):
        class Measure:
            def textlength(self, text, font=None):
                return len(text) * 10

        self.assertEqual(
            wrap_paragraph(Measure(), "한국어 테스트 문장", None, 60, "ja"), ["한국어 테스", "트 문장"]
        )
        self.assertEqual(wrap_paragraph(Measure(), "one two three", None, 80, "en"), ["one two", "three"])


if __name__ == "__main__":
    unittest.main()
