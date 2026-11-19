<!-- Posted to https://jira.cubrid.org/browse/CBRD-28073?focusedCommentId=4778780 on 2026-11-19. -->

## 후속 확인: ALTER 병합 경로의 OOS chain 중복 여부

앞 코멘트(설계 검토)의 "같은 패턴의 다른 호출처" 항목을 확인한 결과다. PR #8514 head `3960d1b215`, debug 빌드, 4K page DB, 서버 모드에서 확인했다.

### 결론

**chain이 남지 않는다.** `src/query/serial.c:2285`의 병합 경로는 실제로 새 OOS chain을 삽입한다. 그러나 같은 update의 `heap_update_home`이 이전 행이 가리키던 chain을 바로 지운다(`src/storage/heap_file.c:26247-26251`, `heap_oos_delete_unreferenced`). 삽입과 삭제 모두 사용자 트랜잭션의 undo 로그 안에서 일어난다. 그래서 NEXT VALUE 경로와 달리 롤백 일관성도 유지된다.

### 근거

- `_db_serial`은 MVCC 비활성 class다(`src/transaction/mvcc.c:696`). 그래서 클라이언트의 update는 non-MVCC 갱신이 되고, 위 즉시 삭제 분기를 탄다.
- gdb dprintf로 서버에서 `2285 → heap_attrinfo_insert_to_oos → heap_oos_delete_unreferenced` 순서를 확인했다.
- 병합 후 COMMIT, 명시적 ROLLBACK, 클라이언트 kill에 의한 abort, 45초 대기, 서버 중지 후 SA 재시작을 모두 해 보았다. 어느 경우든 `SHOW HEAP OOS OF _db_serial`의 `Oos_num_recs`는 comment가 OOS에 있는 serial 수와 같았다. `checkdb -C`와 `checkdb -S`는 통과했다. 롤백 뒤에도 이미 발급한 `current_val`은 되돌아가지 않았고, comment는 1000자 원문 그대로 읽혔다.

### 병합 경로에 도달하는 조건

일반적인 순서로는 병합에 도달하지 않았다.

- 다른 세션의 NEXT VALUE는 ALTER가 serial XASL cache를 비운 뒤 다시 컴파일한다. 이때 serial 행의 S lock을 기다리므로, ALTER가 커밋될 때까지 막힌다.
- 같은 트랜잭션 안의 NEXT VALUE나 AUTO_INCREMENT INSERT는 실행 전에 dirty serial 행을 먼저 flush한다(`src/object/object_accessor.c:3400`).

병합이 일어나려면 하나의 ALTER 문이 실행되는 동안 다른 세션의 NEXT VALUE가 cache된 XASL로 행을 갱신해야 한다. 이번 재현에서는 gdb로 ALTER 클라이언트를 멈춰 이 창을 강제로 만들었다. 실제 운영에서 얼마나 자주 일어나는지는 측정하지 않았다.

### 새로 보인 점 (이 이슈의 범위 밖)

- **comment 배치가 오간다.** 시스템 class의 행은 클라이언트에서 OOS 준비를 하지 않는다(`src/transaction/locator_sr.c:5410-5411`). 그래서 병합 없는 ALTER는 comment를 inline으로 쓰고, 병합된 ALTER는 새 chain을 만든다. 바뀔 때마다 이전 chain은 지워지므로 누수는 없다.
- **`REC_HOME`이 아닌 serial 행.** 병합은 `REC_HOME` 행에서만 실행된다(`src/storage/heap_file.c:27099`). `_db_serial` 행이 relocation이나 big-one 상태가 될 수 있는지, 그 경우 동시 NEXT VALUE 값이 보존되는지는 확인하지 않았다.
- HA 복제, release 빌드, 병합 도중의 crash 복구는 확인하지 않았다.
