# CBRD-27370 주장 검증 보고서

- 대상 이슈: [CBRD-27370](http://jira.cubrid.org/browse/CBRD-27370) `[PGBUF] [Regression] Ordinary nested READ-to-WRITE fix resets BCB fix count and desynchronizes holder debt`
- 검증 기준 소스: develop `5f3a30d0998beafcc3932ed8cf65e66020a53c4c` (2026-09-04 기준 HEAD, worktree `CBRD-27370-read-to-write-fix`)
- 검증일: 2026-09-04
- 작성: Claude (Fable 5.1), 사람 검토 전 초안

## Verdict

**주장은 유효하다.** 정적 코드 분석과 debug/release 두 빌드의 런타임 재현이 모두 이슈의 설명과 일치했고, 이슈가 기술하지 않은 unfix 이후 동작까지 확인했다.

| 검증 항목 | 결과 |
|---|---|
| 현재 코드에 `new_impl.impl.fcnt = 1` 대입이 READ→WRITE 승격 분기에 남아 있는가 | 예. `src/storage/page_buffer.c:6314-6319` |
| 같은 성공 경로에서 `holder->fix_count++` 가 실행되는가 | 예. `src/storage/page_buffer.c:6398` |
| 회귀 커밋이 CBRD-26425 `58cef8e01` 인가 | 예. `git blame` 6314-6319 전부 `58cef8e01 (Ilhan 2026-01-14)`. 이후 이 대입을 건드린 커밋 없음 |
| 개편 전 release 빌드가 두 카운터를 각각 1 증가시켰는가 | 예. `58cef8e01^` (`051851d1e`) 의 `pgbuf_latch_bcb_upon_fix` READ 분기가 `bufptr->fcnt++` 와 `holder->fix_count++` 를 함께 수행 |
| 개편 전 debug 빌드가 `ER_FAILED` 로 거부했는가 | 예. 2014년 `076bf0114` 가 추가한 `assert(false); return ER_FAILED;` 블록 |
| 런타임 재현 (debug, 5f3a30d09) | 재현됨. 아래 Actual Result |
| 런타임 재현 (release, develop `0888ccb` 2026-08-03) | 재현됨. 아래 Actual Result |

## Code Evidence

현재 HEAD의 승격 분기와 공통 성공 처리:

```c
/* src/storage/page_buffer.c:6314-6319 (pgbuf_latch_bcb_upon_fix, CAS loop 내부) */
if (old_impl.impl.fcnt == holder->fix_count)
  {
    can_latch = true;
    new_impl.impl.latch_mode = request_mode;
    new_impl.impl.fcnt = 1;          /* 기존 READ fix 수를 덮어씀 */
  }

/* src/storage/page_buffer.c:6398 (can_latch 공통 성공 처리) */
holder->fix_count++;                 /* 스레드 쪽은 누적 */
```

`fcnt = 1` 은 바로 위 idle 페이지 경로(`:6266`)와 같은 형태다. idle 경로는 fcnt가 0에서 시작하므로 1이 맞지만, 승격 분기는 `old_impl.impl.fcnt`가 이미 holder의 READ fix 수이므로 `fcnt + 1` 이어야 한다.

개편 전(`051851d1e`, `pgbuf_latch_bcb_upon_fix` 기준 6012-6041행) 동일 분기는 다음과 같았다:

```c
else if (bufptr->latch_mode == PGBUF_LATCH_READ)
  {
    if (bufptr->fcnt == holder->fix_count)
      {
        bufptr->latch_mode = request_mode;   /* PGBUF_LATCH_WRITE */
        bufptr->fcnt++;
        ...
        holder->fix_count++;
```

단, 그 앞(같은 파일 5973행)에 2014년 `076bf0114` 가 넣은 검사가 있어 debug 빌드는 `assert(false)` 후 `ER_FAILED` 를 반환했고, release 빌드는 `assert_release` 가 `ER_FAILED_ASSERTION` 알림(notification severity)만 기록한 뒤 위 분기로 진행해 두 카운터를 함께 올렸다. 이슈 본문은 release가 "각각 1 증가"시켰다고만 적었는데, 알림 로그가 함께 남았다는 점만 보충하면 정확하다.

## Runtime Evidence

재현 프로그램과 gdb 스크립트는 `repro/` 에 있다. `pgbuf_fix(READ)`, `pgbuf_fix(READ)`, `pgbuf_fix(WRITE)` 를 같은 스레드에서 같은 페이지(`{0,0}`)에 호출한 뒤 세 번 `pgbuf_unfix` 한다. `latch` 값 1은 READ, 2는 WRITE, 0은 NO_LATCH다.

### Debug build (5f3a30d09, `repro/run_debug.log`)

```
GDB after READ 1: holder_fix_count=1
after READ 1: global_fcnt=1 latch=1
GDB after READ 2: holder_fix_count=2
after READ 2: global_fcnt=2 latch=1
GDB after WRITE: holder_fix_count=3
after WRITE: global_fcnt=1 latch=2          <- 전역 fcnt 2 -> 1 로 후퇴, holder 는 3
GDB after UNFIX 1: holder_fix_count=2
after UNFIX 1: global_fcnt=0 latch=0        <- fix 2개가 남았는데 래치 해제
page_buffer.c:6590: pgbuf_unlatch_bcb_upon_unfix: Assertion `false' failed.   <- 2번째 unfix 에서 abort
```

### Release build (develop 0888ccb, `repro/run_release.log`)

```
after READ 1: global_fcnt=1 latch=1 er_errid=0
after READ 2: global_fcnt=2 latch=1 er_errid=0
after WRITE: global_fcnt=1 latch=2 er_errid=0
after UNFIX 1: global_fcnt=0 latch=0 er_errid=0
after UNFIX 2: global_fcnt=0 latch=0 er_errid=-19 msg=Internal error: pageptr = ... of page 0 ... is not fixed.
after UNFIX 3: global_fcnt=0 latch=0 er_errid=-19 msg=Internal error: pageptr = ... of page 0 ... is not fixed.
```

두 빌드 모두 이슈의 Actual Result(`fcnt 1 -> 2 -> 1`, `holder 1 -> 2 -> 3`)와 정확히 일치한다. 추가로 확인한 unfix 단계는 이슈의 영향 서술(래치가 남은 fix보다 먼저 풀림, 정상 unfix가 내부 오류 처리됨)을 그대로 뒷받침한다.

## Caveats

- **실제 트리거 경로는 확인하지 않았다.** 개편 전 debug 빌드가 이 요청을 `assert(false)` 로 막아 왔으므로, 일반 실행 경로에서 같은 스레드가 READ 보유 중 일반 `pgbuf_fix(WRITE)` 를 호출하는 곳은 없거나 매우 드물 것으로 추정한다. 즉 현재는 잠재(latent) 결함이며, 이 추정은 호출부 전수 조사로 확정한 것이 아니다.
- `pgbuf_promote_read_latch` 는 영향이 없다. 단독 holder 즉시 승격은 `latch_mode` 만 바꾸고 fcnt를 건드리지 않으며, 대기 경로는 `fix_count` 를 `pgbuf_block_bcb` 로 넘겨 복원한다(`:2740-2924`).
- 수정 정책(일반 승격 허용 vs 금지)은 이슈대로 미결이다. 어느 쪽이든 fix/unfix 회계가 일치해야 한다는 요구는 동일하다.
- release 재현은 develop `0888ccb`(2026-08-03) 설치본을 사용했다. 이 커밋은 `58cef8e01` 을 포함하며, 해당 분기는 이후 변경이 없다.

## Repro

```bash
# 1. debug 빌드 설치본과 이 소스 트리 헤더로 SA 프로브 컴파일 (repro/cbrd27370_probe.cpp)
g++ -std=gnu++17 -g -O0 -DSA_MODE -DLINUX -DGCC -DI386 -DX86 -DSYSV -D_GNU_SOURCE \
  -D_FILE_OFFSET_BITS=64 -D_LARGEFILE64_SOURCE -D_REENTRANT \
  -I<build_dir> -I<src>/include -I<src>/src/{api,base,compat,storage,thread,transaction,communication,connection,monitor,object,query,xasl} \
  -I<src>/cubrid-cci/src/cci -I<build_dir>/3rdparty/include -I<build_dir>/3rdparty/Source/lz4/lib \
  -I<build_dir>/3rdparty/Source/rapidjson/include \
  cbrd27370_probe.cpp -L<install>/lib -Wl,-rpath,<install>/lib -lcubridsa -lpthread -ldl -o cbrd27370_probe
# release 빌드는 -DNDEBUG 를 추가해 pgbuf_fix_release 심볼에 연결한다.

# 2. 임시 DB 생성 후 gdb 로 실행 (holder->fix_count 는 gdb 가 읽는다)
CUBRID=<install> CUBRID_DATABASES=<tmp> cubrid createdb -F <tmp>/db -L <tmp>/db cbrd27370_probe en_US.utf8
cd <tmp>/db && gdb -q -batch -x cbrd27370_probe.gdb --args ./cbrd27370_probe cbrd27370_probe
```
