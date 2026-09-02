# CHANGELOG

## Unreleased

- `fastlane upload_screenshots` 레인을 추가했습니다. `store-assets/final/` 의 스크린샷을 App Store 와 Google Play 에 언어별로 업로드하고, `android.featureGraphic` 을 지정하면 Play 피처 그래픽도 함께 올립니다. iOS 는 기존 장을 지우고 새로 올리며, Android 는 바뀐 장만 올리고 로컬에 없는 장은 지워 스토어를 로컬 파일과 일치시킵니다.
- 스크린샷 빌드가 ios 폴더는 있는데 .xcworkspace 가 없는 상태(이전 pod install 실패)를 만나면 프로젝트를 다시 생성합니다. 전에는 폴더를 재사용하며 pod install 을 건너뛰어 같은 실패가 반복됐습니다. 설치 뒤 앱을 실행하던 단계는 capture 가 대신하므로 뺐습니다.
- `metadata verify` 가 조회 결과가 없는 지역(처리 중이거나 미출시)을 실패로 세지 않고 건너뛴 것으로 알립니다. 출력도 한국어로 바꿨습니다.
- 합성 문구가 두 줄을 넘거나 레이아웃이 캔버스를 넘을 때 스택트레이스 대신 메시지만 보여줍니다.
- init 이 iap-products.json 원고의 패키지 자리표시를 채우고, 스크린샷 라우트 안내가 `@oube/expo` v0.4.1 기준으로 바뀌었습니다.

## 0.3.2

- 캡처가 첫 딥링크를 열기 전에 앱을 새로 실행해 안정될 때까지 기다립니다. SpringBoard 재시작으로 앱이 종료된 채 첫 장면을 열면 스플래시가 캡처에 찍히던 문제를 고쳤습니다.

## 0.3.1

- 캡처 전에 SpringBoard 를 재시작합니다. 시뮬레이터에서 다른 앱을 쓴 적이 있으면 상태 표시줄에 그 앱으로 돌아가는 표시가 남아 스크린샷에 찍히던 문제를 고쳤습니다.

## 0.3.0

- `screenshots.appearance` 설정을 추가했습니다. `dark` 또는 `light` 를 지정하면 캡처 전에 시뮬레이터를 그 모드로 바꿉니다.

## 0.2.0

- init 이 만드는 스크린샷 라우트가 `@oube/expo/screenshots` 의 `createScreenshotScene` 을 쓰도록 바뀌었습니다. 앱에 `@oube/expo` v0.3.0 이상이 필요합니다.
- init 이 `.gitignore` 에 추가하는 키 파일 패턴을 `*.json.key`, `*.p8` 로 바꿨습니다. 이 패턴을 이미 쓰는 앱에 같은 항목이 중복으로 들어가지 않습니다.

## 0.1.0

- KnightsOfArthur 에서 쓰던 출시 자동화를 `oube.config.json` 설정으로 동작하는 공용 도구로 옮겼습니다.
- fastlane `beta`, `release` 레인. 로컬 빌드와 EAS 클라우드 빌드를 모두 지원합니다.
- `oube-release screenshots` (iOS 시뮬레이터 빌드, 장면 캡처, 베젤 합성), `oube-release metadata lint|verify`, `oube-release init`.
