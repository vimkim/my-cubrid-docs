# 단건 client fetch OOS Expand flip — future agent 실행 계획서

> **이 문서의 목적**: `locator_lock_and_return_object()` 의 fetch 정책을
> `HEAP_WITHOUT_OOS_EXPAND` → `HEAP_WITH_OOS_EXPAND` 로 flip 하는 작업을,
> 나중에 컨텍스트 없이 투입되는 agent 가 **정확하게** 수행할 수 있도록 필요한 모든
> 근거·함정·검증 절차를 기록한다.
>
> **이슈 소속**: 사용자 결정 (2026-07-07) — PR #7416 (CBRD-27029) 과는 **별도 이슈**로 수행한다.
> 이 gap 은 CBRD-26948 issue 문서의 ANALYSIS 항목("단일 객체 fetch `xlocator_fetch` →
> 워크스페이스 디코드 `tf_disk_to_mem` 도 같은 노출 가능성")에 기등재되어 있으므로 우선 이 디렉터리에
> 둔다. 전용 CBRD 번호가 발급되면 문서를 그쪽으로 이동할 것.

## 1. 문제 정의

CS-mode 단건 object fetch (`xlocator_fetch` 등) 는 `locator_lock_and_return_object()` 가 채운
`assign->recdes` 를 그대로 `LC_COPYAREA` 에 담아 client 로 보낸다. 현재 이 fetch 는
`HEAP_WITHOUT_OOS_EXPAND` 라서, OOS row 의 record 에는 inline OOS OID slot (16B stub) 이
값 대신 남은 채 wire 를 넘어간다. client decoder (`tf_disk_to_mem`, `load_object.c` 계열) 는
OOS 를 전혀 모르므로 stub 을 값으로 오독하거나 깨진 값을 만든다.

- 위치 (PR #7416 head `309753de6` 기준): `src/transaction/locator_sr.c:2336–2339`.
  해당 call 위에 in-code TODO 존재:
  `/* TODO (CBRD-26847): analysis needed - this single-object client fetch keeps inline OOS OID slots
     (pre-policy behavior), while xlocator_fetch_all expands them; CS-mode clients cannot resolve OOS. */`
- Greptile 이 PR #7416 review 에서 P1 으로 지적 (comment id 3534467833). 분석:
  `../cbrd-27029/CBRD-27029-greptile-analysis.md` Comment 1.
- **Pre-existing gap** 이다: base `feat/oos` 의 `heap_init_get_context` 가 `expand_oos = false` 로
  고정했으므로 OOS 도입 이후 줄곧 이 동작이었다. PR #7416 은 이를 가시화만 했다.

## 2. 이력 (왜 아직 안 고쳤나)

| 시점 | 사건 |
|------|------|
| PR #7093 (CBRD-26729) | expand 를 opt-in 으로 전환하면서 fetch_all 형제 경로는 전환됐지만 단건 경로는 원래부터 expand 없음 |
| PR #7416 old head `846b5c7cf` | 이 site 를 WITH 로 flip 했었음 ("의도된 flip", CBRD-26948 계열 일부 해소로 문서화) |
| 2026-07-07 minimization | PR #7416 을 zero-behavior-change 계약으로 squash (`309753de6`) 하며 flip **revert** — 정책 가시화와 동작 수정을 분리하기 위한 의도적 결정 |
| 2026-07-07 grilling | Greptile P1 대응으로 flip 을 **별도 이슈**로 확정, 본 계획서 작성 |

## 3. 변경 내용 (핵심은 1-token + 주석)

`src/transaction/locator_sr.c` `locator_lock_and_return_object()`:

```c
/* AS-IS */
  scan = locator_get_object (thread_p, oid, class_oid, &assign->recdes, assign->ptr_scancache, op_type, lock_mode, COPY,
			     chn, HEAP_WITHOUT_OOS_EXPAND);

/* TO-BE */
  /* Raw RECDES is shipped to the client via LC_COPYAREA; CS-mode clients cannot resolve
   * inline OOS OID slots, so expand them here (same rule as xlocator_fetch_all). */
  scan = locator_get_object (thread_p, oid, class_oid, &assign->recdes, assign->ptr_scancache, op_type, lock_mode, COPY,
			     chn, HEAP_WITH_OOS_EXPAND);
```

기존 TODO 주석 (CBRD-26847 analysis needed) 은 삭제하고 위 KEEP-style 근거 주석으로 교체한다
(census 규칙: WITH site 에는 raw-byte 소비 근거를 주석으로 남긴다).

참고: `846b5c7cf` 에 동일 취지의 hunk 가 있으므로 cherry-pick 소스로 쓸 수 있다
(`git show 846b5c7cf -- src/transaction/locator_sr.c`). 단, 그 head 와 현재 head 는 주변 코드가
다르므로 반드시 재확인.

## 4. 안전성 근거 (2026-07-07 코드 검증 완료 — flip 이 "correct" 한 이유)

이 flip 의 유일한 mechanical risk 는 **expansion 으로 record 가 caller buffer (copy area) 보다
커지는 경우**다. CBRD-26985 (xlocator_lock_and_fetch_all copy-area corruption) 와 동일한 모양새.
현재 코드는 이를 다음과 같이 방어한다 (검증 위치 포함):

1. `heap_init_get_context` (`src/storage/heap_file.c:27085`):
   `context->keep_recdes_buffer = recdes != NULL && recdes->data != NULL && !data_is_scan_cache_area;`
   — `assign->recdes.data` 는 copy area 안을 가리키는 caller-positioned buffer 이므로
   **`keep_recdes_buffer = true`** 가 된다.
2. `heap_oos_build_record` (`src/storage/heap_oos.cpp:250–263`):
   - `rec->area_size < new_length` 이고 `keep_recdes_buffer` 면 **rebinding 하지 않고**
     `rec->length = -(new_length)` + `S_DOESNT_FIT` 반환 (CBRD-26985 fix).
   - scan-cache rebinding (`assign_recdes_to_area`) 은 caller buffer 가 아닐 때만 일어난다.
3. `locator_lock_and_return_object` 의 기존 계약 (함수 header 주석): "If the object does not fit in
   assigned return area, the length of the object is returned as a negative value in the area recdes
   length." — 음수 length 는 locator 의 표준 copy-area grow-and-retry protocol 로 처리된다.
   즉 expansion 초과분은 **더 큰 copy area 로 재시도**될 뿐 corruption 이 없다.
4. 확장된 record 는 `OR_MVCC_FLAG_HAS_OOS` flag 가 제거되고 VOT 가 4-byte offset 으로 재작성된
   평범한 record 다 (`heap_oos_build_record:276–295`) — client decoder 가 그대로 이해한다.
   CHN 등 header 나머지는 verbatim 복사라 cache coherence 의미 불변.

## 5. Flip 전 반드시 재검증할 것 (future agent checklist)

- [ ] **5 caller 의 S_DOESNT_FIT 처리 전수 확인** (head 기준 line 은 re-grep):
  `locator_sr.c:2523` (`xlocator_fetch` — instance, 유일하게 OOS 실노출 경로),
  `:2596` (`xlocator_get_class`), `:3158` / `:3252` (`xlocator_fetch_lockset` class/instance),
  `:11648` (`xlocator_fetch_lockhint_classes`). class record 는 OOS 불가라 no-op 이지만
  음수 length 전파가 각 caller 의 retry/skip 로직과 맞물리는지 확인.
  특히 prefetch 성 caller 가 S_DOESNT_FIT 을 fatal 로 다루지 않는지.
- [ ] `locator_return_object_assign` 이 음수 length (S_DOESNT_FIT) 경로에서 expansion 후 크기를
  기준으로 area growth 를 요청하는지 (기존 non-OOS oversize record 와 동일 protocol 인지) 확인.
- [ ] base 가 그 사이 바뀌었는지 확인: PR #7416 merge 후에는 `HEAP_OOS_EXPAND_POLICY` enum 인자가
  이미 있으므로 1-token flip. merge 전이라면 이 계획서의 전제(정책 인자 존재)가 성립하지 않는다.
- [ ] CBRD-26948 본체 (unloaddb `xlocator_fetch_all` value-loss) 와의 중복/순서 조정 —
  같은 census 규칙("클라이언트로 나가는 raw RECDES 는 Expand")의 두 적용 지점이다.
  compactdb 는 재저장 semantics 때문에 blanket expand 금지 (CBRD-26948 문서 참고).
- [ ] `heap_get_class_record` / class-record 경로에 의도치 않은 영향 없는지 (class 는 OOS 불가,
  expand 는 `heap_recdes_contains_oos` guard 로 no-op — `heap_oos.cpp:372`).

## 6. 테스트 계획

1. **재현 (flip 전, 버그 확인)**: CS-mode 에서 단건 object fetch 로 OOS row 를 받는 시나리오.
   query 경로(SELECT)는 server-side 실행이라 이 경로를 타지 않는다 — object-level fetch 가 필요:
   trigger/method 평가, workspace 객체 접근 (`CALL` on instance / object reference deref) 등.
   확실한 관측법 (SA 아님 주의 — 이 경로는 CS 전용):
   `gdb cub_server` follow-fork-mode parent + `b locator_lock_and_return_object` 후
   csql(CS) 에서 시나리오 실행 → `assign->recdes` 에 `OR_MVCC_FLAG_HAS_OOS` 가 남아 wire 로
   나가는지 확인 (관측 레시피는 memory `project_oos_select_no_resolve_verified` 참고).
2. **수정 후 검증**: 같은 시나리오에서 client 수신 값 byte-equality (md5). OOS blob 을
   copy-area 기본 크기보다 크게 만들어 **S_DOESNT_FIT grow-retry 경로를 강제로 통과**시킬 것.
3. **회귀**: `just build-test` (unit 23종) + 기존 `test_oos_sql_visible_version` +
   OOS row INSERT/UPDATE/DELETE/SELECT round-trip, `cubrid checkdb`.
4. CI: `/run sql medium` 최소; client-fetch 를 실제로 두드리는 shell TC 가 있으면 추가.

## 7. Acceptance criteria

- CS-mode 단건 fetch 로 수신한 OOS row 의 모든 컬럼 값이 server 값과 byte-identical.
- `OR_MVCC_FLAG_HAS_OOS` 가 설정된 record 가 `LC_COPYAREA` 로 전송되는 경로 0건
  (xlocator_fetch / fetch_all / lock_and_fetch_all 모두 — 후자 둘은 기존 WITH 유지 확인만).
- copy-area 보다 큰 expansion 에서 grow-retry 성공, corruption 없음 (CBRD-26985 재발 방지).
- 기존 대비 non-OOS row 의 단건 fetch 동작/성능 불변 (`heap_recdes_contains_oos` early-return).

## 8. 참고 문서

- `../cbrd-27029/CBRD-27029-greptile-analysis.md` — Greptile 4건 분석 (본 gap 은 Comment 1)
- `../cbrd-27029/CBRD-27029-greptile-fix-plan.md` — 분리 결정 기록
- `../cbrd-27029/CBRD-27029-expand-raw-records.md` — census 전수표 (old head `846b5c7cf` 기준, stale 주의)
- `~/gh/my-cubrid-jira/issues/CBRD-26948-unloaddb-compactdb-oos.md` — 상위 이슈 (fetch_all value loss)
- engine repo `CBRD-26847` branch `33b90a444` — visible-version census flip 커밋 (P2 3건의 소관)
