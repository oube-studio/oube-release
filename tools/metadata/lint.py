"""fastlane/metadata 와 iap-products.json 이 스토어 글자수 한도를 지키는지 검사한다.

한도를 넘으면 실패로 끝내고, 두 스토어의 문구(이름, 설명, 릴리스 노트)가 서로 다르면 경고만 한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import app_root, load_config, read_text

AS_LIMITS = {
    "name.txt": 30,
    "subtitle.txt": 30,
    "keywords.txt": 100,
    "promotional_text.txt": 170,
    "description.txt": 4000,
    "release_notes.txt": 4000,
}
PLAY_LIMITS = {
    "title.txt": 30,
    "short_description.txt": 80,
    "full_description.txt": 4000,
    "changelogs/default.txt": 500,
}
# App Store 인앱 상품 표시 이름과 설명 한도
IAP_LIMITS = {"name": 30, "description": 45}


def lint_iap(path: Path, locales: dict) -> int:
    """iap-products.json 에 설정의 모든 언어가 있고 글자수 한도를 지키는지 검사한다. 파일이 없으면 건너뛴다."""
    if not path.exists():
        return 0
    errors = 0
    with path.open(encoding="utf-8") as file:
        products = json.load(file).get("products", [])
    for product in products:
        product_id = product.get("productId", "?")
        localizations = product.get("localizations", {})
        for code in locales:
            if code not in localizations:
                errors += 1
                print(f"✗ IAP {product_id}: {code} 현지화가 없습니다")
        for code, texts in localizations.items():
            for field, limit in IAP_LIMITS.items():
                length = len(texts.get(field, ""))
                if length > limit:
                    errors += 1
                    print(f"✗ IAP {product_id} {code} {field}: {length}/{limit}")
    return errors


def main() -> None:
    root = app_root()
    meta = root / "fastlane" / "metadata"
    locales = load_config()["locales"]
    errors = lint_iap(root / "fastlane" / "iap-products.json", locales)
    warnings = 0
    for code, locale in locales.items():
        apple = meta / locale["appStore"]
        play = meta / "android" / locale["play"]
        for name, limit in AS_LIMITS.items():
            length = len(read_text(apple / name))
            if length > limit:
                errors += 1
                print(f"✗ {code} App Store {name}: {length}/{limit}")
        for name, limit in PLAY_LIMITS.items():
            length = len(read_text(play / name))
            if length > limit:
                errors += 1
                print(f"✗ {code} Play {name}: {length}/{limit}")
        drift = [
            ("이름", read_text(apple / "name.txt"), read_text(play / "title.txt")),
            ("설명", read_text(apple / "description.txt"), read_text(play / "full_description.txt")),
            (
                "릴리스 노트",
                read_text(apple / "release_notes.txt"),
                read_text(play / "changelogs" / "default.txt"),
            ),
        ]
        for label, apple_text, play_text in drift:
            if apple_text != play_text:
                warnings += 1
                print(f"! {code} {label}이 App Store 와 Play 에서 다릅니다 (의도한 것인지 확인)")
    print(f"\n한도 초과 {errors}건, 두 스토어 문구가 다른 항목 {warnings}건")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
