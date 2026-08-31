# CHANGELOG

## 0.3.0

- `screenshots.appearance` 설정을 추가했습니다. `dark` 또는 `light` 를 지정하면 캡처 전에 시뮬레이터를 그 모드로 바꿉니다.

## 0.2.0

- init 이 만드는 스크린샷 라우트가 `@oube/expo/screenshots` 의 `createScreenshotScene` 을 쓰도록 바뀌었습니다. 앱에 `@oube/expo` v0.3.0 이상이 필요합니다.
- init 이 `.gitignore` 에 추가하는 키 파일 패턴을 `*.json.key`, `*.p8` 로 바꿨습니다. 이 패턴을 이미 쓰는 앱에 같은 항목이 중복으로 들어가지 않습니다.

## 0.1.0

- KnightsOfArthur 에서 쓰던 출시 자동화를 `oube.config.json` 설정으로 동작하는 공용 도구로 옮겼습니다.
- fastlane `beta`, `release` 레인. 로컬 빌드와 EAS 클라우드 빌드를 모두 지원합니다.
- `oube-release screenshots` (iOS 시뮬레이터 빌드, 장면 캡처, 베젤 합성), `oube-release metadata lint|verify`, `oube-release init`.
