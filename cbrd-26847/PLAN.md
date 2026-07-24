# CBRD-26847 OOS Expand / raw RECDES 전수 조사 Agent Plan

## Document Status

| 항목 | 값 |
|---|---|
| 상태 | Ready for execution |
| 대상 이슈 | CBRD-26847 — `[OOS] [M2] raw RECDES 소비 경로와 OOS Expand 정책 전수 조사` |
| 선행 이슈 | CBRD-27029 — 명시적 `HEAP_RECDES_CONSUMPTION_POLICY` 도입 |
| 기준 worktree | `/home/vimkim/gh/cb/CBRD-26847-oos-visible-version` |
| 기준 branch | `CBRD-26847-oos-visible-version` |
| 최초 source anchor | `6816023df4ed910687523ab4d34bf667ab32b9cd` |
| CBRD-27029 merge | `de84fa59e16aa0b863cfdbda4655f6c371dc0f86` |
| 규범 문서 | `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` |
| 이슈 원문 snapshot | `/home/vimkim/gh/my-cubrid-jira/issues/CBRD-26847-oos-raw-recdes-expansion-audit_6816023_codex.md` |
| 폐기된 옛 계획 | `CBRD-26847-oos-visible-version-expansion.md` — 조사 seed로만 사용 |
| 조사 산출물 위치 | `/home/vimkim/gh/my-cubrid-docs/cbrd-26847/audit/` |

이 문서의 목적은 검색 결과를 나열하는 것이 아니라, **OOS inline stub을 포함할 수 있는 heap instance
`RECDES`의 생성·전달·소비 경로에 누락이 없음을 재현 가능한 방식으로 입증**하는 것이다.

최초 source anchor와 아래 개수는 계획 작성 시점의 기준값일 뿐이다. 실행 시 `HEAD`가 달라졌다면 모든 검색,
호출 관계, line reference와 개수를 새 `HEAD` 기준으로 다시 고정한다. 과거 CBRD-26847 문서의
visible-version 전용 설계와 CBRD-27029 문서의 옛 함수명·인자는 역사적 입력일 뿐 완료 근거로 사용하지 않는다.

## 1. 조사 결과로 답해야 하는 질문

조사가 끝나면 다음 질문에 각각 코드 근거와 테스트 근거로 답할 수 있어야 한다.

1. OOS stub을 포함할 수 있는 heap instance `RECDES`를 얻는 모든 경로는 무엇인가?
2. 각 경로의 최종 소비자는 record body 중 어떤 byte range를 어떤 목적으로 읽는가?
3. 각 소비자는 record-level Expand, attribute-level Resolve, stored-form 유지 중 무엇이 필요한가?
4. 현재 전달되는 `HEAP_RECDES_CONSUMPTION_POLICY`와 실제 처리가 그 요구사항과 일치하는가?
5. 명시적 policy를 거치지 않는 WAL, CDC/flashback, replication, network, utility 경로도 동일한 기준으로
   분류되었는가?
6. 불필요한 Expand 때문에 대용량 OOS 값을 읽거나 메모리를 확장하는 경로는 없는가?
7. undo/redo, MVCC, vacuum 등 물리 이미지를 보존해야 하는 경로에서 stub이 잘못 materialize되지 않는가?
8. 정방향 조사 집합과 역방향 조사 집합이 서로 닫혔으며 미분류 후보가 0개인가?

## 2. 변경할 수 없는 OOS 불변식

| 소비 유형 | 필요한 처리 | 판단 근거 |
|---|---|---|
| raw logical full-record 또는 variable-area 소비 | `HEAP_RECDES_CONSUME_RAW_BYTES` / Expand | 소비자가 on-disk stub이 아니라 논리값 byte를 직접 기대한다. |
| attribute layer를 통한 값 접근 | stored form + Resolve | `heap_attrvalue_read_oos_inline()` → `oos_read()`가 필요한 속성만 읽는다. |
| WAL undo/redo, recovery, MVCC, vacuum의 물리 이미지 | stored form 유지 | 기존 record version과 head OOS OID 소유 관계를 보존해야 한다. |
| header, fixed area, CHN, existence만 읽는 raw 소비 | stored form 유지 | OOS stub이 있는 variable area를 논리값으로 해석하지 않는다. |
| record body를 사용하지 않는 경로 | stored form 유지 | Expand의 정확성 이득이 없고 I/O·메모리 비용만 발생한다. |
| 여러 종류의 소비자를 대신하는 wrapper | caller policy 전달 | wrapper가 단일 보수값으로 모든 호출자의 의미를 덮어쓰면 안 된다. |

