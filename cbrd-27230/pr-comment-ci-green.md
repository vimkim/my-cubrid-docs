@hornetmj @beyondykk9 리뷰 지적을 반영하고 CI를 다시 돌렸습니다.

- `7e73eafc63`: OOS 복제 항목이 바로 뒤 행의 `RVREPL_DATA_UPDATE` 와 함께 기록되거나 함께 버려지도록 고쳤습니다. savepoint·문장 롤백과 `INCR()` flush mark 두 경우를 모두 다룹니다.
- `4d6eeb345e`: 이 규칙을 debug 빌드에서 `repl_oos_items_follow_row` assert로 확인합니다. HA를 켠 savepoint 롤백·`INCR()` test를 추가했고, 수정 전 코드에서는 assert가 4개 test에서 걸립니다.
- CI: 모든 gha-ci 검사가 통과했습니다 (https://github.com/CUBRID/cubrid/actions/runs/44462717809). shell `bug_bts_5492` 는 첫 실행에서 broker CAS 대기 시간 초과로 실패했고, 다시 돌려 통과했습니다. 다른 PR에서도 실패한 적이 있는 일시적인 실패입니다.
- 같은 원인(외래 키 오류로 롤백된 UPDATE의 행 복제 레코드가 NULL lsa로 남는 문제)이 develop에도 있어 CBRD-28251로 따로 등록했습니다. 이 PR 범위는 아닙니다.

다시 봐 주시면 감사하겠습니다.
