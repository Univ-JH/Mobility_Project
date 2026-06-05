# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

Smart helmet integrated safety system for personal mobility devices (e-scooters, bikes). Four-layer architecture:

- **Embedded** (`embedded-helmet/`): Arduino Nano 33 BLE — helmet sensing (pressure, IMU), BLE transmission
- **Edge** (`edge-pi/`): Raspberry Pi 5 — camera AI inference (sidewalk/road), servo brake control, local state machine
- **Backend** (`backend/`): FastAPI + MongoDB + MQTT — telemetry ingestion, policy engine, emergency lifecycle
- **Frontend** (`frontend-web/`, `frontend-mobile/`): React admin dashboard, React Native (Expo) user app

---

## Development Rules (Mandatory)

**Before writing any code**, read all relevant docs in this order:
1. `.cursor/rules/` — constraint rules for the target layer
2. `AGENTS.md` and `README.md` in the target folder and its parents
3. Write a plan, get it reviewed, then implement

**Fail-Safe principle**: when uncertain (sensor error, comms loss, unknown state), default to restrict/slow/stop — never allow unsafe operation.

**Contract immutability**: MQTT payloads and API DTOs follow v1 schema. Do not add/remove/rename fields without schema versioning. `schemaVersion` is always `1` currently.

**Commit format**: `<type>: <subject>` where type is `feat`, `fix`, `refactor`, `docs`, `test`, or `chore`.

**Branch format**: `feature/<topic>`, `fix/<topic>`, `chore/<topic>`, `docs/<topic>`

---

## Backend (FastAPI / Python 3.11)

### Run

```bash
# Start infrastructure (MongoDB + MQTT broker)
docker-compose up -d mongo mqtt

# Install dependencies
cd backend
pip install -r requirements.txt

# Copy and configure env
cp .env.example .env

# Run dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Full stack via Docker

```bash
docker-compose up --build
```

### Tests

```bash
cd backend
pytest tests/
# single test
pytest tests/test_policy_engine.py::test_name -v
```

### Architecture

Strict layered architecture — never skip layers:

```
api/v1/       → FastAPI routers (HTTP only: auth, users, devices, events, policies, emergencies, admin)
services/     → Business logic (policy engine, state transitions, emergency lifecycle)
repositories/ → MongoDB CRUD via Beanie/Motor
workers/      → MQTT ingestion daemon (normalize → validate → persist)
domain/       → Pure types: DeviceState enum, ALLOWED_TRANSITIONS matrix, policy DSL types
schemas/      → Pydantic v2 DTOs for API and MQTT payloads
```

All API responses use this envelope:
```json
{ "success": true, "code": "OK", "message": "...", "data": {...}, "traceId": "..." }
```

**Device state machine** (`domain/states.py`): `IDLE → READY → RUNNING_NORMAL ↔ RUNNING_LIMITED → AUTO_BRAKING → EMERGENCY → IDLE`. Invalid transitions are stored with `anomaly=true`, never silently dropped.

**Policy engine** (`services/policy_engine.py`): Deterministic JSON-DSL evaluation. Emergency rules always win. Tie-break order: lower `targetSpeedKph` → higher `brakeLevel` → lexicographic `policyId`. Returns `mode`, `targetSpeedKph`, `brakeLevel`, `reason`, `confidence`, `appliedPolicyId`.

**MQTT ingestion**: Idempotency key is `deviceId + rideId + seq`. Duplicate messages are dropped (logged as `dup`). `eventAt` = device timestamp, `ingestedAt` = server receipt time.

**Error codes** (use catalog, no new codes): `AUTH_INVALID_CREDENTIALS`, `AUTH_TOKEN_EXPIRED`, `AUTH_FORBIDDEN`, `REQ_VALIDATION_FAILED`, `REQ_UNSUPPORTED_SCHEMA_VERSION`, `STATE_TRANSITION_INVALID`, `POLICY_CONFLICT`, `RESOURCE_NOT_FOUND`, `RESOURCE_DUPLICATED`, `INTERNAL_ERROR`, `DEPENDENCY_UNAVAILABLE`

### Env vars

See `backend/.env.example`. Key vars: `MONGODB_URL`, `DATABASE_NAME`, `MQTT_BROKER_URL`, `MQTT_PORT`, `SECRET_KEY`, `PRE_SHARED_TOKEN`, `EMERGENCY_WAIT_SEC`.

---

## Frontend Web (React 19 / TypeScript / Vite)

```bash
cd frontend-web
npm install
npm run dev       # dev server
npm run build     # production build
npm run lint      # eslint
```

Screens: Dashboard, LiveMap (Leaflet), EventLogs, Emergencies, Policies. Server state via TanStack Query. Separate API layer (`src/api/`) from screen components (`src/screens/`). Reusable logic in hooks (`src/hooks/queries/`).

Parse event fields as strict types — `severity` is `'low'|'medium'|'high'`. Unknown `schemaVersion` → isolate message, show user-facing "compatibility error", no crash.

---

## Frontend Mobile (React Native / Expo)

```bash
cd frontend-mobile
npm install
npm run start          # Expo dev server
npm run android        # Android
npm run ios            # iOS
```

Emergency notifications require confirm/cancel flow with `caseId`. Duplicate events (same `seq`) must not show twice. Background MQTT/WebSocket subscriptions must not leak — lifecycle-bound to foreground state.

---

## Edge (Raspberry Pi 5 / Python)

Located in `edge-pi/`. Sub-modules:
- `src/ai/` — YOLOv8 / Hailo-8 NPU inference for sidewalk classification
- `src/camera/` — 30fps capture + preprocessing pipeline
- `src/control/` — PWM servo brake control (calibration table required, no hardcoded angles)
- `src/state/` — Local state machine (mirrors backend states)
- `src/communication/` — BLE GATT receiver (helmet) + MQTT bridge (server)

Decision loop: stabilize over a time window before triggering brake — never act on a single frame. BLE disconnect or inference uncertainty → conservative mode (slow/stop). ACK every server control command to `device/{deviceId}/ack` with `commandId`, `result`, `reason`. Commands expire after `ttlMs`.

---

## Embedded (Arduino Nano 33 BLE)

Located in `embedded-helmet/`. Helmet sensor firmware:
- Pressure sensor + hysteresis logic for wear detection
- IMU (accel/tilt) for crash/anomaly detection
- BLE packet fields: `seq`, `timestamp`, `battery`, `rideId` (mandatory on safety events)
- Retry must reuse same `seq` for idempotency; if `seq` continuity breaks (reboot), issue new `rideId`

---

## MQTT Topic & Payload Contracts (v1)

| Topic | Direction |
|---|---|
| `device/{deviceId}/telemetry` | Device → Server |
| `device/{deviceId}/event` | Device → Server |
| `device/{deviceId}/status` | Device → Server |
| `device/{deviceId}/control` | Server → Device |
| `device/{deviceId}/ack` | Device → Server |

**All payloads require**: `schemaVersion` (1), `deviceId`, `timestamp` (ISO8601 or epoch ms — pick one), `seq`, `rideId` (mandatory on events).

Safety events must include `reason`, `severity` (`low|medium|high`), `confidence` (0–1).

Unsupported `schemaVersion` → isolate as `unsupported_schema`, log, never store.

---

## Observability

Structured log required fields: `traceId`, `correlationId`, `deviceId`, `rideId`. State-change logs add: `eventType`, `severity`, `confidence`, `stateFrom`, `stateTo`, `commandId`. Logs missing these fields are treated as incomplete.

Performance targets: event ingest-to-persist P95 < 300ms, control ACK round-trip P95 < 800ms.