추가 불변식:

- OOS inline stub은 head OOS OID 8 byte와 full length 8 byte로 구성된 16 byte 표현이다.
- Expand는 record 안의 모든 inline stub을 논리값으로 바꾸는 record-level eager 작업이다.
- Resolve는 attribute 단위 lazy 작업이다.
- 각 OOS value chain은 하나의 논리적 heap record version에만 소유된다. version 간 공유를 가정하지 않는다.
- `COPY`/`PEEK`는 버퍼 소유권 정책이고, OOS 소비 정책이 아니다.
- “현재 이 class에는 OOS 속성이 없다”만으로 stored form을 정당화하지 않는다. 코드 계약과 byte 소비 범위로
  판정한다.

## 3. 조사 범위

### 포함

- `heap_next`, `heap_prev`, `heap_get_visible_version`, `heap_scan_get_visible_version`
- `locator_lock_and_get_object`, `locator_lock_and_get_object_with_evaluation`, `locator_get_object`
- 위 API를 감싸거나 내부에서 policy를 고정하는 모든 heap/locator wrapper
- heap instance `RECDES`를 copy area, network, client, callback 또는 다른 내부 구조로 전달하는 경로
- insert/update/delete/reinsert와 partition 이동 등 다른 heap record로 다시 쓰는 경로
- WAL undo/redo image의 생성, 복원, 해석 경로
- MVCC old version, vacuum, rollback/recovery 경로
- CDC 및 flashback의 undo/redo `RECDES` 재구성과 logical value 생성 경로
- replication/HA log 생성·전송·적용 경로
- unload/load, compactdb 등 조사 중 발견되는 utility 경로
- OOS 지원 여부가 schema, class representation 또는 오류 분기에서 달라지는 경로

### 제외하되 검색 후보로 발견되면 제외 근거를 기록

- B-tree, sort, list file 등 heap instance가 아닌 `RECDES`
- OOS chunk 자체를 저장하는 `OOS_RECDES`
- logical `DB_VALUE`에서 heap record를 만들기 전 단계
- record body에 접근하지 않고 OID, scan position 또는 상태만 다루는 코드

이름이 `RECDES`라는 이유만으로 포함하거나, heap 함수 안에 있다는 이유만으로 제외하지 않는다. 항상
**record provenance와 terminal consumer**를 추적해 결정한다.

## 4. 필수 산출물

실행 에이전트는 먼저 `/home/vimkim/gh/my-cubrid-docs/cbrd-26847/audit/`를 만들고 다음 문서를 유지한다.

| 파일 | 역할 |
|---|---|
| `AUDIT-INVENTORY.tsv` | 정방향·역방향 조사 결과의 단일 원장 |
| `SEARCH-LEDGER.md` | 실행한 검색, 후보 개수, 포함·제외·중복·미결정 합계 |
| `FINDINGS.md` | 오분류, 누락, 과도한 Expand와 수정 또는 후속 이슈 판단 |
| `VERIFICATION.md` | 최종 commit, build/test 명령, 결과, 동적 관찰 근거 |
| `FOLLOWUPS.md` | 별도 설계·protocol 변경이 필요한 후속 작업. 없으면 “없음”을 명시 |

### `AUDIT-INVENTORY.tsv` 필수 열

다음 header를 그대로 사용한다.

```text
id	direction	origin_kind	producer	fetch_api	current_policy	wrapper_chain	terminal_consumer	operation	byte_range	oos_capable	classification	required_handling	current_handling	verdict	evidence	test	finding_id	followup
```

작성 규칙:

