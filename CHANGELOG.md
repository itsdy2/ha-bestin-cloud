# Changes

## Unreleased

- Discover cloud 2.0 onepass lobby doors and add one open button per door.
- Reuse current session tokens and aliases; isolate discovery failures from other devices.
- Validate door responses, encode door IDs and never retry opening requests automatically.
- Add Korean/English labels, usage instructions and offline protocol/platform/runtime tests.
- Live door listing and opening have not been tested; no running HA was modified.

## 1.5.0 — 2026-11-17

- Register cloud 2.0 devices entirely in HA using wallpad verification.
- Add up/down elevator call buttons without a wallpad IP.
- Discover elevator support; unknown support defaults to disabled buttons.
- Preserve manual UUID setup, cloud device entities and legacy SSE sensors.
- Validate cloud responses, bound requests, refuse auth redirects and sanitize errors.
- Preserve HA startup retry/re-auth exceptions and close failed sessions.
- Add offline protocol, config-flow, runtime and button tests.

Household registration, device control and elevator operation have not been tested live. The official complex directory was verified read-only. See README for installation and limitations.
