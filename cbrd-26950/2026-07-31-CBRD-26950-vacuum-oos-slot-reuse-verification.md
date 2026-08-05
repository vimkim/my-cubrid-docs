# CBRD-26950 — vacuum OOS 슬롯 재사용 데이터 손실: 현재 소스 검증 보고

- **작성일**: 2026-07-31 / **갱신**: 2026-08-05 (§8 런타임 재현 완료로 교체, Q4 정정, §8-5 부수 발견 추가)
- **검증 기준 커밋**: `0ad6afc0ff871f5aa6c002923868fc6527149ea0` (= `origin/feat/oos`, ahead/behind 0/0)
- **재현 기준 커밋**: `07fef9d48` (`feat/oos` + `origin/develop` 머지, debug_gcc 빌드) — §8
- **JIRA 앵커와의 관계**: JIRA 본문은 `2c329a4e0` 기준. 본 문서는 그 이후의 모든 변경(bestspace 리디자인 CBRD-26176 포함)을 반영한 현재 HEAD 재검증 결과.
- **작성 도구**: Claude Code (Fable 5) — 소스 무변경 (분석 + 런타임 재현)
- **판정**: **성립 — 런타임 재현 완료.** 소스 수정도 fault-injection 훅도 필요하지 않았다. 스톡 debug 빌드에서 `cubrid server stop` 만으로 재현되며, 커밋하고 그 뒤 한 번도 수정하지 않은 행이 판독 불가가 된다. 상세는 §8.

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

블록 재시도 + 슬롯 재사용 조합을 만드는 테스트가 **존재하지 않는다**(부재 ≠ 안전). 발현 시 증상이 에러·로그 없는 **무증상 데이터 손실**이라 사후 진단도 불가능한 부류이므로 심각도는 CRITICAL이 맞다.

> **2026-08-05 정정**: 이 답변은 원래 "결정적 재현에는 vacuum sysop 커밋 직후 worker를 멈추는 fault-injection이 필요하다"고 썼다. **틀렸다.** `cubrid server stop` 이 vacuum worker를 블록 중간에 버리므로(`vacuum.c:3493` 의 `thread_p->shutdown` 체크) 훅 없이 재현된다 — 즉 확률이 낮은 것도 아니고, OOS 부하가 있는 DB의 **평시 정상 종료**가 그대로 발현 조건이다. 크래시는 창을 넓히는 요인일 뿐 필수 조건이 아니다. §8 참조.

### Q5. "REMOVE 경로는 heap 레코드와 sysop으로 묶이고 MVCC version check가 있으니 문제없지 않나?"

정확하다 — 그리고 그래서 **REMOVE 경로는 이 이슈 대상이 아니다.** 슬롯 제거와 OOS 삭제가 한 sysop으로 원자적이고, 재시도 시 heap 슬롯의 MVCC 체크가 자연 멱등성을 준다. 버그는 **forward-walk 경로**다: UPDATE는 변환마다 새 OID를 발급하므로 옛 체인을 참조하는 살아있는 heap 레코드가 없고(undo image에만 존재), **MVCC 체크를 걸 대상 자체가 없다.** pass 1의 forward-walk는 heap 레코드를 건드리지 않아 어떤 heap 기반 게이트도 pass 2에서 같은 답을 낸다. heap이 슬롯 재사용에도 안전한 이유는 삭제 대상이 자기 몸에 MVCC 헤더(신원/가시성 메타데이터)를 지니기 때문이다 — vacuum이 지연 삭제하는 대상(heap 슬롯: MVCC 헤더, btree 엔트리: 키+MVCC info) 중 **OOS 청크만 신원 메타데이터가 없다.** identity 필드 제안은 새 발명이 아니라 이 기존 계약을 OOS에 채우는 것이다.

### Q6. "블록 전체를 단일 sysop으로 묶으면 되지 않나? (overflow 선례처럼)"

overflow 선례는 **레코드 단위** sysop이고 OOS도 이미 그렇게 한다. 블록 단위 sysop은 세 가지로 탈락: ① 블록=VACUUMED 표기는 **master가 비동기로** 기록하므로 "sysop 커밋 ~ VACUUMED 영속화" 사이 크래시에서 같은 버그가 재현 — 창이 좁아질 뿐 닫히지 않는다. ② `oos_delete_chain` 은 커밋 전에 페이지를 unfix하고 bestspace에 재등록하므로 **커밋 전 빈 슬롯이 물리적으로 노출**되는데, sysop abort 시 undo가 남이 차지한 슬롯에 옛 청크를 복원하려는 충돌 창이 레코드 단위에선 마이크로초, 블록 단위에선 **블록 처리 시간 전체**로 늘어난다. ③ 로그 31페이지 분량의 무한계 sysop 자체가 vacuum 설계와 충돌.