- 정방향 행은 `F-001`, 역방향 행은 `R-001`, 명시적 제외 행은 `X-001`처럼 안정적인 ID를 부여한다.
- `evidence`에는 `path:line`, symbol, 축약하지 않은 call chain을 함께 적는다.
- line number만 적지 않는다. 최종 검증 때 line 이동에 견딜 수 있도록 symbol을 반드시 포함한다.
- `byte_range`는 `full`, `variable`, `fixed`, `header/CHN`, `none` 중 하나로 시작하고 필요하면 상세를 덧붙인다.
- `classification`은 `EXPAND`, `RESOLVE`, `PRESERVE_PHYSICAL`, `STORED_SAFE`, `NO_BODY`,
  `PROPAGATE`, `EXCLUDED` 중 하나다.
- `verdict`는 `CORRECT`, `BUG`, `OVER_EXPAND`, `CONTRACT_GAP`, `FOLLOWUP`, `EXCLUDED` 중 하나다.
- 모르는 값은 빈칸으로 두지 말고 `TBD`로 적는다. phase gate에서는 `TBD`가 0이어야 한다.
- 하나의 fetch가 여러 terminal consumer로 갈라지면 소비자별 행을 만든다.
- 정방향 행과 역방향 행이 같은 경로를 나타내더라도 삭제하지 말고 서로의 ID를 evidence에 연결한다.

### `SEARCH-LEDGER.md` 필수 기록

각 검색마다 다음을 남긴다.

```text
검색 목적:
source anchor:
명령 또는 semantic query:
raw candidate 수:
included:
excluded:
duplicate:
pending:
새로 발견한 symbol/alias/callback:
다음 검색어:
```

항상 아래 식이 맞아야 한다.

```text
raw candidate = included + excluded + duplicate + pending
```

## 5. 계획 작성 시점의 source baseline

실행 시작 시 아래 값을 재검증한다.

- 명시적 policy를 받는 공개 API: 7개
  - heap 4개: `heap_next`, `heap_prev`, `heap_get_visible_version`,
    `heap_scan_get_visible_version`
  - locator 3개: `locator_lock_and_get_object`,
    `locator_lock_and_get_object_with_evaluation`, `locator_get_object`
- 현재 source의 실제 호출 인자 기준:
  - `HEAP_RECDES_CONSUME_RAW_BYTES`: 25개
  - `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`: 59개
- 내부 policy 또는 고정 결정을 가진 대표 wrapper:
  - `heap_first`, `heap_last`, `heap_next_1page`
  - `heap_next_record_info`, `heap_prev_record_info`
  - scan range 관련 helper
- `heap_next_sampling`은 현재 `src`에 존재하지 않는다. 과거 이슈 설명의 API 목록을 그대로 복사하지 않는다.
- CBRD-26847 관련 TODO가 현재 `heap_file.h`, `heap_file.c`에 남아 있다. TODO는 후보 seed이지
  정확성의 증거가 아니다.

기준 개수가 달라지면 오류로 중단하지 않는다. `HEAD`, 새 개수와 변화 원인을 `SEARCH-LEDGER.md`에 기록하고
현재 source를 기준으로 계속한다.

## 6. 실행 절차와 phase gate

### Phase 0 — 기준점 고정과 사전 점검

1. `cubrid-oos-context` 지침에 따라 `OOS-CONTEXT.md` 전체를 다시 읽고 last-updated와 source 사이의
   차이를 기록한다.
2. `cubrid-jira`로 live CBRD-26847, CBRD-27029를 읽고 이슈 원문 snapshot 및 현재 source와 비교한다.
3. 환경, branch, `HEAD`, dirty worktree를 기록한다. 기존 사용자 변경은 수정하거나 되돌리지 않는다.
4. CBRD-27029 merge가 현재 `HEAD`의 조상인지 확인한다.
5. 필수 산출물의 skeleton을 만들고 모든 파일에 source anchor를 적는다.
6. baseline 검색을 다시 실행하고 개수를 기록한다.

권장 명령:

```bash
bash /home/vimkim/.agents/skills/cubrid-oos-context/scripts/validate-env.sh "$PWD"
git status --short
git rev-parse HEAD
git merge-base --is-ancestor de84fa59e16aa0b863cfdbda4655f6c371dc0f86 HEAD
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_CONSUMPTION_POLICY|HEAP_RECDES_(CONSUME|DONT_CONSUME)_RAW_BYTES' src unit_tests
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'TODO.*CBRD-26847|CBRD-26847.*TODO' src unit_tests
```

Gate 0:

