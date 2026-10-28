# CBRD-27785: PR #8299의 두 축 코드 검토

작성일: 2026-10-28, Asia/Seoul. 대상 독자: PR 작성자와 리뷰어.
검토 대상은 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67...408d1352941e9d28a88b4d5c899bacf34e2ec1a0`의 변경 파일 9개다.
서로 독립된 두 검토자가 코드 규칙과 요구사항을 나눠 읽었으며, 코드 수정이나 테스트 재실행은 하지 않았다.

## Standards

명시된 규칙 위반: **0건**. 수정이 필요하다고 판단한 기본 code smell도 없다.

`CONTRIBUTING.md`, 적용되는 `src/`와 `unit_tests/` 안내 및 그보다 우선하는 개인 CUBRID 정책을 기준으로 검토했다. 새 STL allocation의 예외는 CUBRID 오류로 변환한다. legacy `.c`에 추가한 template, 기본 인자, 예외 처리와 optional owner 연산에는 INDENT 보호가 있다. OOS 테스트는 문서화된 GoogleTest 예외를 유지한다.

scalar reader와 index-key reader의 짧은 variable/OOS 분기는 이번 성능 수정에서 별도 추출이 필요하다는 발견사항으로 판단하지 않았다.

이 축은 정적 검토이며 formatting 도구나 테스트를 재실행하지 않았다. `AGENTS.user.md`는 없고 오래된 root `AGENTS.md`는 사용하지 않았다. 로컬 준비 branch에는 PR 연결이 없으므로 별도로 확인한 기존 PR #8299를 대상으로 삼았다.

## Spec

실행 가능한 수정으로 이어질 발견사항: **0건**.

- 누락·부분 구현: 허용된 reader/UPDATE 개선 범위에서 누락된 구현 요구를 찾지 못했다. 기존 전체 +2% 목표의 미달은 문서에 남아 있으며, 작성자가 현재 관측된 약 +5%를 수용하고 잔여 작업을 CBRD-27816으로 넘긴 결정과 일치한다.
- 범위: 공통 읽기, 작은 작업 배열, OOS 계획의 지연 생성, layout 재사용, pending owner 생성과 회귀 테스트·벤치마크로 한정된다. allocator 본체, reclaim, threshold 정책 및 기존 기준 2를 변경하지 않는다.
- 정합성: scalar OOS 읽기는 같은 transformer를 사용하고 transient buffer를 해제한다(`src/storage/heap_file.c:11621`, `11635`, `11637`). `data_readval`에는 COPY가 전달된다(`11357`). optional received owner는 변환이 가능한 copy-area/workspace 조건과 같은 조건에서 생성한다(`src/transaction/locator_sr.c:6119`, helper guard `4930`). OOS 계획은 index로 접근하기 전에 생성한다(`heap_file.c:13262`). `oos_read_many`는 완료 배열을 바꾼 뒤에도 head identity와 payload 길이 검사를 유지한다.

OOS 규범 문서는 전체를 읽고 SHA-256 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`을 확인했다. 변경 전부터 있던 raw-quarter-page 목표와의 차이는 이 diff가 정책을 유지하고 사용자가 threshold 변경을 제외했으므로 이번 발견사항으로 넣지 않았다.

이 축도 정적 검토다. 별도로 기록된 집중 CTest 15/15를 전체 CI, crash recovery·HA 또는 다른 platform의 통과로 확대하지 않는다. 이전 `02df4d9` 성능 측정을 새 PR binary의 실측으로 바꾸어 해석하지 않는다. 최종 3-way 수치와 판정은 [PR 검증 보고서](CBRD-27785-shared-read-update_408d135_codex.md)에 구분해 기록한다.

Standards 0건, Spec 0건이다. 각 축에서 수정이 필요한 최상위 발견사항은 없다.
