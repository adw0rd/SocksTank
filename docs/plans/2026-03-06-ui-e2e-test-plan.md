# UI E2E Test Plan and Coverage

## Goal
Validate the full web control surface through end-to-end browser flows with mocked backend APIs and mocked WebSocket telemetry.

## Scope
- App shell and live status rendering
- Motor control, keyboard driving, mode switching, emergency stop
- Servo control and LED control interactions
- Inference mode + remote GPU server management
- Config save flow
- Places workflow: create, upload, annotate, quick-check, train
- Photo annotator loading state while switching frames

## Test Environment
- Framework: Playwright
- Browser: Chromium (headless in CI)
- Frontend app served via `vite preview`
- API + WS mocked per test (deterministic state and request capture)

## Specs
- `frontend/tests/e2e/app-shell.spec.ts`
- `frontend/tests/e2e/motor-mode-estop.spec.ts`
- `frontend/tests/e2e/servo-led.spec.ts`
- `frontend/tests/e2e/inference-servers.spec.ts`
- `frontend/tests/e2e/config-panel.spec.ts`
- `frontend/tests/e2e/places-workflow.spec.ts`
- `frontend/tests/e2e/places-annotator-loading.spec.ts`
- `frontend/tests/e2e/edge-cases.spec.ts`

## Coverage Matrix
| UI Area | Covered | Notes |
|---|---|---|
| Header chips (camera/backend/e-stop) | Yes | Validates telemetry-driven labels |
| Video panel | Yes | Checks stream element and fullscreen control presence |
| Status bar | Yes | Verifies core status fields render |
| Sensor block | Yes | Verifies temperature/distance tiles render |
| Motor control buttons | Yes | Mouse hold + stop command assertions |
| Motor keyboard hotkeys | Yes | Keydown/keyup command flow |
| Mode selector | Yes | Manual to AI command coverage |
| E-STOP button | Yes | Latch command coverage |
| Servo claw power toggle | Yes | `servo_power` command assertions |
| Aux servo expand/collapse | Yes | Visibility and helper text |
| LED color + presets | Yes | RGB and effect commands |
| Inference mode switch | Yes | API request assertion |
| GPU server start | Yes | Start request + status transition |
| GPU server add | Yes | Modal flow and persistence in list |
| Config confidence save | Yes | PUT payload assertion |
| Places create | Yes | Add place flow |
| Places upload | Yes | Multi-image upload flow |
| Places annotation save | Yes | Canvas draw + save request |
| Places quick-check | Yes | Trigger and result feedback |
| Places train | Yes | Train trigger and job cards |
| Annotator loading overlay | Yes | Switch-frame loading behavior |
| Empty places and empty GPU list | Yes | Empty state rendering |
| Places create backend error | Yes | Error message rendering |
| Quick-check and train backend failures | Yes | Failure feedback rendering |

## Known Gaps
- Fullscreen API state transitions are not deeply asserted (only control presence).
- Visual styling regressions are not covered (functional checks only).
- No cross-browser matrix yet (Chromium only).

## CI Execution
GitHub Actions uses split workflows:
- `Tests` workflow: backend unit tests on push and pull_request.
- `UI E2E` workflow: Playwright e2e on pull_request, manual dispatch, and nightly schedule.

Playwright stores `trace`, `screenshot`, and `video` only on failure, and CI uploads those artifacts only when the run fails.
