# experiment-1 — 현행 snapshot-copy flush baseline 관찰

## 질문

대량의 dirty data page를 만들고 online backup의 사전 flush를 유발했을 때, pinned CUBRID runtime에서
data-page physical write가 증가하는가? 이 관찰은 현행 `pgbuf_bcb_flush_with_wal`이 실제 workload에서
사용되는 경로라는 사실을 보강하는가?

## 가설

세 번의 동일 SQL runner는 매번 20,000개 row를 만들고 `Num_data_page_dirties > 0`을 기록한다. 통계
watcher의 active observation window에는 세 SQL workload, background activity와 `cubrid backupdb` trigger가
함께 들어간다. 이 전체 구간에서 전역 `Num_data_page_iowrites`가 before보다 after에서 증가하는지만
확인하며, 증가를 특정 caller에 귀속하지 않는다.

## 절차

1. 보고서 전용 DB `sxaio_codex`가 없음을 확인하고 생성·시작한다.
2. `start_watcher.sh`로 통계 수집을 켜고 before statdump를 기록한다.
3. 동일한 `flush_workload.sql`을 정확히 세 번 `csql -i`로 실행한다.
4. 보고서 전용 scratch directory로 `cubrid backupdb -C -r`를 실행한다. 여기서 `-r`은 archive 제거
   옵션이며 checkpoint를 뜻하지 않는다.
5. after statdump를 기록하고 watcher를 정리한다.
6. DB를 stop/delete하고 report-owned watcher와 DB가 남지 않았는지 확인한다.

첫 시도에 쓴 이름 `sx_aio_report_codex`는 CUBRID의 log-name 길이 제한(17자 미만)을 넘겨 createdb가
exit 254로 거절했다. database registry에 등록되지 않은 것을 확인한 뒤 더 짧은 전용 이름으로 바꿨다.

## 해석 경계

- runtime은 dirty-page 생성과 data-page I/O 증가를 관찰한다. DWB 경로는 DWB와 home-volume write를
  함께 집계할 수 있으므로 `Num_data_page_iowrites`를 unique page 수로 해석하지 않고 `delta > 0`만 본다.
- snapshot `memcpy`, writer와 I/O의 overlap 허용, WAL 순서, 실패 복원은 pinned source가 직접 증명한다.
- 이 실험은 SX/READ/I/O-freeze 대안의 처리량이나 writer wait를 측정하지 않는다. 아직 구현되지 않은
  대안에 대한 성능 수치는 `UNKNOWN`이다.

관련 장: `chapters/07-experiment.html#experiment-1`.
