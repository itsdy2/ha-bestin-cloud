# BESTIN IPARK Cloud

한국 BESTIN / 현대 IPARK 월패드용 Home Assistant 커스텀 통합입니다. [dlxmax/ha-bestin-fork](https://github.com/dlxmax/ha-bestin-fork)를 포크해 **IPARK 스마트홈 클라우드 2.0 등록과 엘리베이터 호출**을 개선했습니다.

- **HA 안에서 기기 등록**: 단지 선택 → 동·호·기기 이름 → 월패드 인증번호 → 완료. Colab이나 UUID 복사가 필요 없습니다.
- **엘리베이터 상향·하향 호출 버튼**: 공식 앱의 사용자 API로 호출합니다. 월패드 IP 입력이 필요 없습니다.
- **출입문별 공동현관 열기 버튼**: 지원 단지의 출입문 목록을 조회해 로비폰 이름별 버튼을 만듭니다.
- 기존 UUID와 조명·난방 제어, IP 기반 엘리베이터 위치·방향 센서는 유지합니다.

[![HACS 저장소 추가](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=itsdy2&repository=ha-bestin-cloud&category=integration)

## 설치

1. HACS → 사용자 지정 저장소에 `https://github.com/itsdy2/ha-bestin-cloud`, 종류 **통합(Integration)** 을 추가합니다.
2. **BESTIN IPARK Cloud**를 다운로드하고 HA를 재시작합니다.
3. 설정 → 기기 및 서비스 → 통합 추가 → **BESTIN IPARK Cloud**를 선택합니다.
4. **IPARK 스마트홈 연동 → version2.0 → 월패드 인증으로 새 기기 등록**을 선택합니다.
5. 단지·동호수를 입력하고, 월패드에서 **설정 → 모바일 기기 등록 → 등록** 화면을 연 뒤 제출합니다. 월패드의 인증번호를 HA에 입력하면 됩니다.

**기존 BESTIN 사용자:** HA 백업 후 기존 HACS 저장소를 이 저장소로 교체하고 다운로드·재시작하세요. 기존 HA 통합 설정을 삭제하지 마세요. 같은 `bestin` 도메인이므로 두 저장소의 파일을 동시에 설치하면 안 됩니다. 기존 UUID와 장치 ID를 유지합니다.

[등록·오류 복구·엘리베이터 사용 안내](guide/cloud.md) · [변경 내역](CHANGELOG.md)

## 검증 범위

공식 단지 목록 조회와 오프라인 테스트를 수행했지만 **실제 세대 등록·장치 제어·엘리베이터 호출은 검증하지 않았습니다.** 단지 서버와 권한에 따라 지원이 달라집니다. 호출 성공은 도착 확인이 아닙니다.

공동현관은 공식 앱 1.5.4의 API 구조에 맞춰 구현했으며 실제 목록 조회·문 열기는 검증하지 않았습니다. 방문차량·가족 관리·신규 계정 로그인은 추가하지 않았습니다. 구글홈은 HA의 별도 Google Assistant 연결로 조명·난방 등을 노출할 수 있습니다. SmartThings로 자동 내보내는 기능은 포함하지 않습니다.

## 개발 및 출처

Python 3.12 이상: `pip install -r requirements-test.txt` 후 `python scripts/test_offline.py`.

원본 [lunDreame/ha-bestin](https://github.com/lunDreame/ha-bestin), 기반 포크 [dlxmax/ha-bestin-fork](https://github.com/dlxmax/ha-bestin-fork)에 감사드립니다. 기준 커밋은 `3bf492aa6a53ff0c18a5839492f24947b6bb2efa`입니다. 원본의 다른 기능 안내는 [README-upstream.md](README-upstream.md), 저작권·라이선스 안내는 [ABOUT.md](ABOUT.md)에 유지했습니다.
