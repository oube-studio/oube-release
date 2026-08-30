"""oube.config.json 을 읽는다. 앱 폴더와 설정 파일 경로는 oube-release CLI 가 환경 변수로 넘긴다."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def app_root() -> Path:
    value = os.environ.get("OUBE_APP_ROOT")
    if not value:
        sys.exit("OUBE_APP_ROOT 가 없습니다. 이 스크립트는 oube-release CLI 를 통해 실행하세요.")
    return Path(value)


def load_config() -> dict:
    path = Path(os.environ.get("OUBE_CONFIG") or app_root() / "oube.config.json")
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def app_version(root: Path) -> str:
    with (root / "app.json").open(encoding="utf-8") as file:
        return json.load(file)["expo"]["version"]


def read_text(path: Path) -> str:
    if not path.exists():
        sys.exit(f"메타데이터 파일이 없습니다: {path}")
    return path.read_text(encoding="utf-8").rstrip("\n")
