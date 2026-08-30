"""폰트 다운로더의 네트워크 없는 부분: 없는 파일 판별, 체크섬 검증, zip 에서 꺼내기."""

from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from fonts import fetch  # noqa: E402


class FontsTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="oube-fonts-"))
        os.environ["OUBE_CACHE_DIR"] = str(self.root / "cache")
        self.config = {
            "screenshots": {
                "fonts": {
                    "default": {"regular": "fonts/A.otf", "semibold": "fonts/B.otf"},
                    "ja": {"variable": "fonts/C.ttf"},
                    "zh-Hans": {"variable": "fonts/C.ttf"},
                }
            }
        }

    def test_lists_only_missing_files_once(self):
        (self.root / "fonts").mkdir()
        (self.root / "fonts" / "B.otf").write_bytes(b"x")
        missing = fetch.missing_fonts(self.config, self.root)
        self.assertEqual([p.name for p in missing], ["A.otf", "C.ttf"])

    def test_verify_rejects_and_removes_a_tampered_file(self):
        path = self.root / "bad.ttf"
        path.write_bytes(b"tampered")
        with self.assertRaises(SystemExit):
            fetch.verify(path, hashlib.sha256(b"original").hexdigest())
        self.assertFalse(path.exists())

    def test_extracts_a_zip_member_from_a_verified_archive(self):
        archive = fetch.cache_dir() / "bundle.zip"
        with zipfile.ZipFile(archive, "w") as bundle:
            bundle.writestr("public/static/X.otf", b"font bytes")
        target = self.root / "X.otf"
        fetch.fetch_zip_member(
            "file:///unused/bundle.zip", fetch.sha256_of(archive), "public/static/X.otf", target
        )
        self.assertEqual(target.read_bytes(), b"font bytes")

    def test_unknown_font_names_fail_with_the_known_list(self):
        with self.assertRaises(SystemExit) as raised:
            fetch.fetch_font(self.root / "Mystery.ttf")
        self.assertIn("NotoSansJP.ttf", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
