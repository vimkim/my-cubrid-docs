# CBRD-27093 — DWB 비활성 시 checkpoint가 데이터 볼륨을 fsync하지 않는 문제

- 이슈: <http://jira.cubrid.org/browse/CBRD-27093>
- 확인 커밋: develop `3aac1a6bb` (11.5.0.2336)
- 영향 버전: DWB가 도입된 10.2 ~ 11.4, develop 전부
- 한 줄 요약: `double_write_buffer_size=0`이면 checkpoint가 영구 데이터 볼륨을
  한 번도 fsync하지 않은 채 성공 처리되고, 복구에 필요한 로그까지 삭제되어
  **정전 시 커밋된 데이터가 조용히 유실**될 수 있다.

---

## 1. 배경 지식 (이것만 알면 이해된다)

### 1.1 write ≠ 디스크 저장: flush와 sync는 다르다

프로세스가 `write()`를 호출하면 데이터는 디스크가 아니라 **OS 페이지 캐시**
(메모리)에 들어간다. OS는 이걸 나중에 알아서 디스크에 내려쓴다.

```
cub_server 메모리          OS 페이지 캐시              디스크
┌────────────┐   write()   ┌────────────┐   fsync()   ┌────────────┐
│ dirty page │ ──────────► │ dirty page │ ──────────► │ 영구 저장   │
└────────────┘   (flush)   └────────────┘   (sync)    └────────────┘
                            ▲ 정전/OS 크래시 시 여기 있던 건 증발
```

- **flush** = 서버 메모리 → OS 페이지 캐시로 write. 아직 안전하지 않다.
- **sync** = `fsync()`/`fdatasync()`로 페이지 캐시를 디스크까지 강제 반영.
  이걸 해야만 정전에서 살아남는다.

핵심: **cub_server 프로세스만 죽으면** 페이지 캐시는 OS에 남아 있으므로 문제
없다. **OS가 통째로 죽는 장애**(정전, 커널 패닉)에서만 flush-but-not-synced
데이터가 증발한다. 이 버그가 평소에 안 보이는 이유다.

### 1.2 checkpoint의 계약

CUBRID는 WAL(Write-Ahead Logging)을 쓴다. 데이터 페이지가 유실돼도 로그만
있으면 redo로 복원할 수 있다. 그런데 로그를 무한히 쌓을 수 없으니 주기적으로
checkpoint를 한다. checkpoint의 계약은:

> "이 시점(chkpt_lsa) 이전의 데이터 변경은 전부 **디스크에 안전하게** 있다.
> 그러니 복구는 이 시점부터만 하면 되고, 그 이전 로그(아카이브)는 버려도 된다."

그래서 checkpoint 절차는 반드시 이 순서여야 한다:

```
1. dirty 데이터 페이지를 볼륨에 write        (flush)
2. 볼륨을 fsync                              (sync)   ← 여기가 빠지면 계약 위반
3. 로그 헤더의 chkpt_lsa(재시작 위치) 전진
4. 더 이상 필요 없는 아카이브 로그 삭제
```

2번 없이 3, 4번을 해버리면? 페이지는 아직 OS 캐시에만 있는데 "안전하다"고
선언하고 복구 수단(로그)까지 버린 것이다. PostgreSQL, MySQL(InnoDB), Oracle,
SQLite 모두 2번을 끝낸 뒤에만 3번을 한다.

### 1.3 DWB(Double Write Buffer)란

디스크는 16KB 페이지 하나를 원자적으로 써주지 않는다. 쓰다가 정전이 나면
페이지 앞쪽은 새 내용, 뒤쪽은 옛 내용인 **torn page(찢어진 페이지)**가 생길 수
있고, 이건 로그 redo로도 복원이 안 될 수 있다.

DWB는 이를 막는 장치다: 페이지를 먼저 DWB 전용 볼륨에 모아 쓰고 sync한 뒤,
실제 데이터 볼륨에 쓴다. 어느 쪽이 찢어져도 반대쪽 사본으로 복원 가능하다.