## 5-1. 수정 방식 그릴 결과 (2026-07-31 논의)

| 쟁점 | 결론 |
|---|---|
| "OID 재발급이 안 되거나 오래 걸리면?" | OOS OID는 물리 주소 — 재발급 절차가 없고 재점유가 곧 재등장. bestspace 즉시 재등록 + 최저 슬롯 우선이 재사용을 **촉진** |
| vacuum-side만 수정 (3안) | INTERRUPTED 스킵 = 영구 누수 회귀(CBRD-26668 목적 훼손), 레코드 단위 진행 영속화 = vacuum data 코어 수술(역방향 walk라 LSA 전진으로 표현 불가), 블록 sysop = 위 Q6 |
| forward-walk 폐지·슬롯 기반 재설계 | **undo image가 이미 완벽한 '삭제 대기 큐'** (영속 + MVCCID 게이팅 + 추가 쓰기 0). tombstone/영속 큐/orphan 스캔 GC 전부 그 큐를 재발명하며 "정확히 한 번 소비" 문제를 그대로 계승. 고장난 건 큐가 아니라 소비 단계의 신원 확인 하나 |
| owner OID vs generation | **저울은 generation 쪽.** owner OID는 stub 불변이 장점이나, `heap_attrinfo_insert_to_oos` 가 heap 슬롯 할당 **전에** 실행되므로(`heap_file.c:13128` → `heap_insert_logical` 순) INSERT 시점에 owner가 미존재 — backfill(핫패스 영구 비용) 또는 흐름 재배치(침습) 필요. generation은 온디스크 2곳(청크 헤더+stub) 변경이지만 쓰기 흐름 불변이고, 미출시라 포맷 변경은 지금 공짜 |
| 제3안: 생성 MVCCID 스탬프 | 탈락 — 같은 트랜잭션의 다중 UPDATE에서 스탬프 충돌, undo image의 insert MVCCID가 이미 vacuum에 지워졌을 수 있음 |
| generation 폭 | **uint32 충분** — 오탐에는 블록 재처리 창 안에 한 페이지 43억 insert/delete 사이클 필요(물리적 불가). 증가 시점은 행 UPDATE가 아니라 **페이지에 대한 청크 insert마다** (페이지 헤더 카운터 유력) |
| stub 크기 20B vs 24B | **20B** (OID 8 + length 8 + gen 4, 패딩 없음). stub은 행·컬럼마다 반복 지불하는 비용이고, variable area 내 오프셋이 임의라 24B 패딩이 8-정렬을 보장하지 못함(정렬은 리더 책임, PG TOAST 18B 선례). 미래 예약은 행당 반복인 stub이 아니라 체인당 1회인 청크 헤더에 |
| 연쇄 갱신 항목 | `OR_OOS_INLINE_SIZE` 16→20, demotion 수익성 문턱, 경계 테스트 9.1/9.2, OOS-CONTEXT 문서. redo/undo는 레코드 전체 이미지 물리 로깅이라 핸들러 불변. replication은 slave가 자기 `oos_insert` 를 수행하므로 generation도 slave 로컬 발급 |

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

- 유력안: `oos_record_header` 에 신원 필드(owner OID 또는 generation) 추가 + probe/`oos_delete` 대조, 불일치 시 no-op. 단일·멀티청크를 같은 근본 원인에서 함께 차단. **2026-07-31 그릴 결과 generation 우세 — §5-1 참조** (owner OID는 INSERT 시점 미존재 문제로 핫패스 backfill 또는 흐름 재배치 필요).
- 대안: 슬롯 재사용 유예(블록 완료까지) — 공간 회수율·bestspace 설계 비용이 있어 비교 대상.
- **온디스크 포맷 변경이므로 feat/oos 미출시인 지금이 마이그레이션 비용 0인 유일한 시점.**
- 후속 의존: 페이지 회수(CBRD-26786), flashback retention(CBRD-26847 FU-01)이 이 수정을 전제.

## 8. 런타임 재현 — 완료 (2026-08-05, 소스 무변경)

