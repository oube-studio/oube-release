# @oube/release

oube 의 Expo 앱들이 공통으로 사용하는 스토어 출시 도구입니다. 앱마다 복사해서 쓰던 fastlane 레인, 스크린샷 자동화,
스토어 문구 검사를 한곳에서 관리합니다. 앱에 포함되는 런타임 코드는 [@oube/expo](https://github.com/oube-studio/oube-expo) 에 있고,
이 패키지는 개발 환경과 CI 에서만 실행됩니다.

## 설치

```bash
pnpm add -D github:oube-studio/oube-release#v0.2.0
```

버전은 항상 태그로 지정합니다. `#main` 을 사용하면 설치 시점에 따라 다른 코드가 설치되어 같은 결과를 보장할 수 없습니다.

필요한 도구: fastlane, jq, python3 와 Pillow, numpy (`python3 -m pip install Pillow numpy`), Xcode 와 시뮬레이터, EAS CLI.
빠진 도구가 있는지는 `pnpm oube-release doctor` 로 확인할 수 있습니다.

## 앱에 적용하기

```bash
cd <앱 폴더>             # app.json 이 있는 폴더. 모노레포라면 apps/mobile
pnpm oube-release init  # app.json 의 값을 채워 넣은 oube.config.json 을 생성합니다
# oube.config.json 을 작성한 뒤
pnpm oube-release init  # fastlane/, 스토어 문구 폴더, 스크린샷 라우트를 생성하고 .gitignore 에 필요한 항목을 추가합니다 (이미 있는 파일은 유지)
```

키 파일 두 개는 앱의 `fastlane/` 폴더에 둡니다. `.gitignore` 에 포함되어 있으며, 잃어버리면 각 콘솔에서 다시 발급받을 수 있습니다.

- `fastlane/asc-api-key.json.key` (App Store Connect API 키)
- `fastlane/play-service-account.json.key` (Play 서비스 계정)

## 명령어

| 명령어                                                          | 설명                                                                                        |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `fastlane beta`                                                 | 프로덕션 빌드를 만들어 TestFlight 와 Play 내부 테스트 트랙에 업로드합니다                   |
| `fastlane release [iap:true]`                                   | 스토어 문구를 업로드하고 iOS 심사 제출과 Play 프로덕션 승격까지 진행합니다                  |
| `pnpm oube-release screenshots all`                             | 모든 기기와 언어의 스크린샷을 생성합니다 (시뮬레이터 빌드, 캡처, 합성)                      |
| `pnpm oube-release screenshots run --device iphone --locale ko` | 특정 기기와 언어의 스크린샷만 생성합니다 (`--skip-build` 로 빌드 생략)                      |
| `pnpm oube-release screenshots build\|capture\|compose`         | 각 단계를 따로 실행합니다                                                                   |
| `pnpm oube-release fonts`                                       | 설정에 지정된 폰트 중 없는 파일을 내려받습니다 (compose 전에 자동 실행)                     |
| `pnpm oube-release metadata lint`                               | 스토어 문구와 인앱 상품 원고의 글자수 한도를 검사하고, 두 스토어의 문구가 다르면 경고합니다 |
| `pnpm oube-release metadata verify`                             | 스토어에 실제로 게시된 문구와 로컬 파일을 비교합니다                                        |
| `pnpm oube-release doctor`                                      | 필요한 도구가 설치되어 있는지 확인합니다                                                    |

fastlane 명령어는 앱 폴더에서 실행합니다. 앱의 `fastlane/Fastfile` 은 두 줄로, 설치된 이 패키지의 레인을 import 합니다.
패키지 설치 위치는 앱마다 다르기 때문에(모노레포에서는 저장소 루트의 `node_modules`) 경로를 하드코딩하지 않고
`node -p "require.resolve(...)"` 로 찾습니다.

## oube.config.json

앱 폴더에 둡니다. 스키마는 `schema/oube.config.schema.json` 을 참고합니다.

```jsonc
{
  "scheme": "huddle", // app.json 의 scheme. 스크린샷 장면을 여는 딥링크에 사용
  "ios": { "bundleId": "studio.oube.huddle" },
  "android": { "package": "studio.oube.huddle" },
  "build": "local", // local 또는 eas-cloud
  "iap": false, // true 면 init 이 fastlane/iap-products.json 원고를 생성
  "locales": {
    // 앱의 언어 코드별 스토어 로케일
    "ko": { "appStore": "ko", "play": "ko-KR", "storefront": "kr", "hl": "ko" },
    "en": { "appStore": "en-US", "play": "en-US", "storefront": "us", "hl": "en" },
  },
  "screenshots": {
    "devices": {
      // 키가 --device 옵션 값
      "iphone": {
        "simulatorName": "iPhone 17 Pro Max",
        "canvas": [1320, 2868],
        "bezel": "iphone-17-pro-max",
        "frameWidthFraction": 0.86,
        "anchor": "bottom",
      },
      "ipad": {
        "simulatorName": "iPad Pro 13-inch (M5)",
        "canvas": [2064, 2752],
        "bezel": "ipad-pro-m4-13",
        "rotateBezel": 90,
        "frameWidthFraction": 0.68,
        "anchor": "center",
      },
    },
    "style": {
      "background": [16, 16, 16], // 단색 [r, g, b] 또는 그라디언트 { "top": [...], "bottom": [...] }
      "noise": false,
      "headlineColor": [255, 255, 255],
      "subheadlineColor": [255, 255, 255],
    },
    "fonts": {
      // 경로는 앱 폴더 기준. default 는 따로 지정하지 않은 언어에 적용
      "default": {
        "regular": "store-assets/fonts/Pretendard-Regular.otf",
        "semibold": "store-assets/fonts/Pretendard-SemiBold.otf",
      },
      "ja": { "variable": "store-assets/fonts/NotoSansJP.ttf" },
      "zh-Hans": { "variable": "store-assets/fonts/NotoSansSC.ttf" },
    },
    "scenes": [
      // 배열 순서대로 스토어에 게시
      {
        "id": "home",
        "copy": {
          "ko": { "headline": "...", "subheadline": "..." },
          "en": { "headline": "...", "subheadline": "..." },
        },
      },
    ],
  },
}
```

- `build`: `local` 은 현재 Mac 에서 `eas build --local` 로 빌드하고, `eas-cloud` 는 EAS 서버에서 빌드한 파일을 내려받아 업로드합니다.
- `screenshots.appearance`: `dark` 또는 `light`. 캡처 전에 시뮬레이터를 이 모드로 바꿉니다. 다크 모드 앱은 `dark` 로 지정합니다.
- 베젤: 모든 앱이 같은 기기 프레임을 쓰도록 패키지에 `iphone-17-pro-max` 와 `ipad-pro-m4-13` 두 개만 포함합니다.
  다른 기기가 꼭 필요하면 앱 폴더 기준 PNG 경로를 지정합니다 (`.png` 로 끝나면 경로로 인식).
- 폰트: 파일이 없으면 `fonts` 명령어가 고정된 출처(Google Fonts 의 특정 커밋에 있는 Noto Sans JP/SC/TC, Pretendard 1.3.9 릴리스)에서
  내려받고 sha256 으로 검증합니다. 다른 폰트를 사용하려면 파일을 직접 넣거나 `tools/fonts/fetch.py` 의 `KNOWN_FONTS` 에 출처를 추가합니다.

## 앱에 있어야 하는 파일

- `app/__screenshots/[scene].tsx`: init 이 생성합니다. `@oube/expo/screenshots` 의 `createScreenshotScene` 을 쓰므로
  `@oube/expo` v0.3.0 이상이 설치되어 있어야 합니다. 스크린샷 빌드(`EXPO_PUBLIC_SCREENSHOT_MODE=true`)에서만 동작하며,
  `applyScreenshotScene(scene, lang)` 을 호출한 뒤 반환된 경로로 이동합니다.
- `lib/screenshot-scenes.ts`: 앱마다 직접 구현합니다. 언어를 설정하고 장면에 필요한 데이터(예시 사용자, 고정된 기록 등)를 앱 상태에 넣은 뒤
  이동할 화면 경로를 반환합니다. 화면 구성과 데이터 구조가 앱마다 달라 공통화하지 않습니다.
- 캡처 스크립트는 `<scheme>:///__screenshots/<scene>?lang=<locale>` 딥링크로 장면을 엽니다. 로그인이 필요한 앱은
  스크린샷 모드에서 로그인 없이도 해당 화면에 진입할 수 있어야 합니다.
- `fastlane/metadata/`: 스토어 문구의 원본입니다. 폴더 구조는 init 이 생성한 `fastlane/metadata/README.md` 를 참고합니다.
- `store-assets/`: 캡처 원본(`captures/`), 합성 결과(`final/`), 미리보기(`contact-sheets/`), 폰트(`fonts/`).
  모두 명령어로 다시 만들 수 있는 파일이라 init 이 `.gitignore` 에 추가합니다.

## 결과 파일

```
store-assets/captures/<device>/<locale>-<NN>-<scene>.png   시뮬레이터 캡처 원본
store-assets/final/<device>/<locale>/<NN>-<scene>.png      스토어에 업로드할 합성 이미지
store-assets/contact-sheets/<device>-<locale>.png          한 언어의 결과를 한 장에 모은 미리보기
```

합성 규격은 캔버스 폭 1320px 기준으로 헤드라인 88px SemiBold, 부제 56px Regular, 자간 -3%, 문구와 기기 사이 간격 96px 이며,
캔버스 폭이 다르면 비례해서 조정합니다. iPhone 은 좌우와 아래 여백을 같게 두고(`anchor: bottom`), iPad 는 세로 중앙에 배치합니다(`anchor: center`).

## 개발

```bash
pnpm install
pnpm hooks    # 클론 후 한 번 실행하면 pre-commit 훅이 활성화됩니다
pnpm verify   # shellcheck, ruff, ruby -c, prettier, node:test, unittest
```

로컬에서는 `brew install shellcheck ruff` 와 `python3 -m pip install -r tools/requirements.txt` 가 필요합니다.
GitHub Actions 에서도 같은 `pnpm verify` 를 실행합니다.

앱에서 바로 확인할 때는 `pnpm link ~/codes/oube-release` 를 사용합니다. EAS 빌드는 링크를 인식하지 못하므로 빌드 전에 태그 참조로 되돌려야 합니다.

## 릴리스

1. KnightsOfArthur 에서 동작을 확인합니다. 새 버전은 항상 이 앱에서 먼저 검증한 뒤 다른 앱에 적용합니다.
2. `CHANGELOG.md` 의 `## Unreleased` 아래에 변경 내용을 적고 커밋합니다.
3. `pnpm version minor` (또는 `patch`, `major`) 를 실행합니다. 버전을 올리고, 위 설치 예시의 태그와 `CHANGELOG.md` 의
   `## Unreleased` 제목을 새 버전으로 바꾸고, `chore: release vX.Y.Z` 커밋과 태그를 만들어 push 까지 진행합니다.
4. 앱에서 태그를 올리고 테스트합니다.

0.x 버전에서는 minor 업데이트에서도 호환성이 깨질 수 있습니다. 위험한 변경은 `v0.2.0-rc.1` 같은 rc 버전으로 먼저 검증합니다.

## 포함 기준

스토어 출시와 관련된 코드는 모두 이 패키지에 둡니다. 앱마다 다른 값은 `oube.config.json` 으로 받고,
특정 앱의 코드나 문구는 포함하지 않습니다. 한 앱에서만 사용하는 기능은 그 앱에 두고, 다른 앱에서도 필요해지면 이쪽으로 옮깁니다.
