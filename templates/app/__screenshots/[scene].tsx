import { useEffect } from 'react';
import { View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';

import { applyScreenshotScene } from '@/lib/screenshot-scenes';

// 스토어 스크린샷 장면 라우트. 스크린샷 빌드(EXPO_PUBLIC_SCREENSHOT_MODE=true)에서만 동작하고,
// 그 외에는 홈으로 보낸다. 캡처 스크립트가 <scheme>:///__screenshots/<scene>?lang=<locale> 로 연다.
// applyScreenshotScene(scene, lang) 은 앱마다 작성한다: 언어를 바꾸고 장면에 필요한 데이터를 넣은 뒤 보여줄 화면 경로를 반환한다.
const SCREENSHOT_MODE = process.env.EXPO_PUBLIC_SCREENSHOT_MODE === 'true';

export default function ScreenshotScene() {
  const { scene, lang } = useLocalSearchParams<{ scene?: string; lang?: string }>();

  useEffect(() => {
    if (!SCREENSHOT_MODE || typeof scene !== 'string') {
      router.replace('/');
      return;
    }
    void applyScreenshotScene(scene, typeof lang === 'string' ? lang : undefined).then((route) =>
      router.replace(route as never)
    );
  }, [lang, scene]);

  return <View className="flex-1 bg-background" />;
}
