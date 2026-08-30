# 출시 절차

레인과 스크립트는 `@oube/release` 패키지에 있고, 이 앱의 설정은 `oube.config.json` 에 있습니다.
키 파일 두 개가 필요합니다. 둘 다 `.gitignore` 에 포함되어 있으며, 잃어버리면 각 콘솔에서 다시 발급받을 수 있습니다.

- `fastlane/asc-api-key.json.key` (App Store Connect API 키)
- `fastlane/play-service-account.json.key` (Play 서비스 계정)

## 순서

1. `app.json` 과 `package.json` 의 버전을 함께 올리고 커밋합니다.
2. `fastlane/metadata/` 에 릴리스 노트를 작성하고 `pnpm oube-release metadata lint` 로 글자수 한도를 확인합니다.
3. `fastlane beta`
   프로덕션 빌드를 만들어 TestFlight 와 Play 내부 테스트 트랙에 업로드합니다.
4. 실제 기기에서 확인합니다. iOS 는 TestFlight 앱으로, Android 는 내부 테스트 참여 링크로 설치합니다.
5. `fastlane release`
   스토어 문구를 업로드하고 심사 제출과 프로덕션 승격까지 진행합니다.
   새 인앱 상품을 함께 제출할 때만 `fastlane release iap:true` 를 사용합니다.
6. 스토어에 반영된 뒤 `pnpm oube-release metadata verify` 로 게시된 문구와 로컬 파일을 비교합니다.

## 스토어 문구

원본은 `fastlane/metadata/` 에 있습니다. 항목 하나가 파일 하나이며, 수정한 내용은 다음 `fastlane release` 때 함께 업로드됩니다.
App Store 문구는 `{locale}/` 에, Google Play 문구는 `android/{locale}/` 에 있습니다 (fastlane 의 기본 폴더 구조).

## 스크린샷

`pnpm oube-release screenshots all` 을 실행하면 시뮬레이터 빌드, 장면 캡처, 베젤 합성을 한 번에 처리합니다.
결과물은 `store-assets/final/` 에 생성됩니다. 스토어 업로드는 아직 자동화되지 않아 콘솔에서 직접 올려야 합니다.
