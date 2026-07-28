# Grill 세션 로그 — CUBRID 로그 매니저 append→flush (2026-07-28)

> 목적: `/grill-with-docs` 세션의 진행 상태 기록. **재개 시 이 파일을 읽으면 전체 맥락 복원 가능.**
> 도메인 문서: 같은 폴더의 `cubrid-log-manager-overview_4cfc837_claude.md`(정적),
> `cubrid-log-manager-append-flush-dynamic-analysis_4cfc837_claude.md`(동적 실측),
> `CONTEXT.md`(확정 용어집)
> 워크트리: `~/gh/cb/log-manager-analysis` (master 4cfc8370e) — **트레이스 계측 코드가 비커밋 상태로 남아 있음**
> (logmgr_trace.hpp 신규 + log_append.cpp/log_manager.c/log_page_buffer.c 수정, 출력: /tmp/cubrid_logmgr_trace.log)
> 테스트 DB: `logtestdb` (debug_gcc 프리셋, 서버 기동 중이었음. conf는 원복 완료: log_buffer_size=256M, group_commit=0)

## 진행 상황 요약

### Q1. LSA 3좌표와 durable 판정 — 완료 ✅ (사용자가 코드보다 정확했음)

- 질문: durable 판정 조건과 prior_lsa/append_lsa/nxio_lsa 각각의 의미.
- **사용자의 반격이 세션의 첫 수확**: "durable은 `nxio_lsa > commit_lsa`(strict)여야 하지 않나?" → 맞는 지적.
  - `nxio_lsa` = "next I/O LSA", **디스크에 아직 안 쓴 첫 위치** (`log_append.hpp:76`).
  - 코드의 탈출 조건은 `nxio >= flush_lsa`(커밋 레코드 **시작** LSA, 등호 포함)인데, nxio가 레코드 경계에만 멈추므로 일반 경로는 strict `>`로만 탈출 (S1 실측: commit 6016, flush 후 nxio 6056).
  - **미해결**: `nxio == commit_lsa` 등호 케이스가 레이스로 도달 가능해 보임 (drain이 커밋 레코드 직전에 끝나는 인터리빙). 도달하면 durability 위반. 보고서 §7.1에 기록. 사용자가 (b) "미해결로 남기고 진행" 선택.

### Q2. prior list 백프레셔 — 완료 ✅ (실측으로 검증)

- 질문: 대량 tx에서 prior list 무한 성장을 막는 것은? → 답: 소프트 백프레셔 (임계 초과 시 데몬 wakeup + append당 1ms sleep, 하드 상한 없음).
- 사용자 의심: "1ms로 충분한가?" → **S6 실험으로 검증**: log_buffer_size 4M으로 낮추고 13MB tx 실행.
  - MAXED 6회, 임계 초과분 최대 ~350B, wakeup→drain 응답 109µs, 디스크 I/O는 drain 후 생산과 병행.
  - 핵심 통찰: **백프레셔는 느린 디스크가 아니라 빠른 drain까지만 버티면 된다.**
  - 보고서 §4.6에 반영.

### Q3. prior list의 존재 이유 — 완료 ✅

- 사용자 답: "prior mutex로 직렬화 후 데몬이 append — concurrent queue에 넣고 소비자가 출력하는 것과 동일" → 본질(MPSC 분리) 정확.
- 조임 2가지: (1) 일반 큐와 달리 **enqueue 시점에 LSA(주소)가 확정**되는 좌석 예약 시스템 — page LSA/undo 체인/커밋 대기가 그 주소를 즉시 소비. (2) 소비자는 데몬 전담이 아니라 **LOG_CS를 잡은 자의 역할** (롤백 스레드의 직접 drain, S3 실측).
- CONTEXT.md에 용어 확정.

### 파생 토론: prior_lsa_mutex의 lock-free화 — 완료 ✅

- 사용자 제안: lock-free queue로 최적화 가능하지 않나?
- 결론: **방향은 옳고 선례 있음** (MySQL 8.0 link_buf, PG 샤딩 insertion lock, Aether consolidation array). 단 "교체(swap)"가 아니라 "재설계(redesign)":
  뮤텍스가 파는 건 큐 넣기가 아니라 **3중 원자성** — ① LSA 확정(페이지 경계·정렬 탓에 fetch_add 한 방 불가), ② MVCC 체인 연결("직전"은 순서 확정 후에만 결정 — lock-free면 사슬 갈라짐 → vacuum 누락), ③ tdes 상태 전이와의 원자성(체크포인트 일관성, 코드 주석 명시).
- 착수 전 다코어 고TPS에서 뮤텍스 경합 실증이 선행 과제 (현 실측 병목은 fsync: 커밋 0.5ms 중 0.32ms).

### Q4. WAL 규칙의 집행 지점 — **여기서 중단, 미답변** ⏸️

> **재개 시 이 질문부터**: 버퍼 풀(pgbuf)이 더티 데이터 페이지를 내리려는 순간, 그 페이지의 변경 로그가 아직 `nxio_lsa` 너머(미기록)라면 무슨 일이 일어나야 하나? 왜 그 판정 좌표가 `nxio_lsa`인가?
> 준비된 추천 답: pgbuf flush 경로가 page LSA와 nxio_lsa를 비교, `page_lsa >= nxio_lsa`면 로그 선행 강제 flush (`logpb_flush_log_for_wal` 계열). nxio_lsa가 "디스크에 있는 로그의 경계" 그 자체이므로 WAL 판정의 유일한 좌표.

### 이후 후보 질문 (미출제)

- Q5: 그룹 커밋 1초 지연(보고서 §5.1)의 코드 경로를 사용자가 직접 설명해보기 — waiter/데몬/플래그 3자 상호작용.
- Q6: 로그 레코드가 페이지 경계에 걸치면? (partial append, `LOGPB_APPENDREC_*` 상태 기계)
- Q7: 복구(analysis→redo→undo)가 이번에 본 좌표들과 어떻게 만나는가 — 범위 확장 시.

## 재개 방법

1. 새 Claude Code 세션 (워크트리 `~/gh/cb/log-manager-analysis`)에서:
   `/grill-with-docs CUBRID log manager append→flush 이해 검증 계속. 세션 로그: /home/vimkim/gh/my-cubrid-docs/log-manager/grill-session-log_2026-07-28_claude.md 를 먼저 읽고 Q4부터 재개`
2. 또는 이 세션 자체를 잇기: `claude --resume` (세션 목록에서 이 대화 선택).
3. 실험 재현이 필요하면: 계측 코드가 워크트리에 그대로 있으므로 `just build` 후 서버 재시작만 하면 트레이스가 다시 쌓임. 시나리오 원본 트레이스는 세션 스크래치패드(휘발)에 있었으므로, 필요 시 보고서 §2.2 시나리오로 재생성.