중요한 부수효과: **DWB의 flush 사이클은 데이터 볼륨 fsync까지 같이 해준다.**
그래서 DWB가 켜져 있으면(기본값 2MB) checkpoint 시점에 데이터 볼륨은 이미
sync가 끝나 있고, checkpoint가 따로 fsync를 안 해도 계약이 지켜진다.

`double_write_buffer_size=0`은 DWB를 끄는 **정식 지원 설정**이다 (예: torn
page가 없는 스토리지, 성능 실험 등).

---

## 2. 버그의 정체

### 2.1 문제의 코드 구조

checkpoint(및 복구 종료, 부팅, 아카이브 삭제 판단)는 마지막에
`fileio_synchronize_all()`을 불러 "모든 영구 볼륨을 sync"하려 한다.

`src/storage/file_io.c:4625`:

```c
int
fileio_synchronize_all (THREAD_ENTRY * thread_p)
{
  ...
  /* Flush DWB before volume data. */
  success = dwb_flush_force (thread_p, &all_sync);

  /* Check whether the volumes were flushed. */
  if (success == NO_ERROR && all_sync == false)
    {
      /* Flush volume data. */
      (void) fileio_traverse_permanent_volume (thread_p, fileio_synchronize_volume, &arg);
      ...
```

설계 의도: "DWB한테 먼저 물어본다. DWB가 '내가 데이터 볼륨 sync까지 다
해놨어(`all_sync=true`)'라고 하면 내가 또 fsync할 필요 없다. 아니면
(`all_sync=false`) 내가 직접 전 볼륨을 돈다."

DWB가 켜져 있을 땐 이 로직이 정확하다. 문제는 DWB가 **아예 만들어지지 않은**
경우다. `src/storage/double_write_buffer.cpp:3550` (`dwb_flush_force`):

```c
  if (DWB_NOT_CREATED_OR_MODIFYING (initial_position_with_flags))
    {
      if (!DWB_IS_CREATED (initial_position_with_flags))
        {
          /* Nothing to do. Everything flushed. */   ← 여기가 함정
          goto end;
        }
      ...
end:
  *all_sync = true;        ← "할 일 없음"을 "전부 sync됨"으로 보고
  return NO_ERROR;
```

DWB가 없으니 flush할 것이 없는 건 맞다. 하지만 함수는 이를
`*all_sync = true`로 보고하고, 호출자는 "데이터 볼륨 sync가 이미 끝났구나"로
해석해 **볼륨 순회 fsync를 건너뛴다.** 실제로는 아무도 sync하지 않았는데.

한 문장으로: **"nothing to flush"(할 게 없었다)와 "everything synced"(전부
디스크에 내렸다)를 한 변수에 뭉뚱그린 의미론 버그다.**

### 2.2 왜 다른 안전망도 다 뚫리는가

"checkpoint 말고 다른 데서 fsync해주지 않나?"— 전부 같은 구멍으로 빠진다.

1. **페이지를 쓸 때 sync?** 영구 볼륨은 `O_SYNC` 없이 열린다
   (`boot_sr.c:1274`, `is_do_sync=false`). write 자체는 durability가 없다.
2. **주기적 보상 flush?** DWB off면 페이지 write가
   `FILEIO_WRITE_DEFAULT_WRITE` 모드가 되어 N페이지마다
   `fileio_compensate_flush()`(`file_io.c:627`)가 sync를 시도한다. 그런데 그
   함수가 부르는 것도 결국 `fileio_synchronize_all()` — **같은 버그로
   no-op**이다.
3. **개별 볼륨 sync 경로?** `dwb_synchronize()`(`double_write_buffer.cpp:2841`,
   볼륨 복사·페이지 기록 후 동기화 등 file_io.c의 4곳 — 2844, 2912, 3126,
   3332행에서 호출)도 동일 패턴이다:

   ```c
   error = dwb_flush_force (thread_p, &complete);
   if (error == NO_ERROR && complete == false)
     error = fsync (vol_fd);          ← complete=true라서 역시 건너뜀
   ```

   즉 JIRA 이슈에 적힌 checkpoint 계열보다 실제 영향 범위가 넓다.
   (이 발견은 JIRA 코멘트로 추가 예정.)

