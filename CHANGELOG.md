# Changes

## 1.5.1 — 2026-11-19

- Fix the Smart Home 2.0 wallpad registration menu in Home Assistant.
- Complete registration when the verification response is not a JSON object, after validating the resulting login session.
- Use the upstream User-Agent for cloud device requests, elevator capability checks, and elevator calls.
- Verified in one household: wallpad registration, light state retrieval, and a down elevator call without a wallpad IP.

## 1.5.0 — 2026-11-17

- Register cloud 2.0 devices entirely in HA using wallpad verification.
- Add up/down elevator call buttons without a wallpad IP.
- Discover elevator support; unknown support defaults to disabled buttons.
- Preserve manual UUID setup, cloud device entities and legacy SSE sensors.
- Validate cloud responses, bound requests, refuse auth redirects and sanitize errors.
- Preserve HA startup retry/re-auth exceptions and close failed sessions.
- Add offline protocol, config-flow, runtime and button tests.

Household registration, device control and elevator operation have not been tested live. The official complex directory was verified read-only. See README for installation and limitations.
