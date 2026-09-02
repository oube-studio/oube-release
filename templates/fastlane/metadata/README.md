# 스토어 문구

App Store 와 Google Play 에 게시하는 문구의 원본입니다. 항목 하나가 파일 하나입니다.

이 폴더 바로 아래의 언어별 폴더는 App Store 용이고, Google Play 용은 `android/` 아래에 있습니다.
구조가 비대칭인 것은 fastlane 의 기본 경로를 그대로 따르기 때문입니다.

- App Store (fastlane deliver): `{locale}/name.txt`, `subtitle.txt`, `promotional_text.txt`,
  `description.txt`, `keywords.txt`, `release_notes.txt`, URL 파일 3개(marketing, privacy, support). 이 폴더에 `copyright.txt`.
- Google Play (fastlane supply): `android/{locale}/title.txt`, `short_description.txt`,
  `full_description.txt`, `changelogs/default.txt`.

언어 폴더 이름은 `oube.config.json` 의 `locales` 에서 정의합니다 (App Store 폴더 → Play 폴더 예: ko → ko-KR, en-US → en-US, ja → ja-JP, zh-Hans → zh-CN).

## 작업 순서

- 문구 수정 후 글자수 확인: `pnpm oube-release metadata lint`
- 스토어 반영 후 비교: `pnpm oube-release metadata verify`
- 인앱 상품 이름과 설명의 원본: `../iap-products.json` (인앱 상품이 있는 앱만)

스크린샷과 그래픽 원본은 `store-assets/` 에 있습니다. `fastlane upload_screenshots` 가 두 스토어에 올리며,
Google Play 쪽 배열 경로인 `android/{locale}/images/` 는 `.gitignore` 에 포함되어 있습니다.
