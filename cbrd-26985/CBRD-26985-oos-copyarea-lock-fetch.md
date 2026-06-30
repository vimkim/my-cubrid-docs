# [CBRD-26985] OOS copyarea fetch crash

- JIRA: https://jira.cubrid.org/browse/CBRD-26985
- Target branch: `feat/oos`
- Code branch: `CBRD-26985-infinite-loop`

## Purpose

`function_index_skip_alter_table.sql` 의 `ALTER TABLE ... CHANGE` 회귀에서 서버가 죽고, 다음 SQL 테스트가 같은 DB 에 계속 접속을 재시도하는 문제를 막는다.

이 경로는 `OOS` (큰 가변 컬럼 값을 heap 레코드 밖으로 떼어 저장하는 방식) 확장 fetch 를 사용한다. 반환 레코드의 bytes 와 `LC_COPYAREA_ONEOBJ` metadata 가 같은 `LC_COPYAREA` 안에서 일치해야 하는데, 기존 코드는 그 계약을 보장하지 못했다.

최종 수정은 crash 재현 경로인 `xlocator_lock_and_fetch_all` 과 같은 copyarea packing 계약을 쓰는 sibling 경로 `xlocator_fetch_all` 을 함께 정리한다.

## Implementation

재현 crash 경로는 domain upgrade 중 전체 인스턴스를 잠그고 가져오는 흐름이다.

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

수정은 `src/transaction/locator_sr.c` 의 copyarea packing helper 두 개로 공통화한다.

- `locator_copyarea_prepare_fetch_recdes` 는 다음 object 가 사용할 copyarea slot 과 남은 payload 공간을 계산하고, heap fetch 직전에 `recdes.data` / `recdes.area_size` 를 그 slot 으로 맞춘다.
- `locator_copyarea_pack_fetch_recdes` 는 fetch 결과가 현재 slot 에 들어가는지 확인하고, `recdes.data` 가 scan cache 등 copyarea 밖이면 descriptor 를 만들기 전에 bytes 를 copyarea slot 으로 복사한다.
- instance lock 경로는 `heap_next` 로 OID 를 찾은 뒤 `heap_get_visible_version_expand_oos` 로 다시 읽으므로, 두 번째 fetch 직전에도 같은 세팅을 반복한다.
- record 가 현재 copyarea slot 보다 크면 `S_DOESNT_FIT` 으로 빠져 기존 copyarea 확장 재시도 흐름을 탄다.
- 첫 object 를 이미 읽은 뒤 slot 부족을 알게 된 경우에는 OID 를 직전 값으로 되돌려 같은 object 를 더 큰 copyarea 에 다시 fetch 한다.

같은 helper 를 적용한 경로는 두 곳이다.

| 경로 | 이유 |
|------|------|
| `xlocator_lock_and_fetch_all` | CBRD-26985 의 직접 crash 재현 경로. `ALTER TABLE ... CHANGE` domain upgrade 에서 사용된다. |
| `xlocator_fetch_all` | `heap_next_expand_oos` 로 raw record 를 copyarea 에 담는 sibling 경로. `unloaddb` / `compactdb` bulk fetch 계열이 여기에 연결된다. |

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

이 PR 은 copyarea packing 계약을 고친다. 직접 crash frame 은 `xlocator_lock_and_fetch_all` 이지만, 같은 계약을 공유하는 `xlocator_fetch_all` 도 같은 helper 를 쓰게 해 sibling rebind 위험을 같이 제거한다.

CircleCI 에서 별도로 관찰된 insert-side `OOS+REC_BIGONE` abort 는 이 PR 범위가 아니다. 그 실패는 `locator_insert_force` 아래 heap insert path 의 임시 abort guard 와 맞으며, copyarea packing 문제가 아니다.

`heap_get_visible_version_expand_oos` 자체의 ownership 규칙은 유지한다. heap 계층은 caller-owned buffer 가 부족하면 `S_DOESNT_FIT` 을 줄 수 있지만, copyarea descriptor 와 payload 의 경계 계산은 locator 계층이 알고 있으므로 locator 에서 최종 fit 과 pointer 위치를 확인하는 것이 맞다.

호환성 변화는 없다. SQL 문법, 저장 포맷, OOS record layout, WAL (복구 로그) format 은 바뀌지 않는다.
