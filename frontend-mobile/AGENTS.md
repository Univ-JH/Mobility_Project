# Frontend-Mobile 폴더 전용 AI 개발 규칙

이동장치 주행자용 어플리케이션(React Native/TypeScript)을 위한 개발 규칙입니다.

## 핵심 규칙
1. **가독성 기반 빠른 인지 (UX)**: 주행이라는 극단적 상황에서 모바일 화면을 잠깐 볼 가능성을 생각하여 글씨보단 크고 직관적인 아이콘, 빨강(경고)/주황(제한)/초록(정상) 등의 안전 색공간을 적극 이용하여 UI를 묶어주세요.
2. **응급 방어 로직의 최상단 배치 (Z-Index)**: 사용자가 앱 내 어디를 보고 있던 간에 서버(혹은 Push)로 부터 사고(응급) 경고 카운트다운을 수신(수신 채널: Websocket/푸시/폴링 등)했다면 가장 높은 `Z-Index` 혹은 최상위 독립 React Native Navigation Modal 트리로 전체 뷰를 덮어버려야 합니다. 
3. **상태 관리에 집중 분리 (Decoupling)**: 비동기 데이터 로딩 스피너 등의 서버 사이드 상태는 `React Query`에 전담시키며, 네비게이션 탭의 현재 인덱스 등의 아주 부위별 뷰 상태만 로컬 State/Zustand로 분리해 유지보수성을 끌어올리세요.
4. **Typescript 철저**: 컴포넌트 간 Props나, React Query로부터 돌아오는 제네릭 리스폰스 등은 무조건 명시된 `interface`를 거쳐야 합니다. 타입 단언(`as`) 혹은 `any`의 사용을 원천 차단합니다.
5. **Cursor Rules**: 상세한 RN 특수 구조 룰은 `.cursor/rules/30-mobile-react-native.mdc`를 기반으로 구동합니다.
