# IPARK Cloud Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish a usable HACS fork with cloud registration and user elevator calls.
**Architecture:** Extend existing bestin cloud 2.0. Add one HTTP helper module and one static button platform; reuse existing polling/device handling.
**Tech Stack:** Python, aiohttp, Home Assistant config flow, unittest.
**Spec:** docs/superpowers/specs/2026-11-17-ipark-cloud-design.md

## Global Constraints
- Keep bestin domain and existing UUID/manual path.
- No real registration, elevator calls, or changes to live HA during development.
- Never persist verification codes/transactions in config entries or log auth payloads.
- Bounded timeouts; no automatic retry of elevator POSTs.

## Review Focus
- A lost registration response must not auto-repeat a side effect.
- Bad code/network failures preserve the flow UUID and allow retry.
- Missing site feature metadata must not enable live controls automatically.
- Expired token errors must be visible and must not duplicate calls.
- Existing UUID/IP entries keep legacy switches and sensors.

### Task 1: Cloud HTTP protocol
- [x] Add failing unittest tests for directory, registration, verify/login, shape validation, HTTP/API failures, and up/down wire format.
- [x] Implement cloud.py with CloudAPI, CloudError, validate_session and elevator_support.
- [x] Run tests and confirm success.

### Task 2: Config flow and runtime
- [x] Test registration progression, retries and no secret persistence; test button calls and existing paths.
- [x] Add cloud registration config steps and translations; preserve manual center_v2 flow.
- [x] Use shared login helper for refresh; discover elevator support during cloud startup; add up/down ButtonEntity platform.
- [x] Run relevant regressions and new tests.

### Task 3: Distribution
- [x] Document setup, migration, limitations and release; update fork metadata/version.
- [x] Run isolated offline tests, compile, translation checks and independent review.
- [ ] Push reviewed commits, verify GitHub checks, tag and publish release with HACS installation URL.

## Verification record

18 standalone offline suites passed on Python 3.12, including 7 config-flow tests with real voluptuous-serialize coverage. The official directory returned 167 entries read-only. Independent review found a form serialization blocker; corrected to text selectors with explicit submit validation, reproduced failure before the fix and verified green afterward. Actual wallpad registration and elevator behavior remain unverified.
