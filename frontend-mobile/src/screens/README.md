# frontend-mobile/src/screens

화면 단위 UI를 구성하는 영역이다. 응급 알림, 장치 상태, 이벤트 목록/상세 등 화면을 배치한다.

## 호환성
- 응급/경고 UX는 backend의 `caseId` 또는 동일 식별자를 기준으로 중복 표시를 방지한다.

## 확장성
- 화면 추가 시 기존 navigation/state 패턴을 유지한다.

## 가시성/명확성
- 화면은 loading/error/ready 상태를 명시적으로 다룬다.