- source anchor, branch, dirty files와 CBRD-27029 ancestry가 기록되어 있다.
- 5개 산출물이 존재하고 같은 source anchor를 가리킨다.
- baseline 후보 수와 계획 작성 시점의 차이가 설명되어 있다.

### Phase 1 — 명시적 policy에서 시작하는 정방향 조사

1. enum 정의, 모든 명시적 enum 값, policy parameter와 member를 찾는다.
2. 공개 API의 직접 호출뿐 아니라 내부 helper, wrapper, callback을 따라간다.
3. 각 fetch 결과가 소멸할 때까지 추적해 terminal consumer를 찾는다.
4. terminal consumer가 읽는 byte range와 operation을 기록한다.
5. 소비 의미에 따라 `EXPAND`, `RESOLVE`, `PRESERVE_PHYSICAL`, `STORED_SAFE`, `NO_BODY`,
   `PROPAGATE`로 분류한다.
6. 현재 policy/처리와 필요한 처리를 비교해 verdict를 기록한다.

검색 seed:

```bash
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_CONSUMPTION_POLICY' src unit_tests
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_CONSUME_RAW_BYTES' src unit_tests
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'HEAP_RECDES_DONT_CONSUME_RAW_BYTES' src unit_tests
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'heap_(next|prev|get_visible_version|scan_get_visible_version)[[:space:]]*\(' src unit_tests
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'locator_(lock_and_get_object|lock_and_get_object_with_evaluation|get_object)[[:space:]]*\(' src unit_tests
```

`rg` 결과만으로 호출 관계를 확정하지 않는다. 함수 포인터, macro, callback, overload는 language-server
references와 caller/callee 본문을 함께 확인한다.

Gate 1:

- 모든 명시적 policy occurrence와 policy를 내부 고정하는 wrapper에 `F-*` 행이 있다.
- 각 `F-*` 행이 terminal consumer 또는 `NO_BODY` 종점에 도달한다.
- `current_policy`, `classification`, `required_handling`, `verdict`의 `TBD`가 0이다.

### Phase 2 — 소비자에서 시작하는 역방향 조사

정방향 API 목록을 재사용하는 데 그치지 말고, raw `RECDES` 소비 행위에서 독립적으로 시작한다.

1. `RECDES.data`, raw copy/compare, OR decoding, copyarea packing, log image extraction을 검색한다.
2. heap insert/update/reinsert에 넘기는 `RECDES`의 provenance를 역추적한다.
3. client/network, locator, replication, utility, CDC/flashback에서 record image를 다루는 코드를 검색한다.
4. 각 terminal consumer에서 producer까지 역추적한다.
5. 명시적 fetch policy에 도달하지 않으면 아래 중 하나에 도달할 때까지 계속한다.
   - attribute Resolve
   - record construction 전에 이미 logical `DB_VALUE`
   - WAL/undo/redo physical image
   - network/copyarea에서 온 heap instance
   - non-heap `RECDES`
6. non-heap과 OOS chunk 후보도 버리지 말고 `X-*` 행에 제외 근거를 기록한다.
7. 새 alias, helper, callback을 발견할 때마다 검색어에 추가한다. 새 symbol이 나오지 않을 때까지 반복한다.

최소 검색 seed:

```bash
rg -n --glob '*.{c,cc,cpp,h,hpp}' '\bRECDES\b|RECDES[[:space:]]*\*' src
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'recdes[^;]*\.data|recdes->data|\.data[^;]*recdes' src
rg -n --glob '*.{c,cc,cpp,h,hpp}' '\b(memcpy|memmove|memcmp)[[:space:]]*\(' src
rg -n --glob '*.{c,cc,cpp,h,hpp}' '\bor_(init|unpack|unpack_|get_|put_)|OR_BUF' src
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'LC_COPYAREA|copyarea|S_DOESNT_FIT' src
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'log_(append|extract|read|copy)|undo|redo|mvcc|vacuum' src
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'cdc_|flashback|replication|repl_|ha_' src
rg -n --glob '*.{c,cc,cpp,h,hpp}' 'heap_(insert|update|delete|reinsert)|locator_(insert|update|delete)' src
```

위 검색은 후보 생성용이다. 예를 들어 모든 `memcpy`를 조사 원장에 넣는 것이 아니라, `RECDES.data`의 alias와
크기가 도달하는 호출만 포함한다. 반대로 변수 이름에 `recdes`가 없더라도 alias된 `char *`, `OR_BUF`,
copyarea slot으로 이동한 record body는 놓치지 않는다.

