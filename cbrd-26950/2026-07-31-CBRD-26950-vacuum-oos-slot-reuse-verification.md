# CBRD-26950 — vacuum OOS 슬롯 재사용 데이터 손실: 현재 소스 검증 보고

- **작성일**: 2026-07-31
- **검증 기준 커밋**: `0ad6afc0ff871f5aa6c002923868fc6527149ea0` (= `origin/feat/oos`, ahead/behind 0/0)
- **JIRA 앵커와의 관계**: JIRA 본문은 `2c329a4e0` 기준. 본 문서는 그 이후의 모든 변경(bestspace 리디자인 CBRD-26176 포함)을 반영한 현재 HEAD 재검증 결과.
- **작성 도구**: Claude Code (Fable 5) — 분석 전용 세션, 소스 무변경
- **판정**: **성립** (신뢰도 높음 — 코드 수준 도달 가능성. 런타임 재현은 fault-injection 훅이 필요해 미수행)

---

## 1. 한 줄 요약

vacuum이 블록을 재처리할 때, 이미 회수했다가 **다른 살아있는 행이 재사용한 OOS 슬롯**을 구분하지 못하고 다시 지워서 **무증상 데이터 손실**이 발생할 수 있다. 이를 막는 불변식은 현재 엔진 어디에도 없다.

## 2. 사고 타임라인 (정확한 메커니즘)

핵심: **vacuum의 진행 기록 단위가 레코드가 아니라 블록 전체**라는 것.

| 시점 | 사건 | 근거 |
|---|---|---|
| T1 | `UPDATE R1` → 옛 OOS 체인 `V\|P\|S` 는 이제 **UPDATE 로그 레코드의 undo image에만** 참조가 남음. 이 레코드는 로그 블록 B 소속 | OOS-CONTEXT 불변식 2 |
| T2 | B의 MVCCID가 가시성 임계값 아래로 → master가 B 배포, vacuum data(영속 페이지)에서 B = **IN_PROGRESS** | `vacuum.c` |
| T3 | **1차 삭제(정상)**: worker가 undo image에서 `V\|P\|S` 추출 → probe 통과 → `oos_delete` → **레코드 단위 sysop 커밋**. 슬롯이 비고 페이지는 **즉시 bestspace 재등록**. ⚠️ "이 레코드 처리 완료" 메모는 어디에도 안 남고 `start_lsa` 도 불변. B는 여전히 IN_PROGRESS | `vacuum_oos.cpp:171,196`, `oos_file.cpp:2189` |
| T4 | 다른 트랜잭션 T가 R2 insert → `oos_insert` 가 bestspace tier-1에서 그 페이지 선택, **최저 빈 슬롯 = S** 재사용 → R2의 청크가 정확히 `V\|P\|S` 에 앉음. T 커밋(WAL flush로 T3·T4 모두 영속) | `oos_file.cpp:912-961`, `slotted_page.c:1284-1290` |
| T5 | worker가 블록 B를 끝내기 **전에** 중단 — 크래시 / 정상 셧다운 / (릴리스) 블록 중간 에러 | `vacuum.c:3895-3940` |
| T6 | 재기동 복구: redo는 page LSA 게이트로 정확히 복원 (**여기까지 아무 문제 없음**). vacuum data 로드 시 IN_PROGRESS 블록 → **AVAILABLE + INTERRUPTED 재장전**, `start_lsa` 그대로 | `vacuum.c:4398-4401`, `8357-8361` |
| T7 | **2차 처리(사고)**: B를 `start_lsa` 부터 통째로 재주행 → 같은 undo image(WAL 불변)에서 같은 `V\|P\|S` 추출 → `oos_chunk_exists`: 슬롯에 레코드 있음(R2의 것) → **true** → `oos_delete` 가 **R2의 살아있는 청크 삭제**. 신규 연산이므로 새 로그를 남기며 복구 관점에선 완벽히 일관 — 내용만 틀림. 에러·경고 없음 | `vacuum_oos.cpp:179,188`, `oos_file.cpp:2241-2244` |

멀티청크 확대: `oos_delete_chain` 은 **현재 점유자**의 헤더에서 `next_chunk_oid` 를 읽어 체인을 끝까지 따라가므로(`oos_file.cpp:2171-2194`), 재사용된 head 슬롯이 멀티청크 R2의 것이면 **R2 체인 전체**가 삭제된다.

## 3. 증명 의무 A–H (전부 현재 HEAD 라인 기준)

