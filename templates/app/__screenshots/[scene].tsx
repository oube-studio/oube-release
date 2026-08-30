import { createScreenshotScene } from '@oube/expo/screenshots';

import { applyScreenshotScene } from '@/lib/screenshot-scenes';

// 스토어 스크린샷 장면 라우트. applyScreenshotScene(scene, lang) 은 앱마다 작성한다.
// 언어를 바꾸고 장면에 필요한 데이터를 앱 상태에 넣은 뒤 보여줄 화면 경로를 반환해야 한다
export default createScreenshotScene({
  enabled: process.env.EXPO_PUBLIC_SCREENSHOT_MODE === 'true',
  apply: applyScreenshotScene,
});
