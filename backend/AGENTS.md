# Backend 폴더 전용 AI 개발 규칙

이 폴더 내에서 백엔드 코드를 작성하거나 수정할 때 AI는 아래에 명시된 주요 규칙과 헥사고날/레이어드 아키텍처 원칙을 최우선으로 지켜야 합니다.

## 핵심 규칙
1. **역할(Layer) 분리 원칙**: 
   - `api` 레이어에는 절대로 비즈니스 로직을 작성하지 마세요. 비즈니스 로직은 `services`로 넘기고, API 라우터는 얇게(Thin) 유지합니다. 
   - DB 통신은 반드시 추상화된 `repositories`를 통해서만 진행합니다.
2. **비동기 기본 (Async-first)**: FastAPI 환경 구성에 맞게 모든 네트워크 통신, DB 쿼리(motor 사용) 및 연산 모듈은 블로킹되지 않도록 비동기(`async` / `await`) 패턴 적용을 강제합니다.
3. **Pydantic 스키마 검증**: 인풋과 아웃풋, 특히나 MQTT에서 들어오는 거친 페이로드까지 `schemas/`에 정의된 Pydantic 모델을 거쳐야 합니다. 오염된 스키마는 422 언프로세서블 엔티티 에러로 일관성 있게 튕겨냅니다.
4. **멱등성(Idempotence) 구조**: MQTT 워커 디렉터리(`workers/`) 내 작업자는 전송 재시도(Retry)로 인해 같은 페이로드가 들어오는 경우를 감당해야 합니다. `deviceId` + `rideId` + `seq` 기준 조합키를 인덱싱하여 중복 처리를 방어하세요.
5. **Cursor Rules 참고**: `.cursor/rules/10-backend-fastapi-python.mdc`를 기반 프레임으로 활용합니다.