**재현됨.** 원래 계획했던 fault-injection 훅은 필요하지 않았다. 재현 스크립트: `cbrd-26950/cbrd-26950-poc.sh` (기준 커밋 `07fef9d48`, `debug_gcc` 프리셋). 전용 DB와 전용 `cubrid.conf` 를 만들어 쓰므로 설치본의 다른 DB는 건드리지 않고, 1회 약 4분이 걸린다.

### 8-1. 레시피

| 단계 | 내용 | 성립시키는 조건 |
|---|---|---|
| 1 | 5000B `BIT VARYING` 페이로드로 20000행 INSERT (전부 OOS 적재) | — |
| 2 | **단일 트랜잭션**으로 전체 UPDATE → 커밋 순간 20000개 옛 체인이 한꺼번에 회수 대상이 됨. 동시에 별도 세션 6개가 **같은 크기로** 계속 INSERT | ② 슬롯 재사용 |
| 3 | vacuum이 30%를 회수한 시점에 `cubrid server stop` | ③ 블록 중단 |
| 4 | 재기동 → vacuum이 같은 블록을 `start_lsa` 부터 재주행 | ① 신원 없는 probe |

UPDATE여야 하는 이유는 Q5와 같다. DELETE는 heap sysop 안에서 회수되고 MVCC 체크로 멱등하므로 이 경로가 아니다.

### 8-2. 결과

최종 파라미터로 연속 2회 재현. 두 증거가 **정확히 1:1** 로 맞았다.

| 실행 | 두 pass 모두에서 삭제된 OOS OID | 판독 불가해진 살아있는 행 | 대조군(pass 1 이전에 할당된 체인) |
|---|---|---|---|
| 1회차 | 293 | 293 | 무손상 |
| 2회차 | 163 | 163 | 무손상 |

피해 행은 **슬롯이 해제된 뒤에 INSERT·커밋되고 그 후 한 번도 수정되지 않은** 행이다. SELECT 시:

```
ERROR: Internal error: slot 1 on page 8081 of volume ".../oos26950" is not allocated.
```

대조군은 UPDATE 후 체인이 어떤 삭제보다 먼저 할당되어 재사용 슬롯에 있을 수 없는 행들이며, 두 실행 모두 무손상이었다 — 즉 손상은 "재사용된 슬롯"에만 정확히 국한된다.

### 8-3. 각 레버가 왜 필요한지 (실패한 시도 기록)

재현이 안 되는 조합이 여러 개 있어, 같은 길을 다시 걷지 않도록 남긴다.

| 문제 | 관찰 | 대응 |
|---|---|---|
| 블록이 아예 발행되지 않음 | 블록은 **다음 로그 레코드가 경계를 넘을 때만** 발행된다(`log_append.cpp:1376-1385`). UPDATE 후 로그를 더 쓰지 않으면 마지막 블록이 영원히 대기 | 뒤이어 로그를 더 밀어주는 워크로드를 둔다 (스크립트에서는 재사용용 INSERT가 겸함) |
| vacuum이 backlog를 항상 다 비움 | `cubrid server stop` 이 worker에 도달하기까지 **약 1.5초**, vacuum 회수율은 **초당 수천 개**(실측 1000~13000/s, 버퍼 온도에 따라 요동). 4000행 규모로는 매번 완주 | backlog를 20000행으로 키운다 |
| 배치 커밋 UPDATE로는 backlog가 안 쌓임 | vacuum 회수율 ≈ 클라이언트 생산율이라 backlog가 자라지 않는다 | UPDATE를 **단일 트랜잭션**으로 — 커밋 전까지 vacuum이 손대지 못한다 |
| 고정 sleep이 불안정 | 회수율이 실행마다 요동쳐 어떤 실행은 다 비우고 어떤 실행은 덜 비움 | **진행률 기반 정지**(`STOP_AT_PCT`, 기본 30%)로 폴링 |
| 재사용이 일어나지 않음 | 재시작 후에는 bestspace 캐시가 비어 있고 tier-3 sync가 파일 **앞쪽 100 페이지**만 훑는다(`oos_file.cpp` `oos_stats_sync_bestspace`, `oos_Find_best_page_limit`). 앞쪽이 꽉 차 있으면 새 페이지를 할당해버림 | 재사용 INSERT를 **삭제와 같은 서버 세션에서** vacuum과 동시에 돌린다 |
| 재사용이 최근 해제 슬롯을 못 따라감 | 중단된 블록의 이미 처리된 구간은 **가장 최근에 해제된** 슬롯이다. 단일 writer는 vacuum 속도를 못 따라가 그 구간이 재기동 시점에 비어 있음 → probe가 false로 정상 스킵 | writer를 6개로 병렬화 |