결론: DWB off 구성에서 영구 데이터 볼륨으로 가는 fsync 경로는 **문자 그대로
하나도 없다.** 이슈의 strace 실측(데이터 볼륨 fsync 0회)과 정확히 일치한다.

### 2.3 strace 실측 (이슈 재현 결과)

```
double_write_buffer_size=0:              DWB 기본 활성:
   7  testdb_lgat    (활성 로그)            28  testdb        ← 데이터 볼륨
   1  testdb_lgar_t                         28  testdb_dwb
   1  testdb_t32766  (임시 볼륨)             7  testdb_lgat
   1  databases/testdb                       2  testdb_lgar_t
   0  testdb         ← 데이터 볼륨 0회!      1  testdb_t32766
                                             1  databases/testdb
```

DWB on일 때 데이터 볼륨에 28회 보이는 fdatasync가 off에선 0회다. 로그
(lgat)는 별도 경로로 sync되므로 멀쩡하다 — 그래서 로그는 안전한데 데이터
페이지만 위험한, WAL 계약이 뒤집힌 상태가 된다.

---

## 3. 실제 데이터 유실 시나리오 (단계별)

기본 배포 설정(`log_max_archives=0`) + `double_write_buffer_size=0` 가정:

```
t1  트랜잭션 커밋           → 로그는 fsync됨(안전), 데이터 페이지는 버퍼풀에 dirty
t2  checkpoint 실행         → 페이지를 볼륨에 write (OS 캐시까지만 감)
                            → fileio_synchronize_all() = no-op  ← 버그
                            → chkpt_lsa 전진, 이전 아카이브 로그 삭제
t3  정전                    → OS 페이지 캐시에 있던 데이터 페이지 증발
t4  서버 재시작/복구        → "chkpt_lsa 이후만 redo하면 된다"고 믿음
                            → 유실 페이지를 복원할 로그는 t2에 이미 삭제됨
                            → 복구는 오류 없이 정상 종료
t5  운영 재개               → 커밋된 변경이 사라져 있음. 에러 없음.
```

더 고약한 점: 페이지마다 OS가 디스크에 내려쓴 타이밍이 달라서, 테이블
페이지는 옛날 것 + 인덱스 페이지는 새것 같은 **불일치 상태**로 남는다. 증상은
한참 뒤에 unique 위반, 인덱스-데이터 불일치로 나타나며, 그 시점엔 원인 추적이
사실상 불가능하다.

---

## 4. 수정 설계 (grill 세션 확정 사항)

### 4.1 수정 지점: `dwb_flush_force` 내부 (한 곳)

원인이 out-parameter의 의미론 하나이므로 거기만 고친다. `all_sync=true`의
의미를 다음으로 좁힌다:

> **"이 호출에서 DWB 기계가 영구 데이터 볼륨 sync까지 실제로 수행했다"**

`dwb_flush_force`의 `end:` 도달 경로는 4가지인데:

| # | 경로 (double_write_buffer.cpp) | 상황 | 수정 후 all_sync |
|---|---|---|---|
| 1 | :3552 | DWB 미생성 (size=0) | **false** ← 버그 본체 |
| 2 | :3583 | DWB 활성, flush 완료 확인 | true (유지) |
| 3 | :3655 | 루프 중 DWB가 동시 비활성화됨 | **false** |
| 4 | :3712 | dwb_add_page 중 비활성화 감지 | **false** |

