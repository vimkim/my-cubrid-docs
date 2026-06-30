# [CBRD-26985] OOS copyarea lock fetch crash

- JIRA: https://jira.cubrid.org/browse/CBRD-26985
- Target branch: `feat/oos`
- Code branch: `CBRD-26985-infinite-loop`

## Purpose

`function_index_skip_alter_table.sql` 의 `ALTER TABLE ... CHANGE` 회귀에서 서버가 죽고, 다음 SQL 테스트가 같은 DB 에 계속 접속을 재시도하는 문제를 막는다.

이 경로는 `OOS` (큰 가변 컬럼 값을 heap 레코드 밖으로 떼어 저장하는 방식) 확장 fetch 를 사용한다. 반환 레코드의 bytes 와 `LC_COPYAREA_ONEOBJ` metadata 가 같은 `LC_COPYAREA` 안에서 일치해야 하는데, 기존 코드는 그 계약을 보장하지 못했다.

## Implementation

문제 경로는 domain upgrade 중 전체 인스턴스를 잠그고 가져오는 흐름이다.

```text
ALTER TABLE ... CHANGE
  -> do_run_upgrade_instances_domain
    -> locator_upgrade_instances_domain
      -> xlocator_upgrade_instances_domain
        -> xlocator_lock_and_fetch_all
          -> heap_next_expand_oos / heap_get_visible_version_expand_oos
```

`LC_COPYAREA` 는 하나의 버퍼 안에서 두 방향으로 자란다.

```text
copyarea->mem
  | record bytes grow upward
  v
  [ rec0 ][ rec1 ][ free space ... ][ obj1 ][ obj0 ][ LC_COPYAREA_MANYOBJS ]
                                      ^
                                      descriptors grow downward
```

기존 `xlocator_lock_and_fetch_all` 은 heap fetch 가 항상 현재 copyarea 위치에 레코드를 써 준다고 가정했다. 그러나 OOS 확장과 heap scan-cache allocation 을 거치면 `recdes.data` 가 `LC_COPYAREA` 가 아니라 scan cache (heap scan 중 임시 record buffer 로 쓰는 영역) 를 가리킬 수 있다. 이 상태에서 `obj->offset = offset` 을 기록하면 metadata 는 copyarea 내부를 가리키지만 실제 bytes 는 다른 버퍼에 있다. 이후 루프가 `recdes.area_size` 를 copyarea 잔여 공간처럼 계속 줄이면서 descriptor 영역까지 침범할 수 있다.

수정은 `src/transaction/locator_sr.c` 의 `xlocator_lock_and_fetch_all` 에 한정한다.

- `locator_copyarea_remaining_fetch_size` 를 추가해 다음 레코드가 쓸 수 있는 payload 공간을 매번 계산한다.
- 각 heap fetch 전에 `recdes.data` 와 `recdes.area_size` 를 `(*fetch_area)->mem + offset` 기준으로 다시 세팅한다.
- instance lock 경로는 `heap_next` 로 OID 를 찾은 뒤 `heap_get_visible_version_expand_oos` 로 다시 읽으므로, 두 번째 fetch 직전에도 같은 세팅을 반복한다.
- fetch 후 `DB_ALIGN(recdes.length, MAX_ALIGNMENT)` 결과가 현재 copyarea 슬롯보다 크면 `S_DOESNT_FIT` 으로 빠져 기존 copyarea 확장 재시도 흐름을 탄다.
- fetch 가 성공했지만 `recdes.data` 가 copyarea 슬롯이 아니면, descriptor 를 만들기 전에 bytes 를 copyarea 슬롯으로 복사한다.

핵심은 descriptor 를 만들기 전에 아래 두 조건을 모두 만족시키는 것이다.

```text
obj->offset == offset
recdes.data == (*fetch_area)->mem + offset
```

이렇게 하면 `LC_RECDES_TO_GET_ONEOBJ` 로 다시 꺼낼 때 metadata 와 실제 record image 가 같은 copyarea 를 기준으로 맞아떨어진다.

## Remarks

### Test Plan

검증한 항목:

- `git diff --check`
- `locator_sr.c` server-mode single-file compile
- `locator_sr.c` SA mode (standalone, 서버와 클라이언트가 한 프로세스에서 도는 모드) single-file compile
- `release_gcc` build, base `53e8d6b9a`, SA mode 재현 SQL

재현 SQL 의 핵심 statement:

```sql
alter table t change i a int;
```

패치 전에는 `xlocator_upgrade_instances_domain` 경로에서 `SIGSEGV` 로 종료했다. 패치 후에는 같은 SQL 이 정상 종료했고, `function_index_skip_alter_table.result` 와 line-for-line 으로 일치했다. 뒤따르던 `function_index_skip_bit.sql` 도 새 core 없이 통과했다.

### Review Notes

이 PR 은 `xlocator_lock_and_fetch_all` 만 고친다. 같은 copyarea packing 형태를 가진 `xlocator_fetch_all` 은 별도 점검 후보지만, 이 티켓의 재현 경로와 직접 crash frame 은 `xlocator_lock_and_fetch_all` 이다.

`heap_get_visible_version_expand_oos` 자체의 ownership 규칙은 유지한다. heap 계층은 caller-owned buffer 가 부족하면 `S_DOESNT_FIT` 을 줄 수 있지만, copyarea descriptor 와 payload 의 경계 계산은 locator 계층이 알고 있으므로 locator 에서 최종 fit 과 pointer 위치를 확인하는 것이 맞다.

호환성 변화는 없다. SQL 문법, 저장 포맷, OOS record layout, WAL (복구 로그) format 은 바뀌지 않는다.
