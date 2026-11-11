https://jira.cubrid.org/browse/CBRD-28011

## Purpose

- OOS(Out-of-row Overflow Storage)는 큰 컬럼 값을 heap 행 밖의 별도 파일에 저장합니다. 쿼리를 튜닝하려면 heap page를 읽은 비용과 OOS page를 읽은 비용을 따로 볼 수 있어야 합니다. ([#7990 요청](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6625292994))
- AS-IS: heap scan trace의 `fetch`, `ioread`, `time`에 OOS 읽기가 합산되어 둘을 구분할 수 없습니다.
- TO-BE: OOS 값을 읽은 scan의 trace에 OOS 몫이 따로 표시됩니다. 이 값은 기존 합계 안에 포함된 부분입니다.

## Implementation

- `oos_read`와 `oos_read_many`는 trace가 켜진 동안에만 자신의 page fix 수, 디스크 읽기 수, 시간을 thread 누적값(`OOS_READ_STATS`)에 더합니다.
- scan이 trace를 재는 모든 구간이 기존 `fetch`/`ioread`와 같은 방식으로 이 누적값의 차이를 `SCAN_STATS.oos_reads`에 더합니다. 대상 구간은 serial scan, page batch, parallel worker, partition, parallel subquery 병합입니다.
- 출력: text는 scan 줄 뒤에 `(oos time: N, fetch: N, ioread: N)`, JSON은 scan 객체 안의 `"oos"`입니다. OOS를 읽지 않은 scan에는 출력되지 않으므로 기존 trace는 바뀌지 않습니다.
- `oos fetch`는 OOS 값을 읽는 동안 일어난 모든 page fix입니다. page 할당 여부를 확인하는 fix도 포함합니다.

## Remarks

- 검증 (debug 빌드, 직접 실행한 trace):
  - 20000바이트 값 200행 full scan, cache가 빈 상태: `heap ... fetch: 2208, ioread: 401` 중 `oos ... fetch: 2200, ioread: 400`. ioread 400은 200행 × OOS page 2개와 맞습니다.
  - 같은 테이블에서 큰 컬럼을 읽지 않는 쿼리와 OOS가 없는 테이블: `oos` 출력이 없고 결과가 같습니다.
  - index lookup, partition별 줄, parallel heap/index scan(OOS fetch가 serial과 같은 7000), JSON 출력에서 `oos`를 확인했습니다.
- debug 빌드의 OOS fetch는 chunk 1개에 7번, chunk 하나가 늘 때마다 4번씩 늘었습니다. release 빌드에서는 page 검증 fix가 없으므로 수가 더 작을 것으로 예상합니다.
- 제한: parallel worker별 요약 줄(`parallel workers: ...`)에는 OOS를 따로 표시하지 않습니다. 합계 줄에는 포함됩니다.
- 이 PR은 #7990 병합 조건이 아닌 별도 후속 작업입니다.
