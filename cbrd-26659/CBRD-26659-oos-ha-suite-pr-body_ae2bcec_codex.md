https://jira.cubrid.org/browse/CBRD-26659

## Purpose

- AS-IS: 실제 복제를 검사하는 OOS HA TC가 일반 GitHub CI의 shell에 포함돼 있었습니다.
- TO-BE: 전용 저장소의 `HA/shell`에서 HA TC를 관리합니다.

## Implementation

- `HA/shell/_40_guava`에 활성 TC 4개와 공용 harness 파일 5개를 옮겼습니다.
- 결함 재현 2개는 `.sh.disabled` 상태로 함께 보존했습니다.
- 원본 11개 파일의 내용·mode를 유지하고 경로·SHA-256 대조표를 남겼습니다.
- 기존 private-ex의 `02d023932`는 HA 4개를 일반 GitHub CI에서 제외합니다. 새 CI의 shell 계획은 3,563개에서 3,559개로 줄었습니다.

## Remarks

- Bash·Perl 문법, 원본 hash·mode, 활성 4개·비활성 2개 탐색 검사를 통과했습니다.
- Engine `e3589ae` optdebug의 격리된 native 최종 실행은 **2 PASS·2 FAIL·0 SKIP**입니다. Async·failover는 통과했고 queue·replication은 실패했습니다. 전체 4개 통과를 주장하지 않습니다.
- 최초 전체 실행은 1 PASS·3 FAIL이었고, replication 단독 실행과 원래 위치의 async 대조 실행은 통과했습니다. 변동 원인은 미확정이며 기대값은 유지했습니다.
- OOS를 지원하는 Engine과 Linux namespace 기능이 필요합니다. 전용 다중 호스트 HA job은 미실행입니다.
- HA 제외 검증 [CI 40692318846](https://github.com/CUBRID/cubrid/actions/runs/40692318846)은 FAILURE입니다. Build·SQL·medium은 성공했고, 수정하지 않은 `temp_enc_06`의 출력 비교가 실패했습니다. 추가 수정·재실행은 하지 않았습니다.
