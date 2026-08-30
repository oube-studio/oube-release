"""iap-products.json 검사: 언어 누락과 글자수 한도."""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from metadata.lint import lint_iap  # noqa: E402

LOCALES = {"ko": {}, "en": {}}


class LintIapTest(unittest.TestCase):
    def write(self, products) -> Path:
        path = Path(tempfile.mkdtemp(prefix="oube-iap-")) / "iap-products.json"
        path.write_text(json.dumps({"products": products}), encoding="utf-8")
        return path

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(lint_iap(Path("/nonexistent/iap-products.json"), LOCALES), 0)

    def test_complete_products_pass(self):
        path = self.write(
            [
                {
                    "productId": "app.remove_ads",
                    "localizations": {
                        "ko": {"name": "광고 제거", "description": "광고를 없앱니다."},
                        "en": {"name": "Remove Ads", "description": "Removes ads."},
                    },
                }
            ]
        )
        self.assertEqual(lint_iap(path, LOCALES), 0)

    def test_counts_missing_locales_and_over_limits(self):
        path = self.write(
            [
                {
                    "productId": "app.remove_ads",
                    "localizations": {"ko": {"name": "x" * 31, "description": "y" * 46}},
                }
            ]
        )
        with contextlib.redirect_stdout(io.StringIO()) as printed:
            errors = lint_iap(path, LOCALES)
        self.assertEqual(errors, 3)  # en 누락 1 + 이름 초과 1 + 설명 초과 1
        self.assertIn("ko name: 31/30", printed.getvalue())


if __name__ == "__main__":
    unittest.main()