| ID | 질문 | 판정 | 핵심 증거 |
|---|---|---|---|
| A | forward-walk 회수가 블록 완료 전에 독립 커밋되나 | confirmed | 레코드별 sysop (`vacuum_oos.cpp:171,196`); 커밋된 sysop은 복구 undo가 `lastparent_lsa` 로 건너뜀 (`log_recovery.c:4800-4804,4857`) |
| B | 같은 로그 엔트리가 다시 검사되나 | confirmed | `start_lsa` 미전진 TODO (`vacuum.c:3764`); incomplete → `set_interrupted()` = AVAILABLE+INTERRUPTED (`vacuum.c:3926, 8357-8361`); 크래시 재장전 (`vacuum.c:4398-4401`); 재주행 진입 (`vacuum.c:3488, 3587-3590, 3722-3728`); 엔트리별 진행 메모 없음 |
| C | 재검사 전에 다른 트랜잭션이 할당 가능한 구간이 있나 | confirmed | 비운 슬롯을 보호하는 잠금 없음 (`oos_file.cpp:2116` TODO — 죽은 행의 row lock 무의미); 셧다운·크래시 시나리오에서는 재사용이 중단 **이전에** 발생해도 성립 |
| D | 정확히 같은 `(volid,pageid,slotid)` 재사용 가능한가 | confirmed | ANCHORED → `REC_DELETED_WILL_REUSE` (`slotted_page.c:2093-2095`); 최저 슬롯 우선 재사용 (`slotted_page.c:1284-1290`); 삭제 직후 bestspace 재등록 (`oos_file.cpp:2189→912-961`); 페이지는 해제되지 않음 (`oos_file.cpp:2283` 주석, `oos_remove_page` vacuum 호출자 부재 = CBRD-26786 미구현) |
| E | 반복 검사 때 undo image가 같은 head OID를 주나 | confirmed | append-only WAL 재독 (`vacuum_fetch_log_page`); undo image를 고쳐 쓰는 코드 없음 (설계 수준 사실) |
| F | probe가 신원을 확인하나 | **refuted(신원 확인 없음)** | `oos_chunk_exists` 는 `S_SUCCESS` 면 무조건 true — 내용을 읽지도 않음 (`oos_file.cpp:2241-2244`); `oos_record_header` = length/index/next 뿐 (`oos_file.hpp:26-31`) |
| G | 후속 `oos_delete` 가 현재 점유자·그 체인에 작용하나 | confirmed | 현재 점유자 헤더 memcpy 후 체인 추적 (`oos_file.cpp:2171-2194`) |
| H | A–G를 깨는 불변식이 있나 | **refuted** | §4 참조 — 후보 7개 전수 반박 |

## 4. 차단 불변식 후보 전수 점검 (H)

1. **블록 재방문 불가?** — 아니오. B에서 반박.
2. **진행 위치가 처리된 엔트리 뒤에서 재개?** — 아니오. `start_lsa` 불변(명시적 TODO), 레코드 단위 메모 없음.
3. **해당 구간에 슬롯 재할당 불가?** — 아니오. 잠금 없음 + bestspace가 재사용을 **촉진**.
4. **페이지/슬롯 메타데이터가 새 점유자를 구분?** — 아니오. 헤더에 신원 필드 없음, probe는 내용조차 안 읽음.
5. **트랜잭션/sysop/래치/스케줄링 직렬화?** — 아니오. sysop은 원자성만 제공, 래치는 fix 단위, vacuum 디스패치 게이트(MVCCID 임계값)는 죽은 행 조건일 뿐 새 점유자와 무관.
6. **복구가 재사용 전에 옛 참조를 제거?** — 아니오. undo image는 불변이고, 복구는 오히려 블록을 재장전한다.
7. **`oos_delete` 전 추가 검증?** — 아니오. exists probe가 유일한 관문.

## 5. 자주 나오는 반론과 답 (Q&A)

### Q1. "삭제된 OOS OID가 재발급 안 되거나 오래 걸리면 실질적으로 문제없지 않나?"

OOS OID는 논리 식별자가 아니라 **물리 주소** `(volid,pageid,slotid)` 그 자체다 — "재발급 절차"가 따로 없고, 슬롯 재점유가 곧 같은 OID의 재등장이다. 그리고 현재 코드는 재점유를 최단 경로로 유도한다: 삭제 즉시 bestspace 재등록(sysop 커밋 전!) + insert의 tier-1 우선 선택 + 최저 슬롯 우선. 재사용 지연은 "엄청난 시간"이 아니라 **같은 테이블에 다음 OOS 값이 들어오는 순간**이다. "재사용을 금지/지연하자"는 현재 동작이 아니라 새로 만들어야 할 불변식이며, 그 순간 논점은 '수정 불필요'가 아니라 '수정 방식 선택'(신원 필드 vs 재사용 유예)이 된다.

### Q2. "page LSA가 있으니 recovery가 알아서 막아주지 않나?"

