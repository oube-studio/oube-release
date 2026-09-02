"""fastlane/metadata 와 두 스토어에 실제로 올라간 문구를 비교한다.

출시가 스토어에 반영된 뒤 실행한다. App Store 의 부제, 프로모션 텍스트, 키워드는
Lookup API 가 제공하지 않아서 비교하지 못한다.
"""

from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import app_root, app_version, load_config, read_text

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"


def norm(text: str) -> str:
    text = unicodedata.normalize("NFC", text).replace("\u00a0", " ")  # 스토어 페이지의 NBSP 를 보통 공백으로
    return re.sub(r"\s+", " ", text).strip()


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read().decode("utf-8", errors="replace")


def show(label: str, ok: bool, expected: str = "", actual: str = "") -> int:
    if ok:
        print(f"    같음  {label}")
        return 0
    print(f"    다름  {label}")
    if expected or actual:
        print(f"          로컬:   {expected[:110]}")
        print(f"          스토어: {actual[:110]}")
    return 1


def page_text(raw: str) -> str:
    raw = re.sub(r"<br\s*/?>", " ", raw, flags=re.IGNORECASE)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return norm(html.unescape(raw))


def check_app_store(meta: Path, config: dict, version: str) -> tuple[int, int]:
    """(다른 항목 수, 조회 결과가 없어 건너뛴 지역 수)를 돌려준다."""
    diffs = 0
    skipped = 0
    bundle_id = config["ios"]["bundleId"]
    print("\n=== App Store (iTunes Lookup API) ===")
    for code, locale in config["locales"].items():
        folder = meta / locale["appStore"]
        print(f"\n  [{code}] storefront={locale['storefront']}")
        try:
            data = json.loads(
                fetch(f"https://itunes.apple.com/lookup?bundleId={bundle_id}&country={locale['storefront']}")
            )
        except Exception as error:  # noqa: BLE001 네트워크 실패도 결과 한 줄로 남긴다
            print(f"    오류  조회 실패: {error}")
            diffs += 1
            continue
        # 지역이 처리 중이거나 그 지역에 출시하지 않았으면 결과가 없다. 문구가 다른 것이 아니므로 실패로 세지 않는다
        if not data.get("resultCount"):
            print("    없음  이 스토어프런트에 게시된 앱이 없습니다 (지역이 처리 중이거나 미출시면 정상)")
            skipped += 1
            continue
        result = data["results"][0]
        expected_name = read_text(folder / "name.txt")
        expected_description = read_text(folder / "description.txt")
        expected_notes = read_text(folder / "release_notes.txt")
        diffs += show("버전", result.get("version") == version, version, str(result.get("version")))
        diffs += show(
            "이름",
            norm(result.get("trackName", "")) == norm(expected_name),
            expected_name,
            result.get("trackName", ""),
        )
        diffs += show(
            "설명",
            norm(result.get("description", "")) == norm(expected_description),
            norm(expected_description),
            norm(result.get("description", "")),
        )
        diffs += show(
            "릴리스 노트",
            norm(result.get("releaseNotes", "")) == norm(expected_notes),
            norm(expected_notes),
            norm(result.get("releaseNotes", "")),
        )
    return diffs, skipped


def check_play(meta: Path, config: dict) -> int:
    diffs = 0
    package = config["android"]["package"]
    print("\n=== Google Play (listing pages) ===")
    for code, locale in config["locales"].items():
        folder = meta / "android" / locale["play"]
        print(f"\n  [{code}] hl={locale['hl']}")
        try:
            body = page_text(
                fetch(f"https://play.google.com/store/apps/details?id={package}&hl={locale['hl']}&gl=KR")
            )
        except Exception as error:  # noqa: BLE001
            print(f"    오류  조회 실패: {error}")
            diffs += 1
            continue
        title = read_text(folder / "title.txt")
        short = read_text(folder / "short_description.txt")
        diffs += show("이름", norm(title) in body, title)
        diffs += show("짧은 설명", norm(short) in body, norm(short))
        paragraphs = [
            p for p in re.split(r"\n\s*\n", read_text(folder / "full_description.txt")) if p.strip()
        ]
        for index, paragraph in enumerate(paragraphs, 1):
            diffs += show(f"설명 {index}번째 단락", norm(paragraph) in body, norm(paragraph))
        for line in [l for l in read_text(folder / "changelogs" / "default.txt").splitlines() if l.strip()]:
            diffs += show(f"새로운 기능: {line[:40]}", norm(line) in body, norm(line))
    return diffs


def main() -> None:
    root = app_root()
    config = load_config()
    meta = root / "fastlane" / "metadata"
    app_store_diffs, skipped = check_app_store(meta, config, app_version(root))
    diffs = app_store_diffs + check_play(meta, config)
    note = f" (조회 결과가 없어 건너뛴 지역 {skipped}곳)" if skipped else ""
    print(f"\n{'모두 일치합니다' if diffs == 0 else f'{diffs}개 항목이 다릅니다'}{note}")
    sys.exit(0 if diffs == 0 else 1)


if __name__ == "__main__":
    main()