경로 3, 4까지 false로 하는 이유: `double_write_buffer_size`는
`PRM_USER_CHANGE`라 **온라인으로 끌 수 있다.** 끄는 순간 이후 직접 볼륨에
쓰인 페이지는 DWB가 보증 못 한다. false로 하면 호출자가 직접 fsync하므로
항상 안전하고, 비용은 드문 경쟁 상황에서 fsync 한 번 더뿐이다.
(이 판단은 `docs/adr/0001-...md`로 기록됨 — 미래에 누가 "destroy가 어차피
flush하니까 true로 최적화하자"고 되돌리는 걸 막기 위해.)

### 4.2 이 한 곳 수정으로 전부 복구되는 이유

호출자들이 **이미 올바른 폴백 코드를 갖고 있기 때문**이다:

- `fileio_synchronize_all()`: `all_sync==false` → 전 영구 볼륨 순회 fsync
  (10.1 이전 checkpoint 동작 그대로 복원)
- `dwb_synchronize()` 4개 호출처: `complete==false` → `fsync(vol_fd)` 직접 수행
- `fileio_compensate_flush()`: `fileio_synchronize_all` 경유이므로 자동 복구

DWB 활성(기본) 구성은 경로 2를 그대로 타므로 **동작 변화 0** — 회귀 위험이
최소다.

### 4.3 명시적으로 범위 밖으로 뺀 것

- **fsync 실패 시 처리 수위**: 현재는 checkpoint만 포기하고 서버는 계속 돈다.
  PostgreSQL은 fsyncgate 이후 이를 PANIC(서버 중단) 사유로 다룬다. 실패한
  fsync 후 OS가 dirty 페이지를 버렸을 수 있어 재시도가 안전하지 않기
  때문이다. 중요한 주제지만 DWB on/off 공통의 별개 설계 논의라 **별도 티켓**.

### 4.4 검증·배포 계획

- **테스트**: 이슈의 strace 재현 절차를 CTP 셸 테스트로 (strace 없으면
  graceful skip). PR에 수정 전/후 strace 집계를 증거로 첨부.
  - fsync "부재"를 검증해야 해서 선택지가 좁다. `cubrid statdump`의
    `Num_file_iosynches`는 로그 fsync 노이즈가 섞여 flaky 위험 → 배제.
- **백포트**: develop 먼저. JIRA에 영향 버전(10.2~11.4) 명시, 릴리즈 브랜치
  백포트는 유지보수 정책에 따름.
- **JIRA 반영**: CBRD-27093에 한국어 코멘트로 (a) `dwb_synchronize` 4개
  호출처도 같은 근본 원인임을 추가 기록, (b) Minor → Major 이상 심각도 상향
  제안. 수정이 동일하므로 별도 티켓은 만들지 않음.

---

## 5. 참고 코드 위치 모음

| 무엇 | 위치 |
|---|---|
| 버그 본체 (`all_sync=true` 오보고) | `src/storage/double_write_buffer.cpp:3550-3557`, `:3739-3740` |
| 건너뛰는 호출자 1 | `src/storage/file_io.c:4625` `fileio_synchronize_all` |
| 건너뛰는 호출자 2 | `src/storage/double_write_buffer.cpp:2841` `dwb_synchronize` (+ file_io.c 4곳) |
| checkpoint에서의 호출 | `src/transaction/log_page_buffer.c:7018` |
| chkpt_lsa 전진 | `src/transaction/log_page_buffer.c:7211-7213` |
| 영구 볼륨 O_SYNC 없이 mount | `src/transaction/boot_sr.c:1274` |
| 보상 flush (역시 no-op) | `src/storage/file_io.c:627` `fileio_compensate_flush` |
| DWB 도입 커밋 | `3917201b0` [CBRD-21529] (2018-08, 10.2) |
| 파라미터 정의 (PRM_USER_CHANGE) | `src/base/system_parameter.c:4304` |

## 6. 용어 (요약)

- **flush**: 서버 메모리 → OS 페이지 캐시 write. 크래시 안전 아님.
- **sync**: fsync/fdatasync로 디스크까지 강제 반영. 이래야 안전.
- **DWB-vouched sync**: `dwb_flush_force`가 `all_sync=true`로 "내가 데이터
  볼륨 sync까지 해놨다"고 보증하는 것. "할 일이 없었다"는 보증이 아니다 —
  이 구분 실패가 이 버그다.