특히 별도 확인할 경로:

- `cdc_get_recdes()`가 undo/redo image를 어떻게 재구성하는지
- `cdc_make_dml_loginfo()`와 flashback 호출이 값 읽기에 attribute Resolve를 실제로 사용하는지
- schema representation 변화와 오류 분기에서도 OOS 값이 누락되지 않는지
- replication이 physical/logical 어느 이미지를 보내며 수신 측에서 어떻게 materialize하는지
- utility가 record 전체를 직접 직렬화하는지, attribute layer를 사용하는지

Gate 2:

- 모든 raw candidate가 `R-*` 또는 `X-*` 행으로 회계 처리되어 `pending = 0`이다.
- 모든 `R-*` 행의 producer/provenance와 terminal consumer가 모두 알려져 있다.
- 각 logical consumer가 Expand 또는 Resolve 중 하나에 연결된다.
- 각 physical consumer가 stored form 유지에 연결된다.

### Phase 3 — 정방향·역방향 closure와 조사 동결

집합을 다음과 같이 정의한다.

- `F`: 명시적 policy 값, policy parameter, 내부 고정 wrapper에서 시작한 모든 정방향 경로
- `R`: heap instance `RECDES` terminal consumer에서 시작한 모든 역방향 경로

closure 조건:

1. 모든 `F` 원소가 terminal consumer와 하나의 classification에 도달한다.
2. 모든 `R` 원소가 명시적 fetch policy 또는 명확한 non-fetch 처리
   (`Expand`, `Resolve`, physical preservation)에 도달한다.
3. 설명되지 않은 forward-only 경로가 0개다.
4. 설명되지 않은 reverse-only 경로가 0개다.
5. 모든 검색의 `pending` 합계가 0이다.
6. `AUDIT-INVENTORY.tsv`의 `TBD`가 0이다.
7. 새로 발견한 symbol을 seed에 추가해 재검색했을 때, **연속 두 번의 closure pass에서 새 함수·경로가
   발견되지 않는다.**

이 gate를 통과하기 전에는 source code를 수정하지 않는다. 조사 중 명백한 오분류를 발견해도
`FINDINGS.md`에 먼저 기록한다. 이렇게 해야 수정 후 검색 결과가 바뀌어 최초 누락 증거를 잃지 않는다.

Gate 3:

- inventory source anchor가 고정되어 있다.
- forward/reverse-only unexplained가 각각 0이다.
- 두 번의 no-new-path pass가 날짜, 명령과 함께 기록되어 있다.
- 수정 전 inventory snapshot이 보존되어 있다.

### Phase 4 — finding 분류와 변경

finding 우선순위:

| 등급 | 의미 | 기본 처리 |
|---|---|---|
| P0 | 물리 이미지/OOS chain 소유권을 깨뜨릴 가능성 | 즉시 중단하고 별도 설계 검토 |
| P1 | 논리 소비자에게 stub/잘못된 값이 노출될 수 있음 | CBRD-26847에서 수정 및 회귀 테스트 |
| P2 | 불필요한 Expand로 OOS I/O·메모리 증가 | 단순 policy 수정은 CBRD-26847에서 처리 |
| P3 | wrapper 계약, 주석, 명명 또는 테스트 근거 부족 | 가능한 범위에서 계약·테스트 보강 |

이 이슈에서 바로 처리할 수 있는 변경:

- 명백한 policy 상수 교정
- caller policy를 누락한 단순 wrapper의 parameter 전달
- 실제 소비 의미와 어긋난 주석·계약 보강
- 좁은 회귀 테스트와 관찰 가능성 보강

후속 이슈로 분리할 변경:

- client/server protocol 또는 copyarea layout 변경
- WAL format, recovery semantics, OOS ownership model 변경
- 여러 subsystem의 공통 API를 다시 설계해야 하는 변경
- 성능 정책에 별도 제품 결정을 요구하는 변경

후속 이슈로 분리해도 현재 경로의 inventory 행과 위험 설명은 제거하지 않는다. `FOLLOWUPS.md`에
영향 경로, 임시 안전성, 필요한 결정, 추천 테스트를 적고 `finding_id`로 연결한다.