page LSA는 "**같은 redo를 같은 페이지에 두 번 적용**"을 막는 장치다. 2차 삭제는 redo replay가 아니라 **복구 완료 후 평시 코드의 신규 연산**이다: 페이지가 아니라 로그의 undo image를 읽고, 새 `RVOOS_DELETE` 로그를 append한다. WAL/복구 기계는 이 잘못된 삭제를 충실히 영속화한다 — 복구 관점에서 완벽히 일관된, 내용만 틀린 상태. 크래시 없는 시나리오(셧다운 중단, 릴리스 중간 에러)에서도 동일하게 발생한다.

### Q3. "bestspace 최근에 완전히 새로 바뀌지 않았나? 분석이 낡은 것 아닌가?"

`e84a7f6dc [CBRD-26176] Redesign bestspace (#7353)` (2026-07-22)는 **heap** bestspace를 갈아엎었지만 파일 목록에 `oos_file.cpp/.hpp` 가 없다. OOS bestspace는 `OOS_HDR_STATS` + `oos_stats_*` 3-tier **별도 구현**(CBRD-26658)이고 리디자인이 건드리지 않았다. 본 문서의 모든 인용은 리디자인 **이후** HEAD(`0ad6afc0f`)에서 직접 확인한 것이다.

### Q4. "테스트 다 통과하는데 왜 CRITICAL이냐?"

블록 재시도 + 슬롯 재사용 조합을 만드는 테스트가 **존재하지 않는다**(부재 ≠ 안전). 결정적 재현에는 vacuum sysop 커밋 직후 worker를 멈추는 fault-injection이 필요하다. 발현 시 증상이 에러·로그 없는 **무증상 데이터 손실**이라 사후 진단도 불가능한 부류이므로 심각도는 CRITICAL이 맞다. 낮은 확률은 도달 불가가 아니다.

## 6. JIRA 앵커(`2c329a4e0`) 이후 변경 검토

| 파일 | 변경 | 이 결함과의 관계 |
|---|---|---|
| `vacuum_oos.cpp` | **무변경** | — |
| `oos_file.hpp/cpp` | batch API(CBRD-27006), 에러 로깅(CBRD-26792), bestspace fit-check/sync 수정(CBRD-26954/26824) | 신원 필드 추가 없음, probe 의미 불변 |
| `vacuum.c` | heap bestspace 리디자인(CBRD-26176), TDE 게이트 | `start_lsa`/블록 상태 기계 불변 |
| `heap_oos.cpp` | expand 정책(CBRD-27029) 등 | forward-walk 경로 무관 |

**결론: 이후 커밋 중 이 결함을 막거나 좁힌 것은 없다.**

## 7. 수정 방향 (설계 논의 대상 — 구현 아님)

바뀌어야 할 최소 계약: forward-walk의 확인이 "슬롯이 점유돼 있는가"에서 "**슬롯이 여전히 undo image가 소유하던 그 청크를 담고 있는가**"로.

- 유력안: `oos_record_header` 에 신원 필드(owner OID 또는 generation) 추가 + probe/`oos_delete` 대조, 불일치 시 no-op. 단일·멀티청크를 같은 근본 원인에서 함께 차단.
- 대안: 슬롯 재사용 유예(블록 완료까지) — 공간 회수율·bestspace 설계 비용이 있어 비교 대상.
- **온디스크 포맷 변경이므로 feat/oos 미출시인 지금이 마이그레이션 비용 0인 유일한 시점.**
- 후속 의존: 페이지 회수(CBRD-26786), flashback retention(CBRD-26847 FU-01)이 이 수정을 전제.

## 8. 결정적 재현 실험 설계 (별도 승인 필요 — 소스 훅 필요)

1. `vacuum_forward_walk_oos_delete_atomic` 의 `log_sysop_commit` 직후 worker를 멈추는 fault-injection 훅 (테스트 빌드 전용).
2. `BIT VARYING` 으로 OOS-backed 행 R1 insert → UPDATE → vacuum 유도 (`vacuum_log_block_pages=4`).
3. 훅에서 정지된 사이 별도 세션이 R2 insert (슬롯 재사용 확인: debug `oos.log` 의 OID 대조).
4. worker 재개(또는 kill -9 후 재기동) → 블록 재처리 → R2의 값 SELECT 가 실패하거나 오독되는지 확인.

## 9. 참고

- JIRA: [CBRD-26950](http://jira.cubrid.org/browse/CBRD-26950) (Status: Analysis, 2026-07-29 갱신)
- 발견 경위: PR #6986 (CBRD-26668) 코드 리뷰 finding #1/#2 — `cbrd-26668/2026-06-15-CBRD-26668-PR6986-code-review.md`
- 정상 동작 설명: `cbrd-26668/CBRD-26668-code-review-explanation.md` §7-5 (정정 포함)
- OOS 사양: `OOS-CONTEXT.md` (Known Bugs 표의 CBRD-26950 행)