### 8-4. 재현으로 새로 확인된 사실 (§2·§3 보정)

- **§2 T5 보정**: 중단이 서버 에러 로그에 `Processing log block N is interrupted!` 로 남는 것은 master가 종료 전에 finished-job 큐를 처리한 경우뿐이다. 그러지 못하면 블록은 vacuum data 페이지에 **IN_PROGRESS 로 남고**, 다음 부팅의 `vacuum_data_load_and_recover` 가 `set_interrupted()` 로 바꾼다(`vacuum.c:4398-4403`). **재주행은 어느 쪽이든 일어나므로**, 로그에 그 경고가 없다는 것이 안전의 근거가 되지 않는다. 실제로 경고가 0건인 실행에서도 재현됐다.
- **§2 T3 보정**: "삭제 즉시 bestspace 재등록"은 맞지만, 그 재등록은 **프로세스 메모리 캐시**에 남는다. 재시작을 건너뛰면 재사용이 사실상 즉시 일어나고, 재시작이 끼면 tier-3 sync의 100 페이지 한계 때문에 오히려 잘 일어나지 않는다. 즉 **재사용 창이 가장 넓은 구간은 삭제와 같은 세션 안**이다.
- **`vacuum_disable=yes` 는 backlog를 보존하지 못한다**: 그 부팅에서는 블록이 발행되지 않고(`vacuum_produce_log_block_data` 조기 return), 재활성화 시 `vacuum_is_empty()` 경로가 `last_blockid` 를 현재 로그 끝으로 밀어 대기 블록을 버린다(`vacuum.c:4430-4452`). 크래시 복구가 아니면 `vacuum_recover_lost_block_data` 도 조기 return한다. 재현 시나리오를 단계별로 끊는 용도로는 쓸 수 없다.

### 8-5. 부수 발견 (CBRD-26950과 별개, 별도 티켓 후보)

1. **종료 중 인터럽트가 debug 빌드에서 서버를 abort시킨다.** 서버 종료로 클라이언트의 OOS INSERT가 인터럽트되어 `pgbuf_fix` 가 `ER_INTERRUPTED`(-4)로 실패하면 `file_alloc` 이 정상적으로 에러를 반환하는데, `oos_file_alloc_new` 가 이를 있을 수 없는 상황으로 보고 무조건 `assert (false)` 를 건다 (`oos_file.cpp:1892`). 인터럽트는 정상 경로이므로 에러를 전파해야 할 자리다. 코어 스택:

   ```
   oos_file_alloc_new (oos_file.cpp:1892)  ← assert (false)
     ← oos_find_best_page ← oos_insert_single_page_batch
     ← oos_insert_many ← heap_oos_insert_serialized_values
     ← heap_attrinfo_insert_to_oos ← heap_attrinfo_transform_to_disk_internal
   ```

2. **`oos_insert_many` 에 디버그 로그가 없다.** `oos_insert` 에는 `oos_debug ("inserted to oid=...")` 가 있는데(`oos_file.cpp:1219`) 실제 INSERT 경로인 배치 API(CBRD-27006)에는 없어서, `oos.log` 에 **삭제만 남고 삽입은 남지 않는다.** 이 때문에 재현 초기에 "OOS가 아예 트리거되지 않는다"고 오판했다. 슬롯 재사용을 로그만으로 직접 증명할 수 없게 만드는 관측성 공백이므로, 배치 경로에도 같은 로그를 넣는 것이 좋다.

## 9. 참고

- JIRA: [CBRD-26950](http://jira.cubrid.org/browse/CBRD-26950) (Status: Analysis, 2026-07-29 갱신)
- 재현 스크립트: `cbrd-26950/cbrd-26950-poc.sh` (§8)
- 발견 경위: PR #6986 (CBRD-26668) 코드 리뷰 finding #1/#2 — `cbrd-26668/2026-06-15-CBRD-26668-PR6986-code-review.md`
- 정상 동작 설명: `cbrd-26668/CBRD-26668-code-review-explanation.md` §7-5 (정정 포함)
- OOS 사양: `OOS-CONTEXT.md` (Known Bugs 표의 CBRD-26950 행)