수정 후에는 새 `HEAD`로 전체 inventory를 다시 생성하거나 재검증하고, 각 행에 이전/이후 verdict 차이를
기록한다.

### Phase 5 — 정적·동적 검증

정적 검증:

- 모든 policy call과 wrapper 검색을 최종 `HEAD`에서 재실행한다.
- 변경한 함수의 모든 caller를 다시 확인한다.
- source 주석과 enum 이름이 실제 terminal consumer 의미를 설명하는지 확인한다.
- physical image 경로가 `heap_record_replace_oos_oids()`에 도달하지 않는지 확인한다.

동적 검증의 최소 시나리오:

| 영역 | 필수 시나리오 |
|---|---|
| raw logical consumer | OOS-backed `VARCHAR`/`VARBIT`, multi-chunk 값, 값·길이 일치 |
| copyarea/network | 작은 버퍼와 `S_DOESNT_FIT`, 재시도 후 값 일치 |
| attribute Resolve | 요청한 OOS 속성만 읽고 record-level Expand를 하지 않음 |
| header/fixed/no-body | CHN, fixed/header, existence 경로에서 Expand를 하지 않음 |
| update/delete | old/new OOS 값, inline↔OOS 경계 전환, rollback 후 값 일치 |
| recovery/vacuum | restart/rollback/vacuum 후 값과 OOS chain 유효성, physical stub 보존 |
| CDC/flashback | insert/update/delete, old/new image, multi-chunk, schema/error 분기 |
| replication | source/replica 논리값 일치. 물리 OID가 같을 것이라고 가정하지 않음 |
| utilities | 조사에서 포함된 unload/load/compact/partition 경로별 논리값 일치 |
| 실행 모드 | 영향을 받는 경로에 대해 CS와 SA 모두 확인 |

Expand 여부를 값 비교만으로 판정할 수 없는 경로는 debugger breakpoint, trace 또는 좁은 임시 계측으로
`heap_record_replace_oos_oids()`와 `oos_read()` 도달 여부를 확인한다. 임시 계측은 최종 변경에 남기지 않는다.

로컬 worktree 빌드는 개인 편의 도구인 다음 명령을 사용한다.

```bash
just build
just build-test
```

이 두 명령은 CUBRID 조직의 공식 workflow가 아니다. JIRA, PR 본문, reviewer 안내 또는 공개 검증 절차에
복사하지 않는다. 외부 문서에는 수행한 표준 build/test 종류와 결과만 적는다.

Gate 5:

- `VERIFICATION.md`에 검증한 최종 commit과 정확한 명령·결과가 있다.
- 각 `BUG`/`OVER_EXPAND` finding에 적어도 하나의 정적 또는 동적 회귀 근거가 연결되어 있다.
- P0/P1 경로의 미검증 항목이 0이다.
- 실패하거나 실행할 수 없는 테스트는 숨기지 않고 원인, 대체 근거, 잔여 위험을 기록한다.

### Phase 6 — 최종 closure

1. 최종 `HEAD`에서 Phase 1과 Phase 2 검색을 모두 재실행한다.
2. 최초/최종 policy 개수와 inventory delta를 기록한다.
3. forward/reverse closure를 다시 계산한다.
4. 모든 finding이 `fixed`, `not-a-bug`, `follow-up` 중 하나인지 확인한다.
5. follow-up마다 별도 이슈에 옮길 수 있는 독립적인 문제 설명과 acceptance criteria를 준비한다.
6. JIRA/PR에 올릴 요약은 준비하되, 외부 시스템 갱신은 별도 사용자 지시가 있을 때만 수행한다.

최종 완료 조건:

- [ ] `F`, `R`, `X`의 모든 행에 source evidence가 있다.
- [ ] forward-only unexplained = 0
- [ ] reverse-only unexplained = 0
- [ ] search pending = 0
- [ ] inventory `TBD` = 0
- [ ] 연속 두 번의 no-new-path closure pass가 있다.
- [ ] 모든 logical raw consumer가 Expand로 연결된다.
- [ ] 모든 attribute consumer가 Resolve 또는 동등한 OOS-aware 경로로 연결된다.
- [ ] 모든 physical image consumer가 stored form을 유지한다.
- [ ] 모든 OOS-insensitive/no-body 경로가 불필요한 Expand를 하지 않는다.
- [ ] CDC와 flashback을 각각 독립적으로 확인했다.
- [ ] replication과 조사에서 발견된 utility 경로를 확인했다.
- [ ] 단순 오분류는 수정·검증되었다.
- [ ] 큰 설계 변경은 구체적인 follow-up으로 연결되었다.
- [ ] 최종 build/test 결과와 미검증 위험이 문서화되었다.

