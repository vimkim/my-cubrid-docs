<!-- Posted to https://jira.cubrid.org/browse/CBRD-28073?focusedCommentId=4778778 on 2026-11-19. -->

## 설계 검토: 근본 원인 구조와 대안 비교

PR #8514 head `3960d1b215` 기준이다. 코드 위치는 이 커밋의 줄 번호다.

### 1. 근본 원인

serial 갱신은 일반 heap update를 거치지 않는 별도 쓰기 경로다. OOS가 추가되면서 공용 인코더 `heap_attrinfo_transform_to_disk`가 "새 OOS chain 삽입"이라는 부수효과를 갖게 되었다. serial 경로는 이 부수효과를 그대로 물려받았다. 그러나 그 부수효과를 감당하는 장치인 이전 chain 정리와 undo 일관성은 물려받지 못했다.

**(1) 일반 update 경로.** 행 쓰기와 OOS 쓰기의 운명이 같다.

```
UPDATE ─▶ 인코더 ─▶ 새 OOS chain 삽입   [undo 있음]
              └──▶ 행 update           [undo 있음, MVCC 새 버전]
          이전 chain ──▶ vacuum이 나중에 지움
```

**(2) serial 경로.** `serial_update_serial_object`는 redo 로그만 남기고 `spage_update`로 슬롯을 직접 덮어쓴다(`src/query/serial.c:1590`, `:1593`). MVCC 버전이 생기지 않으므로 vacuum은 이전 chain을 볼 수 없다.

```
NEXT VALUE ─▶ 인코더 ─▶ 새 OOS chain 삽입   [undo 있음]
                  └──▶ spage_update 덮어쓰기  [redo-only, MVCC 없음]
              이전 chain ──▶ 아무도 안 지움   ← CBRD-28035
```

**(3) SA 모드 롤백.** 서버 모드에서는 이 쓰기를 sysop으로 감싸고 바로 commit한다(`src/query/serial.c:1565`). 그래서 부모 트랜잭션이 롤백되어도 chain 삽입은 남는다. SA 모드의 `lock_get_object_lock`은 항상 `X_LOCK`을 반환하므로(`src/transaction/lock_manager.c:8021`) sysop을 열지 않는다.

```
SA 모드 롤백:
  OOS chain   ── undo가 부모 트랜잭션에 붙어 있음 ──▶ 삭제됨
  serial 행    ── redo-only라 그대로 ──▶ 지워진 chain을 가리킴 → -1397   ← CBRD-28052
```

4K page에서만 나타나는 이유는 OOS 대상을 정하는 기준 때문이다. 기준은 한 page에 레코드가 네 개 들어가는 크기다(`src/storage/heap_file.c:14133`). 4K page에서는 이 기준이 1KB 안팎이어서 `comment VARCHAR(1024)`가 대상이 된다.

### 2. 대안 비교

| 선택지 | 내용 | 판단 |
|---|---|---|
| 결과 수습 (#8492, #8496) | chain 쓰기는 두고 누적과 롤백을 따로 처리한다 | 우회 경로에 OOS 수명 관리를 복제해야 한다. 채택하지 않는다 |
| **keep_form (PR #8514)** | serial 경로는 OOS에 쓰지 않고 각 열의 기존 저장 형태를 유지한다 | 잘못된 결정이 나는 지점에서 막는다. 로그 형식도 바뀌지 않는다. 채택한다 |
| 제자리 바이트 패치 | `current_val` 바이트만 덮어쓴다 | 쓸 수 없다. NUMERIC의 디스크 길이는 값에 따라 달라진다(`src/object/object_primitive.c:8661`). 1에서 2×10^30으로 커지면 길이가 늘어난다 |
| `_db_serial` 열을 OOS 금지로 지정 | 카탈로그 열에 "OOS로 보내지 않음" 정책을 둔다 | 그런 정책이 없다. `PREFER_INLINE`은 내보내는 순서만 늦춘다(`src/storage/heap_file.c:14150`). 새 플래그와 기존 DB 처리가 필요해 범위가 크다 |
| 시퀀스 상태 분리 | `current_val`과 `started`를 고정 크기 전용 레코드로 옮긴다 | 원리상 가장 깔끔하다. redo-only 경로가 가변 열을 다루지 않게 된다. 다만 카탈로그, 업그레이드, HA를 모두 바꿔야 해서 OOS 병합 범위를 넘는다 |

### 3. keep_form의 한계와 후속 후보

- **재발 방지 장치가 없다.** 공용 인코더에 `keep_form` 분기가 추가되었다. 그러나 다른 redo-only writer가 기본 `heap_attrinfo_transform_to_disk`를 호출해도 막는 장치는 없다. 구조적 해결은 인코더를 순수 함수로 나누는 것이다. 인코더는 OOS 배치 계획만 반환하고, 실제 삽입은 undo를 책임지는 heap insert와 update가 수행한다. 후속 리팩터링 후보이며 이 이슈의 범위는 아니다.
- **같은 패턴의 다른 호출처를 확인해야 한다.** 인코더 호출처는 `src/query/serial.c:1576`(이번 수정), `src/transaction/locator_sr.c:8303`과 `:8307`(일반 경로), `src/query/serial.c:2285` 네 곳이다. `serial.c:2285`는 ALTER SERIAL 중 동시에 NEXT VALUE가 바꾼 `current_val`을 새 레코드에 합칠 때 다시 인코딩하는 곳이다. 이미 OOS 참조를 가진 레코드를 다시 인코딩하면 chain이 하나 더 삽입될 수 있다. 일반 update 로그 안에서 실행되므로 롤백 일관성은 유지되는 것으로 보인다. chain 중복 여부는 아직 확인하지 않았다.
- **inline 행은 계속 inline이다.** 값이 커지면 행도 함께 커진다. 꽉 찬 page에서는 `src/query/serial.c:1588`의 `spage_is_updatable` assert가 유일한 방어선이다. serial 24개로 4K page를 채운 시나리오에서 값을 1에서 2×10^30으로 키워도 오류가 없었다. 증가량은 수십 바이트 이하다.
