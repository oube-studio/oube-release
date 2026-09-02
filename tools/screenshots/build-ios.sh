#!/usr/bin/env bash
# 스크린샷용 iOS 시뮬레이터 Release 앱을 빌드해 설치한다. 스크린샷 모드 플래그를 켠 상태로 JS 를 번들한다.
# oube-release CLI 가 OUBE_APP_ROOT, OUBE_CONFIG 를 넘겨서 실행한다.
set -euo pipefail

: "${OUBE_APP_ROOT:?OUBE_APP_ROOT 가 없습니다. oube-release CLI 로 실행하세요}"
: "${OUBE_CONFIG:?OUBE_CONFIG 가 없습니다}"

PROJECT_DIR="$OUBE_APP_ROOT"
CONFIG="$OUBE_CONFIG"
DEVICE="${1:-iphone}"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq 가 필요합니다: brew install jq" >&2
  exit 1
fi

if ! jq -e --arg device "$DEVICE" '.screenshots.devices[$device]' "$CONFIG" >/dev/null; then
  echo "설정에 없는 기기입니다: $DEVICE" >&2
  exit 1
fi

SIMULATOR_NAME="$(jq -r --arg device "$DEVICE" '.screenshots.devices[$device].simulatorName' "$CONFIG")"
DERIVED_DATA="$PROJECT_DIR/.screenshots-derived-data"
IOS_DIR="$PROJECT_DIR/ios"
IOS_FINGERPRINT_FILE="$IOS_DIR/.screenshot-prebuild.sha256"

find_workspace() {
  find "$IOS_DIR" -maxdepth 1 -name '*.xcworkspace' -print -quit 2>/dev/null
}

# 모노레포에서는 lockfile 이 저장소 루트에 있으므로 상위 폴더로 올라가며 찾는다
find_lockfile() {
  local dir="$PROJECT_DIR"
  while [[ "$dir" != "/" ]]; do
    if [[ -f "$dir/pnpm-lock.yaml" ]]; then
      echo "$dir/pnpm-lock.yaml"
      return
    fi
    dir="$(dirname "$dir")"
  done
}

# 네이티브에 영향을 주는 파일(app.json, package.json, lockfile)이 바뀌었을 때만 prebuild 를 다시 한다.
# 프로젝트 경로가 해시에 섞이지 않도록 파일 내용만 stdin 으로 넘긴다
native_input_fingerprint() {
  local inputs=("$PROJECT_DIR/app.json" "$PROJECT_DIR/package.json")
  local lockfile
  lockfile="$(find_lockfile)"
  if [[ -n "$lockfile" ]]; then
    inputs+=("$lockfile")
  fi
  {
    for input in "${inputs[@]}"; do
      printf '%s\n' "$(basename "$input")"
      shasum -a 256 <"$input"
    done
  } | shasum -a 256 | awk '{ print $1 }'
}

write_ios_fingerprint() {
  printf '%s\n' "$1" >"$IOS_FINGERPRINT_FILE"
}

generate_ios_project() {
  (cd "$PROJECT_DIR" && npx expo prebuild --platform ios)
  write_ios_fingerprint "$1"
}

regenerate_ios_project() {
  (cd "$PROJECT_DIR" && EXPO_NO_GIT_STATUS=1 npx expo prebuild --platform ios --clean)
  write_ios_fingerprint "$1"
}

find_device() {
  xcrun simctl list devices available -j |
    jq -r --arg name "$SIMULATOR_NAME" '
      [.devices[][] | select(.name == $name and .isAvailable == true)]
      | sort_by(.state == "Booted")
      | last
      | .udid // empty
    '
}

UDID="${SCREENSHOT_DEVICE_UDID:-$(find_device)}"
if [[ -z "$UDID" ]]; then
  echo "'$SIMULATOR_NAME' 시뮬레이터가 없습니다. Xcode 에서 만들거나 SCREENSHOT_DEVICE_UDID 를 지정하세요." >&2
  exit 1
