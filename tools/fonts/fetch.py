"""oube.config.json 의 screenshots.fonts 에 적힌 폰트 파일 중 없는 것을 내려받는다.

출처를 특정 커밋과 릴리스로 고정하고 sha256 을 확인하므로 어느 Mac 에서 받아도 같은 파일이 된다.
내려받은 원본은 사용자 캐시(~/Library/Caches/oube-release/fonts)에 두고 앱 경로로 복사한다.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import app_root, load_config

GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/ade3d1533e06b2b1462ffcde8e08b129627ca360/ofl"
PRETENDARD = "https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip"
PRETENDARD_SHA256 = "04be351a74d6bf7d60c480a3087e51d185485d35a52023142af1df19eb8c428a"

# 파일명: (URL, 파일 sha256, zip 안 경로, zip sha256). 파일을 바로 받는 출처는 뒤의 둘이 None 이다.
# 새 폰트는 여기에 한 줄 추가한다
KNOWN_FONTS = {
    "NotoSansJP.ttf": (
        f"{GOOGLE_FONTS}/notosansjp/NotoSansJP%5Bwght%5D.ttf",
        "c2f3b4d463500a2ddcd3849cded1fceeb9fd6d1c32e6cbecd568453ba50fc68f",
        None,
        None,
    ),
    "NotoSansSC.ttf": (
        f"{GOOGLE_FONTS}/notosanssc/NotoSansSC%5Bwght%5D.ttf",
        "a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da",
        None,
        None,
    ),
    "NotoSansTC.ttf": (
        f"{GOOGLE_FONTS}/notosanstc/NotoSansTC%5Bwght%5D.ttf",
        "864727d210d54f2537bbe23b3a839436c3992af72de9322af5270897246bd44f",
        None,
        None,
    ),
    "Pretendard-Regular.otf": (
        PRETENDARD,
        "3ffbacde6ab8411f1d2db54bb9b1f0b3ee2a738932033722cf0388c06aed1c93",
        "public/static/Pretendard-Regular.otf",
        PRETENDARD_SHA256,
    ),
    "Pretendard-SemiBold.otf": (
        PRETENDARD,
        "c89bc43027dc7cde5726e96223376f8eec09302b2fc1f8147fd5b57cfc376118",
        "public/static/Pretendard-SemiBold.otf",
        PRETENDARD_SHA256,
    ),
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_dir() -> Path:
    base = (
        os.environ.get("OUBE_CACHE_DIR")
        or os.environ.get("XDG_CACHE_HOME")
        or Path.home() / "Library" / "Caches"
    )
    path = Path(base) / "oube-release" / "fonts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def font_paths(config: dict) -> list[str]:
    """설정에 적힌 폰트 경로 전부 (중복 제거, 순서 유지)."""
    paths: list[str] = []
    for spec in config.get("screenshots", {}).get("fonts", {}).values():
        for value in spec.values():
            if value not in paths:
                paths.append(value)
    return paths


def missing_fonts(config: dict, root: Path) -> list[Path]:
    return [root / p for p in font_paths(config) if not (root / p).exists()]


def download(url: str, target: Path) -> None:
    print(f"내려받는 중: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "oube-release"})
    with urllib.request.urlopen(request, timeout=120) as response, target.open("wb") as file:
        shutil.copyfileobj(response, file)


def verify(path: Path, expected: str) -> None:
    actual = sha256_of(path)
    if actual != expected:
        path.unlink(missing_ok=True)
        raise SystemExit(
            f"{path.name} 체크섬이 다릅니다.\n  기대: {expected}\n  실제: {actual}\n출처의 파일이 바뀐 것이니 KNOWN_FONTS 를 확인하세요."
        )


def fetch_zip_member(url: str, zip_sha: str, member: str, target: Path) -> None:
    archive = cache_dir() / Path(url).name
    if not archive.exists() or sha256_of(archive) != zip_sha:
        download(url, archive)
        verify(archive, zip_sha)
    with zipfile.ZipFile(archive) as bundle, bundle.open(member) as source, target.open("wb") as file:
        shutil.copyfileobj(source, file)


def fetch_font(target: Path) -> None:
    known = KNOWN_FONTS.get(target.name)
    if not known:
        raise SystemExit(
            f"{target} 이 없고 내려받을 출처도 등록돼 있지 않습니다. 파일을 직접 두거나 KNOWN_FONTS 에 출처를 추가하세요.\n"
            f"아는 폰트: {', '.join(KNOWN_FONTS)}"
        )
    url, sha, member, archive_sha = known
    cached = cache_dir() / target.name
    if not cached.exists() or sha256_of(cached) != sha:
        if member:
            fetch_zip_member(url, archive_sha, member, cached)
        else:
            download(url, cached)
        verify(cached, sha)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cached, target)
    print(f"+ {target}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="내려받지 않고 없는 파일만 보여준다")
    args = parser.parse_args()

    root = app_root()
    missing = missing_fonts(load_config(), root)
    if not missing:
        return
    if args.check:
        for path in missing:
            print(f"없음: {path}")
        raise SystemExit(1)
    for path in missing:
        fetch_font(path)


if __name__ == "__main__":
    main()
