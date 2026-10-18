# 우아달력 생성 스크립트

- `build_site.py` — 전체 사이트 생성 (`python scripts/build_site.py`, 약 4초, 2,258페이지). 먼저 `pip install -r scripts/requirements.txt`.
- `engine.py` — 음력(korean-lunar-calendar), 24절기(ephem 태양 시황경), 일진·건제12신·황도, 공휴일/대체공휴일, 택일 판정.
- `common.py` / `content.py` — 레이아웃·공통 컴포넌트 / 공휴일·절기 설명 텍스트.
- `check_engine.py`, `check_site.py`, `test_converter.js` + `test_converter.py` — 검증(엔진 대조, 링크·메타 점검, 음력 변환기 JS↔파이썬 대조).
- 연도 확장: `common.py` 의 `YEARS`, 선거일·임시공휴일은 `engine.py` 의 `ELECTIONS`/`TEMP`.
- 공휴일 규칙은 2026년 개정(노동절·제헌절 공휴일, 대체공휴일 확대) 반영. 새 임시공휴일이 발표되면 `TEMP` 에 추가 후 재생성.