fi

CURRENT_NATIVE_FINGERPRINT="$(native_input_fingerprint)"

# expo prebuild 는 pod install 이 실패해도 정상 종료하므로, 폴더는 있는데 .xcworkspace 가 없는 상태가 남을 수 있다.
# 그 상태에서 --clean 없이 prebuild 하면 폴더를 재사용하며 pod install 을 건너뛰어 같은 실패가 반복되므로 다시 생성한다
if [[ ! -d "$IOS_DIR" ]]; then
  echo "iOS 프로젝트를 생성합니다"
  generate_ios_project "$CURRENT_NATIVE_FINGERPRINT"
elif [[ "${SCREENSHOT_REGENERATE_IOS:-0}" == "1" ]]; then
  echo "요청에 따라 iOS 프로젝트를 다시 생성합니다"
  regenerate_ios_project "$CURRENT_NATIVE_FINGERPRINT"
elif [[ ! -f "$IOS_FINGERPRINT_FILE" ]]; then
  echo "ios/ 는 스크린샷 자동화가 만든 프로젝트가 아니어서 자동으로 지우지 않습니다." >&2
  echo "네이티브 변경 사항을 확인한 뒤 한 번만 다시 생성하세요:" >&2
  echo "  SCREENSHOT_REGENERATE_IOS=1 oube-release screenshots build --device $DEVICE" >&2
  exit 1
elif [[ "$(<"$IOS_FINGERPRINT_FILE")" != "$CURRENT_NATIVE_FINGERPRINT" ]]; then
  echo "네이티브에 영향을 주는 파일이 바뀌어 iOS 프로젝트를 다시 생성합니다"
  regenerate_ios_project "$CURRENT_NATIVE_FINGERPRINT"
elif [[ -z "$(find_workspace)" ]]; then
  echo "ios/ 에 .xcworkspace 가 없어(이전 pod install 실패) iOS 프로젝트를 다시 생성합니다"
  regenerate_ios_project "$CURRENT_NATIVE_FINGERPRINT"
else
  echo "기존 iOS 프로젝트를 재사용합니다"
fi

IOS_WORKSPACE="$(find_workspace)"
if [[ -z "$IOS_WORKSPACE" ]]; then
  echo "prebuild 뒤에도 $IOS_DIR 에 .xcworkspace 가 없습니다. 위의 pod install 오류를 확인하세요." >&2
  exit 1
fi
SCHEME_NAME="$(basename "$IOS_WORKSPACE" .xcworkspace)"
APP_PATH="$DERIVED_DATA/Build/Products/Release-iphonesimulator/$SCHEME_NAME.app"

STATE="$(xcrun simctl list devices -j | jq -r --arg udid "$UDID" '.devices[][] | select(.udid == $udid) | .state')"
if [[ "$STATE" != "Booted" ]]; then
  xcrun simctl boot "$UDID"
fi
xcrun simctl bootstatus "$UDID" -b

echo "$SIMULATOR_NAME 용 스크린샷 Release 앱을 빌드합니다"
export EXPO_PUBLIC_SCREENSHOT_MODE=true
xcodebuild \
  -workspace "$IOS_WORKSPACE" \
  -scheme "$SCHEME_NAME" \
  -configuration Release \
  -sdk iphonesimulator \
  -destination "platform=iOS Simulator,id=$UDID" \
  -derivedDataPath "$DERIVED_DATA" \
  ONLY_ACTIVE_ARCH=YES \
  CODE_SIGNING_ALLOWED=NO \
  -quiet \
  build

if [[ ! -d "$APP_PATH" ]]; then
  echo "빌드된 앱이 $APP_PATH 에 없습니다." >&2
  exit 1
fi

xcrun simctl install "$UDID" "$APP_PATH"

echo "$SIMULATOR_NAME 에 스크린샷 Release 앱을 설치했습니다"
