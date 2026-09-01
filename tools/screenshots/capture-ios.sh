#!/usr/bin/env bash
# 설치된 스크린샷 앱에서 설정에 적힌 장면을 하나씩 딥링크로 열어 캡처한다.
# 결과: <앱 폴더>/store-assets/captures/<device>/<locale>-<NN>-<scene>.png
set -euo pipefail

: "${OUBE_APP_ROOT:?OUBE_APP_ROOT 가 없습니다. oube-release CLI 로 실행하세요}"
: "${OUBE_CONFIG:?OUBE_CONFIG 가 없습니다}"

PROJECT_DIR="$OUBE_APP_ROOT"
CONFIG="$OUBE_CONFIG"
DEVICE="${1:-iphone}"
LOCALE="${2:-ko}"

if ! command -v jq >/dev/null 2>&1; then
  echo "jq 가 필요합니다: brew install jq" >&2
  exit 1
fi

if ! jq -e --arg device "$DEVICE" '.screenshots.devices[$device]' "$CONFIG" >/dev/null; then
  echo "설정에 없는 기기입니다: $DEVICE" >&2
  exit 1
fi

if ! jq -e --arg locale "$LOCALE" '.locales[$locale]' "$CONFIG" >/dev/null; then
  echo "설정에 없는 언어입니다: $LOCALE" >&2
  exit 1
fi

if ! jq -e --arg locale "$LOCALE" 'all(.screenshots.scenes[]; .copy[$locale] != null)' "$CONFIG" >/dev/null; then
  echo "$LOCALE 문구가 없는 장면이 있습니다" >&2
  exit 1
fi

SIMULATOR_NAME="$(jq -r --arg device "$DEVICE" '.screenshots.devices[$device].simulatorName' "$CONFIG")"
BUNDLE_ID="$(jq -r '.ios.bundleId' "$CONFIG")"
SCHEME="$(jq -r '.scheme' "$CONFIG")"
EXPECTED_WIDTH="$(jq -r --arg device "$DEVICE" '.screenshots.devices[$device].canvas[0]' "$CONFIG")"
EXPECTED_HEIGHT="$(jq -r --arg device "$DEVICE" '.screenshots.devices[$device].canvas[1]' "$CONFIG")"
STATUS_BAR_TIME="$(jq -r '.screenshots.statusBarTime // "9:41"' "$CONFIG")"
APPEARANCE="$(jq -r '.screenshots.appearance // empty' "$CONFIG")"
CAPTURE_DELAY="${SCREENSHOT_CAPTURE_DELAY:-$(jq -r '.screenshots.captureDelaySeconds // 3' "$CONFIG")}"
CAPTURE_DIR="$PROJECT_DIR/store-assets/captures/$DEVICE"

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

STATE="$(xcrun simctl list devices -j | jq -r --arg udid "$UDID" '.devices[][] | select(.udid == $udid) | .state')"
if [[ "$STATE" != "Booted" ]]; then
  xcrun simctl boot "$UDID"
fi
xcrun simctl bootstatus "$UDID" -b

if ! xcrun simctl get_app_container "$UDID" "$BUNDLE_ID" app >/dev/null 2>&1; then
  echo "'$SIMULATOR_NAME' 에 앱이 없습니다. 먼저 oube-release screenshots build --device $DEVICE 를 실행하세요." >&2
  exit 1
fi

mkdir -p "$CAPTURE_DIR"

# iOS 는 simctl 로 커스텀 URL 스킴을 처음 열 때 확인 창을 띄운다. 이 앱의 스킴만 미리 승인해 둔다
APPROVAL_KEY="com.apple.CoreSimulator.CoreSimulatorBridge-->$SCHEME"
xcrun simctl spawn "$UDID" defaults write \
  com.apple.launchservices.schemeapproval \
  "$APPROVAL_KEY" \
  "$BUNDLE_ID"

reset_status_bar() {
  xcrun simctl status_bar "$UDID" clear >/dev/null 2>&1 || true
}
trap reset_status_bar EXIT

# 시뮬레이터에서 다른 앱을 쓴 적이 있으면 상태 표시줄에 그 앱으로 돌아가는 표시가 남아 캡처에 찍힌다.
# 이 표시는 앱을 다시 실행해도 사라지지 않고 SpringBoard 를 재시작해야 사라진다.
# 상태 표시줄 재정의도 함께 초기화되므로 재정의보다 먼저 실행한다
xcrun simctl spawn "$UDID" launchctl kickstart -k user/foreground/com.apple.SpringBoard
sleep 6

# appearance 가 지정되어 있으면 캡처 전에 시뮬레이터를 그 라이트/다크 모드로 바꾼다
if [[ -n "$APPEARANCE" ]]; then
  xcrun simctl ui "$UDID" appearance "$APPEARANCE"
fi

xcrun simctl status_bar "$UDID" override \
  --time "$STATUS_BAR_TIME" \
  --batteryState discharging \
  --batteryLevel 100 \
  --wifiBars 3 \
  --cellularMode active \
  --cellularBars 4

# SpringBoard 재시작으로 앱이 함께 종료될 때가 있다. 그 상태로 첫 딥링크를 열면 콜드 스타트의
# 스플래시가 캡처에 찍힐 수 있어, 캡처 전에 앱을 새로 실행해 두고 안정될 때까지 기다린다
xcrun simctl launch --terminate-running-process "$UDID" "$BUNDLE_ID" >/dev/null
sleep 5

count=0
while IFS=$'\t' read -r order scene; do
  printf -v number '%02d' "$order"
  output="$CAPTURE_DIR/$LOCALE-$number-$scene.png"
  url="$SCHEME:///__screenshots/$scene?lang=$LOCALE"

  echo "$SIMULATOR_NAME 에서 $scene 을 엽니다"
  xcrun simctl openurl "$UDID" "$url"
  sleep "$CAPTURE_DELAY"
  xcrun simctl io "$UDID" screenshot --type=png "$output"

  actual_width="$(sips -g pixelWidth "$output" | awk '/pixelWidth/ { print $2 }')"
  actual_height="$(sips -g pixelHeight "$output" | awk '/pixelHeight/ { print $2 }')"
  if [[ "$actual_width" != "$EXPECTED_WIDTH" || "$actual_height" != "$EXPECTED_HEIGHT" ]]; then
    echo "$output 크기가 ${actual_width}x${actual_height} 입니다. 기대값 ${EXPECTED_WIDTH}x${EXPECTED_HEIGHT}." >&2
    exit 1
  fi
  count=$((count + 1))
done < <(jq -r '.screenshots.scenes | to_entries[] | [.key + 1, .value.id] | @tsv' "$CONFIG")

echo "$CAPTURE_DIR 에 장면 $count 개를 캡처했습니다"