## 7. 판단 절차

각 경로는 아래 순서로 판정한다.

```text
heap instance RECDES인가?
├─ 아니오 → EXCLUDED, provenance와 제외 근거 기록
└─ 예
   ├─ physical image를 보존/복원/삭제하는가?
   │  └─ 예 → PRESERVE_PHYSICAL, stored form 유지
   ├─ record body를 사용하지 않는가?
   │  └─ 예 → NO_BODY, stored form 유지
   ├─ attribute layer가 값을 읽는가?
   │  └─ 예 → RESOLVE, 필요한 속성만 OOS-aware read
   ├─ header/fixed/CHN만 읽는가?
   │  └─ 예 → STORED_SAFE, stored form 유지
   ├─ raw full record 또는 variable area를 논리값으로 읽는가?
   │  └─ 예 → EXPAND
   └─ wrapper가 여러 소비자를 대신하는가?
      └─ 예 → PROPAGATE, caller 의미를 parameter로 전달
```

여러 branch가 섞인 함수는 함수 전체에 하나의 판정을 붙이지 말고 branch/terminal consumer별로 행을 나눈다.

## 8. 권장 조사 순서

의존 관계를 고려해 다음 순서로 진행한다.

1. policy enum과 7개 공개 API
2. heap 내부 wrapper와 scan helper
3. locator, copyarea, client/network
4. query executor, schema/object, utility의 raw consumer
5. WAL, MVCC, vacuum, rollback/recovery
6. CDC와 flashback
7. replication/HA
8. non-heap `RECDES` 제외 집합
9. cross-closure와 finding freeze
10. 수정, 테스트, 최종 closure

앞 단계에서 찾은 alias와 callback 이름은 뒤 단계 검색 seed에 누적한다. subsystem별 표를 따로 만들더라도
최종 진실의 원장은 하나의 `AUDIT-INVENTORY.tsv`다.

## 9. 금지되는 지름길

- policy 상수 25/59개를 검토한 것만으로 전수 조사를 완료했다고 판단하지 않는다.
- 과거 문서의 caller 표, line number, 당시 구현 상태를 현재 증거로 사용하지 않는다.
- raw `data` 접근이라는 이유만으로 무조건 Expand하지 않는다. byte range와 의미를 확인한다.
- attribute layer를 거친다는 이름만 믿지 말고 실제 OOS-aware read까지 추적한다.
- undo/redo나 MVCC old image를 논리적으로 보기 좋게 만들기 위해 Expand하지 않는다.
- `COPY`/`PEEK`를 OOS policy의 대용으로 사용하지 않는다.
- grep hit가 없다는 사실을 부재 증명으로 사용하지 않는다.
- inventory freeze 전에 source를 고쳐 최초 상태와 누락 증거를 없애지 않는다.
- unrelated dirty file, submodule 또는 개인 설정을 정리하거나 되돌리지 않는다.
- 실패한 테스트와 확인하지 못한 branch를 “영향 없음”으로 바꾸어 적지 않는다.

## 10. 중단·재개 프로토콜

각 작업 세션 종료 전에 `SEARCH-LEDGER.md` 맨 위에 다음 블록을 갱신한다.

```text
current source anchor:
current phase:
last completed inventory id:
new symbols not yet expanded:
pending candidate count:
open findings:
blocker:
next exact command:
```

재개하는 에이전트는 이 블록, `git status --short`, `git rev-parse HEAD`를 먼저 비교한다. source anchor가
바뀌었으면 기존 행을 삭제하지 말고 stale 여부와 재검증 결과를 기록한다.

에이전트가 완료를 선언할 수 있는 시점은 코드 변경이 끝난 때가 아니라, Phase 6의 closure와 verification
조건이 모두 충족된 때다.
