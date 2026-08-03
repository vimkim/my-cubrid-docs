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

### Q4. WAL 규칙의 집행 지점 — 완료 ✅ (사용자 3문항 전부 정답)

- page LSA vs `nxio_lsa` strict `<` 비교, 부족하면 `logpb_flush_log_for_wal()`로 로그 선행 flush, append_lsa는 메모리 경계라 불가 — 모두 정확히 답변.
- **추가 수확**: `logpb_need_wal()`은 `LSA_LE(nxio, page_lsa)`로 **등호를 보수적으로**("미기록") 취급 — 커밋 대기의 `>=` 탈출과 정반대. Q1 등호 미해결 건의 보강 증거로 보고서 §7.1에 추가.

### Q5. 그룹 커밋 1초 지연 재구성 — 완료 ✅ (중간 오개념 2회 교정)

- 오개념 1: "logpb_flush_pages가 데몬을 막는가?" → 아니오. 데몬을 막는 건 없고, `log_Flush_has_been_requested` 게이트에서 스스로 리턴. "모든 waiter 준비를 기다린다"는 개념 자체가 없음 — 병합은 쌓인 것을 쓸어담는 부수효과.
- 손님(waiter)/직원(데몬)/호출벨(플래그) 비유로 전체 타임라인 재구성: 그룹커밋 손님은 벨을 안 누름 → 직원은 10ms마다 깨지만 벨 게이트에서 리턴 → 1000ms에 손님의 timedwait 타임아웃 → 그제서야 벨 → flush.
- 오개념 2: "벨 없애고 무조건 주기 flush하면 병합 효과 깨짐" → 아니오, **본질적으로 유지**. fsync 상한 = 1/interval이 배치 창을 만듦 (MySQL/PG 방식). 다만 관찰된 '우연한 1s 배칭' 대비로는 fsync 증가 — 파라미터의 약속 기준으론 벨 제거가 더 충실.

### Q6. 페이지 경계에 걸친 로그 레코드 (partial append) — **다음 질문, 미출제** ⏸️

> 재개 시: 로그 레코드가 로그 페이지 경계를 넘으면? `LOGPB_APPENDREC_*` 상태 기계와 flush 중 "불완전 레코드" 처리 (`logpb_flush_all_append_pages`의 partial_append 분기, FLUSH 시 헤더 임시 변조 + 2차 fsync). 트레이스로 재현하려면 큰 VARCHAR 한 건 INSERT.

### 이후 후보 질문 (미출제)

- Q5: 그룹 커밋 1초 지연(보고서 §5.1)의 코드 경로를 사용자가 직접 설명해보기 — waiter/데몬/플래그 3자 상호작용.
- Q6: 로그 레코드가 페이지 경계에 걸치면? (partial append, `LOGPB_APPENDREC_*` 상태 기계)
- Q7: 복구(analysis→redo→undo)가 이번에 본 좌표들과 어떻게 만나는가 — 범위 확장 시.

## 재개 방법

1. 새 Claude Code 세션 (워크트리 `~/gh/cb/log-manager-analysis`)에서:
   `/grill-with-docs CUBRID log manager append→flush 이해 검증 계속. 세션 로그: /home/vimkim/gh/my-cubrid-docs/log-manager/grill-session-log_2026-07-28_claude.md 를 먼저 읽고 Q4부터 재개`
2. 또는 이 세션 자체를 잇기: `claude --resume` (세션 목록에서 이 대화 선택).
3. 실험 재현이 필요하면: 계측 코드가 워크트리에 그대로 있으므로 `just build` 후 서버 재시작만 하면 트레이스가 다시 쌓임. 시나리오 원본 트레이스는 세션 스크래치패드(휘발)에 있었으므로, 필요 시 보고서 §2.2 시나리오로 재생성.
