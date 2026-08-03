## Purpose

[CBRD-26847](https://jira.cubrid.org/browse/CBRD-26847)은 OOS가 적용된 heap record의 visible version을 읽을 때,
호출자가 실제로 필요로 하는 형태에 맞춰 `RECDES` 소비 정책을 선택하도록 정리한다.
OOS(Out-of-row Overflow Storage)는
큰 가변 길이 값을 heap record 밖에 저장하고 record에는 OOS 참조만 남기는 기능이다.

- **AS-IS:** attribute layer, MVCC header, CHN, 존재 여부만 사용하는 호출도 OOS 값을 전부 record 안으로
  materialize했다. 필요하지 않은 OOS I/O가 발생하고, 논리적으로 확장된 record가 고정 fetch buffer보다 크면
  `S_DOESNT_FIT` 위험도 생긴다.
- **TO-BE:** materialized raw `RECDES` 바이트를 직접 소비하는 호출만
  `HEAP_RECDES_CONSUME_RAW_BYTES`를 사용한다. OOS-aware attribute layer 또는 metadata만 사용하는 호출은
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 stored-form record를 보존한다.

이 기준은 OOS 확장을 기본 동작이 아니라 raw-byte 소비자가 명시적으로 선택하는 동작으로 만든다는
[ADR-0003](https://github.com/vimkim/cubrid-oos-context/blob/main/docs/adr/0003-oos-expansion-is-opt-in.md)의 계약과 같다.

## Implementation

`HEAP_RECDES_CONSUMPTION_POLICY` 옆에 지속 가능한 선택 규칙을 기록하고, 감사한 16개 visible-version 호출을
`HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 변경했다.

| 소비 형태 | 변경한 호출 |
|---|---|
| OOS-aware attribute layer | serial 3개, SP code 1개, loaddb 1개, locator update 2개, LOB delete 1개, MVCC re-evaluation 1개 |
| header 또는 CHN만 사용 | lock dump 1개, replication prepare 1개 |
| 존재 여부만 확인 | compactdb client/server 각 1개 |
| fetch 결과·page watcher·attribute layer만 사용하고 local body는 버림 | scanrange following/prior/next 각 1개 |

raw copy area 전송, 다른 heap으로 raw 재삽입, `OR_BUF` 직접 파싱처럼 logical record bytes가 필요한 기존
소비자는 `HEAP_RECDES_CONSUME_RAW_BYTES`를 유지한다. 따라서 stored-form OOS 참조가 raw-byte 소비자에게
노출되도록 소비 계약을 뒤집지 않는다.

정책 변경 과정에서 드러난 오류 처리도 소비 계약에 맞게 보강했다.

- serial attribute Resolve 실패를 이후 계산 전에 반환한다.
- LOB delete fetch 실패를 주 오류로 보존한다. `heap_scancache_end` 반환값도 버리지 않고, 주 오류가 없을 때만
  cleanup 오류를 반환한다. 향후 cleanup이 새 오류를 반환해도 관찰 가능하다.
- MVCC re-evaluation의 scan-cache cleanup 실패는 `V_ERROR`로 변환한다.

`test_oos_sql_visible_version`에는 64 KiB OOS payload를 사용한 두 테스트를 추가했다.

- range를 설정한 뒤 `heap_scanrange_next`의 first-object fetch를 직접 호출해 OOS batch read 횟수가 0인지
  계측한다. 이번 diff의 정확한 정책을 임시로 `CONSUME_RAW_BYTES`로 되돌렸을 때 1회로 실패하고, 최종
  정책에서 0회로 통과하는 red/green을 확인했다.
- 인덱스 키만 갱신한 뒤 큰 OOS payload의 길이와 전체 값이 보존되는지 확인한다.

## Remarks

PR 기준 브랜치는 `feat/oos`다. 최종 source HEAD `89937d7bdac3d928c06b077fb80f0e6a12985a12`은 최신
`origin/feat/oos`를 conflict 없이 병합했고, 기준 브랜치 대비 변경은 의도한 11개 파일, 196 insertions,
26 deletions뿐이다. `git diff --check`도 통과했다.

병합 후 debug GCC 전체 build/install이 성공했고, 새 테스트를 포함한 OOS CTest 25개가 모두 통과했다
(실패 0개, 최종 실행 45.40초). 이는 전체 OOS suite 회귀와 `heap_scanrange_next` 정책을 검증하지만,
scanrange following/prior의 변경 branch와 locator의 두 old-record fetch 지점을 각각 직접 주입해 계측하는
테스트까지 제공한다는 뜻은 아니다. 이 지점들은 소비 흐름을 정적으로 감사했다.

`heap_scanrange_to_following()`의 non-NULL `start_oid` branch에서 `last_oid`를 fetch하는 기존 결함은 현재 유일한
production caller가 NULL을 전달해 휴면 상태이며, 이번 OOS 소비 정책 변경과 원인이 다르다. 검증된 변경에 별도
동작 수정을 섞지 않고 후속 이슈로 분리했다.

SQL 문법, 저장 형식, WAL 형식, 외부 API는 바뀌지 않는다. PR 게시 뒤에는 exact-head를 다시 확인하고 기존
`/run` 요청이 없는 경우에만 `/run all`을 한 번 게시해 SQL, medium, shell CI를 실행한다.
