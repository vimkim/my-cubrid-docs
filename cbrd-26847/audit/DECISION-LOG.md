# DECISION LOG — CBRD-26847

- 세션 source commit: `681323eb2`
- 목적: 대화형 audit에서 검토한 각 변경의 근거, 안전성 논증, 잔여 위험, 사용자 결정을 기록한다.
- 공통 판정 규칙: 소비자가 materialized logical `RECDES` 바이트를 직접 사용할 때만 whole-record OOS Expand가
  필요하다. stored-form, attribute layer, header/fixed/CHN, no-body 소비자는
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 사용한다.

## D-001 — `compactdb.c::process_value` existence probe

- source line: `src/executables/compactdb.c:567`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 코드를 유지하고 되돌리지 않는다.
- terminal consumer: caller가 `recdes = NULL`을 전달하므로 `RECDES`는 반환되지 않으며 `SCAN_CODE`만 소비한다.
- 규범 근거: OOS ADR-0003은 existence-only 접근을 non-Expand 소비자로 분류한다.
- source 근거:
  - `src/executables/compactdb.c:566`에서 `recdes` 인자로 `NULL`을 전달한다.
  - `src/storage/heap_file.c:26539-26543`은 `recdes_p == NULL`이면 log에서 복원한 version도 Expand하지 않는다.
  - `src/storage/heap_file.c:26562-26565`는 `recdes_p == NULL`이면 record data를 fetch하지 않는다.
- 안전성 논증: 이 API 경계에는 record body 자체가 없으므로 OOS stub가 downstream consumer로 전달될 수 없다.
  현재 구현에서 동작은 동일하고 consumption contract 표기만 바로잡는다.
- 잔여 위험: 향후 non-NULL `RECDES`를 전달하고 그 바이트를 소비하도록 바뀌면 policy를 다시 audit해야 한다.
- 현재까지의 검증: 정확한 semantic replacement를 확인했고 `681323eb2`에서 `debug_gcc` build/install이 통과했다.
  전용 runtime 검증은 아직 수행하지 않았다.
- 권고: 위 정확한 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-002 — `compactdb_sr.c::process_value` existence/class probe

- source line: `src/storage/compactdb_sr.c:111`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 코드를 유지하고 되돌리지 않는다.
- terminal consumer: caller가 `recdes = NULL`을 전달한다. 이후에는 `SCAN_CODE`와 별도 out-parameter인
  `ref_class_oid`만 소비하며 record body는 소비하지 않는다.
- 규범 근거: OOS ADR-0003은 existence/header/fixed metadata-only 접근을 non-Expand 소비자로 분류한다.
- source 근거:
  - `src/storage/compactdb_sr.c:110`에서 `recdes` 인자로 `NULL`을 전달한다.
  - `src/storage/compactdb_sr.c:114-126`은 `SCAN_CODE`와 `ref_class_oid`만 검사한다.
  - `src/storage/heap_file.c:26539-26543`, `26562-26565`의 NULL guard 때문에 record fetch/Expand가 실행되지 않는다.
- 안전성 논증: `ref_class_oid`는 별도 API metadata이며 raw record body가 아니다. 반환되는 `RECDES`가 없으므로
  OOS stub 노출 가능성도 없다. 현재 구현에서 동작은 동일하고 consumption contract 표기만 바로잡는다.
- 잔여 위험: 향후 non-NULL `RECDES`를 전달하고 그 바이트를 소비하도록 바뀌면 policy를 다시 audit해야 한다.
- 현재까지의 검증: 정확한 semantic replacement를 확인했고 `681323eb2`에서 `debug_gcc` build/install이 통과했다.
  전용 runtime 검증은 아직 수행하지 않았다.
- 권고: 위 정확한 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-003 — `server_class_installer::locate_class_for_all_users`

- source line: `src/loaddb/load_server_loader.cpp:248`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 코드를 유지하고 되돌리지 않는다.
- terminal consumer: 반환된 `recdes`는 `heap_attrinfo_read_dbvalues`로만 읽히며, 이후 코드는 변환된
  `DB_VALUE`에서 `db_user.name`을 소비한다. raw record 전송·재삽입·바이트 비교·`OR_BUF` parsing은 없다.
- 규범 근거: OOS ADR-0003은 attribute-layer consumer를 non-Expand 소비자로 분류한다.
- source 근거:
  - `src/loaddb/load_server_loader.cpp:261`이 record body의 유일한 직접 후속 소비다.
  - `src/storage/heap_file.c:11004`에서 OOS-aware attribute read 경로로 진입한다.
  - `src/storage/heap_file.c:10536-10539`에서 OOS-marked variable attribute를 감지해 Resolve한다.
  - `src/storage/heap_file.c:10762-10775`는 요청 OOS 속성이 여러 개면 grouped Resolve를 사용한다.
- 안전성 논증: fetch 결과에 OOS inline stub가 남아 있어도 terminal consumer인 attribute layer가 각 요청
  속성을 논리 `DB_VALUE`로 Resolve한다. raw `RECDES`는 attribute layer 밖으로 나가지 않는다.
- 잔여 위험:
  - `heap_attrinfo_start(..., -1, ...)`이므로 현재는 이름만이 아니라 모든 요청 속성을 읽을 수 있으나,
    모두 같은 OOS-aware attribute 경로를 사용하므로 안전성 결론은 변하지 않는다.
  - 향후 raw `RECDES` parsing·전송·재삽입 consumer가 추가되면 policy를 다시 audit해야 한다.
- 현재까지의 검증: exact semantic replacement와 terminal consumer chain을 정적으로 확인했고,
  `681323eb2`에서 `debug_gcc` build/install이 통과했다. 이 경로의 전용 runtime test는 아직 없다.
- 권고: 위 정확한 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-004 — `xserial_get_current_value_internal`

- source line: `src/query/serial.c:234`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 코드를 유지하고 되돌리지 않는다.
- terminal consumer: `SERIAL_ATTR_CURRENT_VAL_INDEX`에 해당하는 속성 하나를
  `heap_attrinfo_read_dbvalues`로 읽어 `DB_VALUE` 결과로 반환한다. raw record 소비는 없다.
- 규범 근거: OOS ADR-0003은 attribute-layer consumer를 non-Expand 소비자로 분류한다.
- source 근거:
  - `src/query/serial.c:250-255`가 current-value 속성 하나만 attr info에 등록한다.
  - `src/query/serial.c:263`이 `recdesc` 본문의 유일한 후속 소비다.
  - `src/query/serial.c:269-271`은 변환된 `DB_VALUE`를 결과로 전달한다.
  - OOS Resolve 근거는 D-003에 기록한 `heap_attrinfo_read_dbvalues` 공통 경로와 같다.
- 안전성 논증: raw `RECDES`는 attribute layer 밖으로 나가지 않는다. 선택 속성이 OOS-backed여도 attribute
  layer가 논리 `DB_VALUE`로 Resolve한다. 현재 serial schema/type이 OOS 대상인지에 의존하지 않는 판정이다.
- 동작 영향: 기존 whole-record 선제 Expand를 제거하고 요청 속성 하나만 Resolve한다. 논리 결과는 같아야 한다.
- 잔여 위험: 이 함수의 전용 OOS serial runtime test는 아직 없다. 향후 raw `recdesc` consumer가 추가되면
  policy를 다시 audit해야 한다.
- 현재까지의 검증: exact semantic replacement와 terminal consumer chain을 정적으로 확인했고,
  `681323eb2`에서 `debug_gcc` build/install이 통과했다.
- 권고: 위 정확한 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-005 — `serial_update_cur_val_of_serial`

- source line: `src/query/serial.c:512`
- 정확한 결정:
  - `HEAP_RECDES_CONSUME_RAW_BYTES`를 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 policy를
    유지하고 되돌리지 않는다.
  - 현재의 “record is consumed only through the attribute layer” 주석은 header/type metadata 직접 접근을
    누락하므로 주석 audit 단계에서 바로잡는다.
- terminal consumer:
  - `heap_attrinfo_read_dbvalues`가 old record의 모든 속성을 논리 `DB_VALUE`로 읽는다.
  - `current_val`을 교체한 뒤 `heap_attrinfo_transform_to_disk`가 새 record를 직렬화한다.
  - old `recdesc`에서는 representation ID, CHN, record type 같은 metadata도 직접 읽는다.
- 규범 근거: OOS ADR-0003은 attribute layer 및 header/fixed metadata consumer를 non-Expand로 분류한다.
- source 근거:
  - `src/query/serial.c:528-534`에서 모든 속성을 등록하고 OOS-aware attribute layer로 읽는다.
  - `src/query/serial.c:556`에서 `current_val`의 논리 값만 교체한다.
  - `src/query/serial.c:563`, `957`에서 attr info를 새 disk record로 직렬화한다.
  - `src/storage/heap_file.c:13085`, `11962-12023`에서 미초기화 속성도 `heap_attrvalue_read`로 읽는다.
  - `src/query/serial.c:971`의 WAL redo 대상은 old record가 아니라 새로 직렬화한 `new_recdesc`다.
- 안전성 논증: old record의 variable body는 OOS-aware attribute layer를 통해 논리 값으로 Resolve된 뒤
  새 record로 직렬화된다. 직접 읽는 부분은 OOS stub와 무관한 header/type metadata뿐이다.
- 동작 영향: 불필요한 whole-record 선제 Expand를 제거한다. 새 record의 논리 속성 값은 동일해야 한다.
- 잔여 위험: OOS가 포함된 `_db_serial` 갱신 전용 runtime test는 아직 없다. 향후 raw variable-body
  consumer가 추가되면 policy를 다시 audit해야 한다.
- 현재까지의 검증: exact semantic replacement와 read/transform/WAL consumer chain을 정적으로 확인했고,
  `681323eb2`에서 `debug_gcc` build/install이 통과했다.
- 권고: 위 policy 변경은 유지하고, 부정확한 주석은 별도 승인 후 수정한다.
- 사용자 결정: **승인** (2026-07-31)

## D-006 — `xserial_get_next_value_internal`

- source line: `src/query/serial.c:650`, attribute-read block은 변경 전 `672-674`
- 정확한 결정:
  - `HEAP_RECDES_CONSUME_RAW_BYTES`를 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 policy를 유지한다.
  - `attr_info_p = &attr_info`를 `heap_attrinfo_read_dbvalues` 호출 전에 실행한다.
  - `heap_attrinfo_read_dbvalues`가 `NO_ERROR`가 아니면 즉시 `goto exit_on_error`로 중단한다.
  - 현재의 “record is consumed only through the attribute layer” 주석은 header/type metadata 직접 접근을
    누락하므로 주석 audit 단계에서 바로잡는다.
- 발견한 current-patch 위험: 기존 코드는 `heap_attrinfo_read_dbvalues`의 반환값을 검사하지 않았다.
  `DONT_CONSUME_RAW_BYTES`로 바꾸면 OOS I/O가 fetch의 checked Expand 단계에서 이 unchecked attribute
  Resolve 단계로 이동하므로, 실패 후 유효하지 않은 `DB_VALUE`를 serial 계산/update에 사용할 수 있었다.
- terminal consumer:
  - 모든 serial 속성을 attribute layer로 읽어 `cached_num`, `current_val`, `increment_val`, 범위/상태 값을
    계산한다.
  - 변경 값을 attr info에 설정하고 D-005와 같은 `serial_update_serial_object` 경로로 새 record를
    직렬화하여 WAL/page update를 수행한다.
  - old `recdesc`의 직접 접근은 representation ID, CHN, record type metadata뿐이다.
- 규범 근거: OOS ADR-0003은 attribute layer 및 header/fixed metadata consumer를 non-Expand로 분류한다.
  단, Resolve 실패는 반드시 terminal consumer 전에 전파되어야 한다.
- source 근거:
  - `src/query/serial.c:666-672`가 모든 속성을 등록하고 attribute layer로 읽는다.
  - `src/query/serial.c:676-845`가 변환된 `DB_VALUE`를 계산 및 결과에 사용한다.
  - `src/query/serial.c:818-819`가 D-005와 같은 새-record 직렬화 경로를 호출한다.
  - `_db_serial`의 정상 record는 작지만 `src/object/schema_system_catalog_install.cpp:987-1003`에
    variable `string` 속성이 있으므로 “OOS가 구조적으로 불가능하다”는 전제에는 의존하지 않는다.
- 안전성 논증:
  - stored-form OOS 값은 attribute layer가 논리 `DB_VALUE`로 Resolve한다.
  - Resolve/recache/corruption 오류는 계산 전에 즉시 중단한다.
  - `attr_info_p`를 먼저 설정하므로 기존 `exit_on_error`가 `heap_attrinfo_end`를 호출한다.
  - 새 record/WAL은 성공적으로 변환된 attr info에서만 생성된다.
- 잔여 위험: OOS-backed `_db_serial`과 강제 OOS read 실패를 검증하는 전용 runtime test는 아직 없다.
- 현재까지의 검증: 기존 policy replacement와 consumer chain을 정적으로 확인했다. 승인된 error-check
  보완 적용 후 `debug_gcc` build/install이 통과했다.
- 권고: 위 네 가지 조치를 함께 적용한다. error check 없이 policy만 유지하는 상태는 승인하지 않는다.
- 사용자 결정: **승인** (2026-07-31)

## D-007 — `sp_get_code_attr`

- source line: `src/sp/sp_code.cpp:91`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 policy를 유지하고 되돌리지 않는다.
- terminal consumer:
  - `attr_name`을 하나의 attr ID로 변환한다.
  - 해당 속성 하나만 `heap_attrinfo_read_dbvalues`로 논리 `DB_VALUE`로 읽는다.
  - 결과를 `db_value_clone`으로 복제한 뒤 attr info와 scan cache를 종료한다.
- 규범 근거: OOS ADR-0003은 attribute-layer consumer를 non-Expand로 분류한다.
- source 근거:
  - `src/sp/sp_code.cpp:107-120`에서 요청 속성 하나를 선택·등록한다.
  - `src/sp/sp_code.cpp:128-132`에서 OOS-aware attribute read와 오류 검사를 수행한다.
  - `src/sp/sp_code.cpp:134-140`에서 논리 값을 clone한 뒤 자원을 정리한다.
  - `src/object/schema_system_catalog_install.cpp:961-963`의 `scode`/`ocode`는 대용량 OOS 대표 속성이다.
- 안전성 논증: raw `RECDES`는 attribute layer 밖으로 나가지 않는다. 요청 속성이 OOS-backed이면 그
  속성만 Resolve하며, Resolve 오류는 결과 소비 전에 전파된다.
- 동작 영향: 논리 결과는 유지하면서 요청하지 않은 대용량 code 속성의 whole-record Expand를 피한다.
- 잔여 위험: OOS-backed `scode`/`ocode`를 이 함수로 직접 읽는 전용 runtime test는 아직 없다.
- 현재까지의 검증: exact semantic replacement와 terminal consumer/error/lifetime chain을 정적으로 확인했고,
  현재 source가 `debug_gcc` build/install을 통과했다.
- 권고: policy 변경을 유지한다.
- 사용자 결정:
  - policy 변경 유지: **승인** (2026-07-31)
  - “the single code attribute”를 “the requested attribute”로 고치는 주석 수정: **미승인**
    (`1만`이라는 사용자 지시에 따라 현재 주석을 변경하지 않음)

## D-008 — `heap_scanrange_to_following` positioning fetch

- source line: `src/storage/heap_file.c:8428`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 policy를 유지하고 되돌리지 않는다.
- terminal consumer: fetch 결과의 `SCAN_CODE`만 검사한다. `recdes`는 함수-local이고 body를 읽지 않으며,
  이후 `spage_next_record`가 같은 descriptor를 덮어쓴다.
- 규범 근거: OOS ADR-0003은 no-body/positioning consumer를 non-Expand로 분류한다.
- source 근거:
  - `src/storage/heap_file.c:8399`의 `recdes`는 local 변수다.
  - `src/storage/heap_file.c:8429-8445`는 fetch 결과 code와 OID 이동만 처리한다.
  - `src/storage/heap_file.c:8474`가 local descriptor를 새 record로 덮어쓴다.
  - fallback `heap_next`도 `src/storage/heap_file.c:8436`에서 DONT policy를 사용한다.
  - repository의 유일한 caller `src/query/scan_manager.c:5053`은 현재 `start_oid = NULL`을 전달하므로
    변경 branch는 current source에서 실행되지 않는다.
- 안전성 논증: materialized logical body가 함수 안팎 어디에서도 소비되지 않으므로 OOS stub가 terminal
  consumer에 노출될 수 없다. 현재 실행 경로에는 영향이 없고 함수-local contract를 바로잡는다.
- 잔여 위험: 향후 함수 내부에서 fetched body를 직접 파싱하도록 바뀌면 policy를 다시 audit해야 한다.
  현재 dead branch라 전용 runtime 검증은 없으며 정적 consumer proof가 주 증거다.
- 현재까지의 검증: exact semantic replacement, complete repository caller search, local consumer chain을
  정적으로 확인했고 현재 source가 `debug_gcc` build/install을 통과했다.
- 권고: 위 정확한 policy 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-009 — `heap_scanrange_to_prior` positioning fetch

- source line: `src/storage/heap_file.c:8540`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 policy를 유지하고 되돌리지 않는다.
- terminal consumer: fetch 결과의 `SCAN_CODE`만 검사한다. `recdes`는 함수-local이고 body를 읽지 않으며,
  이후 `spage_previous_record`가 같은 descriptor를 덮어쓴다.
- 규범 근거: OOS ADR-0003은 no-body/positioning consumer를 non-Expand로 분류한다.
- source 근거:
  - `src/storage/heap_file.c:8512`의 `recdes`는 local 변수다.
  - `src/storage/heap_file.c:8541-8554`는 fetch 결과 code와 OID 이동만 처리한다.
  - `src/storage/heap_file.c:8585`가 local descriptor를 새 record로 덮어쓴다.
  - fallback `heap_prev`도 `src/storage/heap_file.c:8548`에서 DONT policy를 사용한다.
  - repository의 유일한 caller `src/query/scan_manager.c:5057`은 현재 `last_oid = NULL`을 전달하므로
    변경 branch는 current source에서 실행되지 않는다.
- 안전성 논증: materialized logical body가 함수 안팎 어디에서도 소비되지 않으므로 OOS stub가 terminal
  consumer에 노출될 수 없다. 현재 실행 경로에는 영향이 없고 함수-local contract를 바로잡는다.
- 잔여 위험: 향후 함수 내부에서 fetched body를 직접 파싱하도록 바뀌면 policy를 다시 audit해야 한다.
  현재 dead branch라 전용 runtime 검증은 없으며 정적 consumer proof가 주 증거다.
- 현재까지의 검증: exact semantic replacement, complete repository caller search, local consumer chain을
  정적으로 확인했고 현재 source가 `debug_gcc` build/install을 통과했다.
- 권고: 위 정확한 policy 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-010 — `heap_scanrange_next` first-record fetch

- source line: `src/storage/heap_file.c:8639`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 policy를 유지하고 되돌리지 않는다.
- terminal consumer:
  - repository의 유일한 caller는 `scan_next_heap_scan`이다.
  - predicate 속성은 `eval_data_filter`가 `heap_attrinfo_read_dbvalues`로 읽는다.
  - qualified row의 나머지 속성도 `heap_attrinfo_read_dbvalues`로 읽는다.
  - raw record 전송·재삽입·바이트 비교·`OR_BUF` parsing은 없다.
- 규범 근거: OOS ADR-0003은 attribute-layer consumer를 non-Expand로 분류한다.
- source 근거:
  - `src/query/scan_manager.c:5916`이 유일한 caller다.
  - `src/query/scan_manager.c:5971` → `src/query/query_evaluator.c:2763-2766`이 predicate 속성을
    OOS-aware 방식으로 읽고 오류를 전파한다.
  - `src/query/scan_manager.c:6171-6174`가 rest attributes를 읽고 오류를 전파한다.
  - lock 후 refetch도 `src/query/scan_manager.c:6041-6043`에서 DONT policy를 사용한다.
  - 같은 함수의 subsequent-record `heap_next`도 `src/storage/heap_file.c:8665`에서 DONT policy다.
- 안전성 논증: returned stored-form record는 모든 terminal value consumer 전에 attribute layer를 거친다.
  OOS Resolve 실패도 predicate/result 소비 전에 전파된다.
- 동작 영향: grouped scan block의 첫 record만 선제 whole-record Expand하던 비대칭을 제거하고 subsequent
  record와 같은 contract로 맞춘다. 논리 query 결과는 같아야 하며 첫 record의 불필요한 OOS I/O와
  Expand로 인한 `S_DOESNT_FIT` 가능성을 제거한다.
- 잔여 위험: grouped scan block 첫 record에서 Expand 미호출을 직접 관찰하는 runtime instrumentation은
  아직 없다. 향후 raw-body terminal consumer가 추가되면 policy를 다시 audit해야 한다.
- 현재까지의 검증: exact semantic replacement, complete caller search, predicate/rest/lock consumer chain을
  정적으로 확인했고 현재 source가 `debug_gcc` build/install을 통과했다.
- 권고: 위 정확한 policy 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-011 — `locator_update_force` MVCC old-record fetch

- source line: `src/transaction/locator_sr.c:5800`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 policy를 유지하고 되돌리지 않는다.
- terminal consumer:
  - MVCC header를 직접 읽는다.
  - `locator_update_index`가 old index/filter 속성을 attribute layer 및 OOS-aware key generator로 읽는다.
  - old record 전송·재삽입·byte comparison·OOS-blind parsing은 없다.
- 규범 근거: OOS ADR-0003은 attribute layer 및 header metadata consumer를 non-Expand로 분류한다.
- source 근거:
  - `src/transaction/locator_sr.c:5858`, `5872`가 MVCC header만 직접 읽는다.
  - `src/transaction/locator_sr.c:6044`가 old record를 `locator_update_index`에 전달한다.
  - `src/transaction/locator_sr.c:8522-8526`이 old index 속성을 OOS-aware 방식으로 읽고 오류를 전파한다.
  - filtered index는 `src/transaction/locator_sr.c:8588` → `8340-8344`에서 attribute layer를 사용한다.
  - multi-column key는 `src/storage/heap_file.c:14398-14408`, `14051-14076`에서 OOS 길이와 Resolve
    오류를 처리한다.
  - sibling locking fetch는 이미 `src/transaction/locator_sr.c:5793`에서 DONT policy다.
- 안전성 논증: 직접 소비하는 부분은 OOS stub와 무관한 MVCC header뿐이며, variable/index body는 모두
  OOS-aware consumer를 거친다. Resolve/key 오류는 heap update 전에 전파된다. old record는 WAL이나 새
  heap image로 raw 복사되지 않는다.
- 동작 영향: locking/non-locking 경로의 contract를 맞추고, fixed COPY area에 whole logical record를
  Expand해 `S_DOESNT_FIT`이 발생할 수 있는 경로를 제거한다.
- 잔여 위험: OOS-backed indexed attribute, filtered index, multi-column index를 조합한 update runtime
  검증은 아직 없다. 향후 OOS-blind raw consumer가 추가되면 policy를 다시 audit해야 한다.
- 현재까지의 검증: exact semantic replacement와 header/filter/index/key/WAL consumer chain을 정적으로
  확인했고 현재 source가 `debug_gcc` build/install을 통과했다.
- 권고: 위 정확한 policy 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-012 — `locator_update_force` non-MVCC old-record fetch

- source line: `src/transaction/locator_sr.c:5944`
- 정확한 결정: `HEAP_RECDES_CONSUME_RAW_BYTES`를
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 현재 policy를 유지하고 되돌리지 않는다.
- terminal consumer: MVCC-disabled class에서 old record body의 유일한 consumer는
  `locator_update_index`의 OOS-aware index/filter/key 경로다. old record를 WAL·새 heap image로 raw
  복사하거나 OOS-blind하게 파싱하지 않는다.
- 규범 근거: OOS ADR-0003은 attribute-layer consumer를 non-Expand로 분류한다.
- source 근거:
  - `src/transaction/locator_sr.c:5947`에서 성공한 copy를 `oldrecdes`로 지정한다.
  - `src/transaction/locator_sr.c:6044`가 body의 유일한 후속 consumer다.
  - index/filter/key의 OOS-aware 근거는 D-011과 동일하다.
  - `src/transaction/locator_sr.c:6101-6102`의 실제 heap update는 new `recdes`로 생성한 context를 사용한다.
- 안전성 논증: old variable/index body는 OOS-aware consumer에서 Resolve되고 오류는 heap update 전에
  전파된다. 이 branch에는 old record의 direct MVCC-header consumer도 없다.
- 동작 영향: fixed COPY area의 whole-record Expand와 그에 따른 `S_DOESNT_FIT` 가능성을 제거하고,
  필요한 index/filter 속성만 Resolve한다.
- 주석 판정: `src/transaction/locator_sr.c:5941`의 “MVCC header and attribute layer”는 이 non-MVCC
  branch에는 부정확하다. 이번 승인은 policy만 대상으로 하며 주석은 변경하지 않는다.
- 잔여 위험: MVCC-disabled class의 OOS-backed indexed attribute update runtime test는 아직 없다.
  향후 raw-body consumer가 추가되면 policy를 다시 audit해야 한다.
- 현재까지의 검증: exact semantic replacement와 index/filter/key/update consumer chain을 정적으로
  확인했고 현재 source가 `debug_gcc` build/install을 통과했다.
- 권고: 위 정확한 policy 변경을 유지한다.
- 사용자 결정: **승인** (2026-07-31)

## D-013 — `locator_delete_lob_force` old-record fetch

- source line: policy는 `src/transaction/locator_sr.c:6584`, 변경 전 error/cleanup block은 `6585-6588`,
  `6601-6604`
- 정확한 결정:
  - `HEAP_RECDES_CONSUME_RAW_BYTES`를 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 바꾼 policy를 유지한다.
  - fetch 실패 시 `er_errid()`를 `error_code`에 저장하고, 오류 코드가 없으면 `ER_FAILED`를 저장한다.
  - cleanup의 `heap_scancache_end` 반환값도 보존한다. 기존 작업 오류가 있으면 그 오류를 우선하고,
    기존 오류가 없을 때만 scan-cache cleanup 오류를 최종 `error_code`로 사용한다.
  - 현재 주석은 변경하지 않는다.
- terminal consumer: fetched record body는 `heap_attrinfo_delete_lob`만 소비한다. 이 함수는 BLOB/CLOB 속성을
  `heap_attrvalue_read`로 Resolve하여 `DB_ELO` locator를 얻고 `db_elo_delete`를 호출한다.
- 규범 근거: OOS ADR-0003은 attribute-layer consumer를 non-Expand로 분류한다. Resolve 및 LOB delete
  오류는 반드시 caller로 전파되어야 한다.
- 발견한 current-patch 위험:
  - fetch의 `SCAN_CODE` 실패가 `error_code`에 반영되지 않았다.
  - `heap_attrinfo_delete_lob`의 OOS/LOB 오류를 cleanup의 `error_code = heap_scancache_end(...)`가
    덮어썼다.
  - `heap_scancache_end`는 current source에서 항상 `NO_ERROR`를 반환하므로 실패가 성공으로 바뀔 수 있었다.
- source 근거:
  - `src/transaction/locator_sr.c:6592`가 fetched body의 유일한 terminal consumer다.
  - `src/storage/heap_file.c:11123-11127`에서 OOS-aware attribute read와 오류 전파를 수행한다.
  - `src/storage/heap_file.c:11137`에서 external LOB를 삭제한다.
  - `src/storage/heap_file.c:6968-6974`에서 `heap_scancache_end`가 cleanup 후 `NO_ERROR`를 반환한다.
- 안전성 논증:
  - stored-form OOS locator는 attribute layer가 논리 `DB_ELO`로 Resolve한다.
  - fetch, inline-ref parse, OOS read, recache, LOB delete 오류를 보존한다.
  - scan cache cleanup은 항상 수행한다. 앞선 오류를 성공으로 바꾸지 않으면서, 미래에
    `heap_scancache_end`가 실제 오류를 반환하게 되면 그 cleanup 오류도 잃지 않는다.
- 잔여 위험: OOS-backed LOB locator와 강제 OOS/LOB delete 실패를 검증하는 전용 runtime test는 아직 없다.
- 현재까지의 검증: policy/consumer/error-cleanup chain을 정적으로 확인했다. 승인된 오류 보존 보완을
  적용한 뒤 `debug_gcc` 전체 build/install을 통과했다.
- 권고: 위 네 가지 조치를 함께 적용한다. 오류 보존 없이 policy만 유지하는 상태는 승인하지 않는다.
- 사용자 결정:
  - 최초 네 조치: **승인** (2026-07-31)
  - `heap_scancache_end` 반환값을 `(void)`로 버리는 구현은 사용자 지시로 철회
  - 최종 구현은 primary error 우선 + cleanup error fallback 방식으로 반영

## D-014 — `locator_repl_prepare_force` old-record fetch policy

- source line: `src/transaction/locator_sr.c:6959`
- 정확한 결정: 이 줄의 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 그대로 두고,
  `HEAP_RECDES_CONSUME_RAW_BYTES`로 되돌리지 않는다. 바로 위 주석은 이번 결정 범위에서 제외한다.
- terminal consumer: fetched `old_recdes`의 유일한 후속 사용은
  `src/transaction/locator_sr.c:6974`의 `or_chn (old_recdes)`이다.
- 규범 근거: OOS ADR-0003은 header-only consumer를 non-Expand로 분류한다.
- source 근거: `src/object/object_representation.c:352-360`의 `or_chn`은 길이를 확인한 뒤
  레코드 앞부분의 `OR_GET_MVCC_CHN`만 읽는다.
- 안전성 논증: CHN은 OOS 속성 본문과 무관한 레코드 헤더 정보다. 따라서 stored-form RECDES로도
  동일한 CHN을 읽을 수 있고, whole-record Expand는 결과를 바꾸지 않은 채 OOS I/O·메모리 비용과
  `S_DOESNT_FIT` 가능성만 추가한다.
- 잔여 위험: 이 함수에 향후 raw-body consumer가 추가되면 policy를 다시 audit해야 한다.
- 현재까지의 검증: consumer chain을 정적으로 확인했고, 이 policy가 포함된 현재 source는
  `debug_gcc` 전체 build/install을 통과했다.
- 권고: 위 정확한 policy 값을 그대로 둔다.
- 사용자 결정:
  - policy: **승인** (2026-07-31)
  - `src/transaction/locator_sr.c:6956`의
    `/* only the CHN is read from the old record (CBRD-26847) */` 주석을 현재 문구 그대로 둠:
    **승인** (2026-07-31)
- 주석 안전성 근거: 함수 내부에서 fetched `old_recdes`를 읽는 곳은 `or_chn` 한 곳뿐이며,
  호출자 `xlocator_repl_force`도 함수 반환 후 해당 `old_recdes`를 다시 소비하지 않는다. 주석은 실행 동작을
  바꾸지 않고 policy의 header-only 근거를 호출부 가까이에 보존한다.

## D-015 — `locator_mvcc_reeval_scan_filters` visible-version fetch policy

- source line: `src/transaction/locator_sr.c:13846`
- 정확한 결정: 이 줄의 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 그대로 두고,
  `HEAP_RECDES_CONSUME_RAW_BYTES`로 되돌리지 않는다. 바로 위 주석과 scan-cache cleanup 처리는
  이번 결정 범위에서 제외한다.
- terminal consumers:
  - rest attributes는 `heap_attrinfo_read_dbvalues`로 Resolve한다.
  - range/key filters는 `locator_mvcc_reevaluate_filters`에서 각각 `heap_attrinfo_read_dbvalues`로 Resolve한다.
  - data filter는 `eval_data_filter` 내부의 `heap_attrinfo_read_dbvalues`로 Resolve한다.
  - `fetch_val_list`와 predicate 함수는 attribute cache에 적재된 값을 사용한다.
- 규범 근거: OOS ADR-0003은 attribute-layer consumer를 non-Expand로 분류한다.
- 안전성 논증: raw record 전체를 복사·비교·전송하거나 OOS 비인지 파서에 넘기는 경로가 없다.
  attribute read 실패는 `V_ERROR`로 전파된다. 따라서 whole-record Expand는 결과를 바꾸지 않은 채
  OOS I/O·메모리 비용과 `S_DOESNT_FIT` 가능성만 추가한다.
- 별도 발견 사항: `src/transaction/locator_sr.c:13889`의 기존 `heap_scancache_end` 호출은 반환값을
  검사하지 않는다. 이는 policy 한 줄과 별개의 cleanup 결정으로 분리하여 감사한다.
- 잔여 위험: 향후 raw-body consumer가 추가되면 policy를 다시 audit해야 한다. 이 재평가 경로를
  OOS-backed predicate로 직접 검증하는 전용 runtime test는 아직 없다.
- 현재까지의 검증: 전체 consumer/error chain을 정적으로 확인했고, 이 policy가 포함된 현재 source는
  `debug_gcc` 전체 build/install을 통과했다.
- 권고: 위 정확한 policy 값을 그대로 둔다.
- 사용자 결정:
  - policy: **승인** (2026-07-31)
  - `src/transaction/locator_sr.c:13843`의
    `/* record is consumed only through the attribute layer for MVCC reevaluation (CBRD-26847) */` 주석을
    현재 문구 그대로 둠: **승인** (2026-07-31)
- 주석 안전성 근거: rest/range/key/data filter의 record 소비가 모두 OOS-aware attribute reader를
  경유한다. 주석은 실행 동작을 바꾸지 않고 non-Expand policy의 근거를 호출부 가까이에 보존한다.

## D-016 — `locator_mvcc_reeval_scan_filters` scan-cache cleanup result

- source line: 변경 전 `src/transaction/locator_sr.c:13889`
- 정확한 결정: 반환값을 버리던 단일 호출을 다음 검사로 바꾼다.

  ```c
  if (heap_scancache_end (thread_p, &local_scan_cache) != NO_ERROR)
    {
      ev_res = V_ERROR;
    }
  ```

- 오류 모델 근거: 이 함수의 반환형은 error-code `int`가 아니라 `DB_LOGICAL`이므로 cleanup 실패를
  나타낼 수 있는 정확한 반환값은 `V_ERROR`다.
- 안전성 논증:
  - cleanup 호출은 기존과 같이 scan cache가 초기화된 모든 종료 경로에서 수행한다.
  - 현재 `heap_scancache_end`는 항상 `NO_ERROR`를 반환하므로 현재 실행 동작은 바뀌지 않는다.
  - 미래에 오류를 반환하면 `V_TRUE`, `V_FALSE`, `V_UNKNOWN`을 정상 평가 결과처럼 반환하지 않고
    `V_ERROR`로 바꾼다.
  - 앞선 결과가 이미 `V_ERROR`라면 실패 상태를 그대로 유지한다.
  - `(void)` 캐스팅을 추가하지 않고 반환값을 명시적으로 검사한다.
- 잔여 위험: `heap_scancache_end`가 미래에 오류를 반환할 때 error manager에도 해당 오류를 설정한다는
  API 계약이 필요하다. 이 함수는 정수 오류 코드를 직접 반환할 수 없다.
- 검증: 적용 후 `git diff --check`와 `debug_gcc` 전체 build/install을 통과했다.
- 권고: 위 네 줄을 적용한다.
- 사용자 결정: **승인** (2026-07-31)

## D-017 — `lock_dump_resource` visible-version fetch policy

- source line: `src/transaction/lock_manager.c:5701`
- 정확한 결정: 이 줄의 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`를 그대로 두고,
  `HEAP_RECDES_CONSUME_RAW_BYTES`로 되돌리지 않는다. 바로 위 주석과 scan-cache cleanup 처리는
  이번 결정 범위에서 제외한다.
- terminal consumer: fetched `recdes`의 유일한 소비자는 `or_mvcc_get_header`이며, lock dump는
  MVCC insert ID와 delete ID만 출력한다.
- 규범 근거: OOS ADR-0003은 header-only consumer를 non-Expand로 분류한다.
- 안전성 논증: MVCC header는 stored-form record 앞부분에 그대로 있다. OOS 속성 본문을
  복사·비교·전송하거나 직접 파싱하지 않으므로 whole-record Expand는 출력 결과를 바꾸지 않은 채
  OOS I/O·메모리 비용과 `S_DOESNT_FIT` 가능성만 추가한다.
- 별도 발견 사항: `src/transaction/lock_manager.c:5727`의 기존 `heap_scancache_end` 호출은 반환값을
  검사하지 않는다. `lock_dump_resource`는 `void` best-effort 진단 함수이므로 별도 결정으로 감사한다.
- 잔여 위험: 향후 lock dump가 raw record 본문을 출력하게 되면 policy를 다시 audit해야 한다.
- 현재까지의 검증: consumer chain을 정적으로 확인했고, 이 policy가 포함된 현재 source는
  `debug_gcc` 전체 build/install을 통과했다.
- 권고: 위 정확한 policy 값을 그대로 둔다.
- 사용자 결정:
  - policy: **승인** (2026-07-31)
  - `src/transaction/lock_manager.c:5698`의
    `/* only the MVCC header is read from the record (CBRD-26847) */` 주석을 현재 문구 그대로 둠:
    **승인** (2026-07-31)
- 주석 안전성 근거: fetched record의 유일한 소비자가 `or_mvcc_get_header`이고 출력값도 MVCC insert/delete
  ID뿐이다. 주석은 실행 동작을 바꾸지 않고 header-only policy 근거를 호출부 가까이에 보존한다.

## D-018 — `lock_dump_resource` scan-cache cleanup result

- source line: `src/transaction/lock_manager.c:5727`
- 정확한 결정: `heap_scancache_end (thread_p, &scan_cache);`를 현재 형태 그대로 두고 `(void)`를
  추가하지 않는다. 이번 패치에서 임의의 조기 `return`이나 오류 무시용 코드를 추가하지 않는다.
- 근거:
  - `lock_dump_resource`는 `void`인 best-effort 진단 함수라 정수 cleanup 오류를 호출자에게 전달할
    반환 채널이 없다.
  - 조기 `return`은 holder/waiter dump를 잘라 장애 분석 정보를 잃게 할 수 있다.
  - 현재 `heap_scancache_end`는 항상 `NO_ERROR`를 반환하므로 현재 실행에서 손실되는 오류는 없다.
  - `(void)`를 붙이지 않아 반환값을 영구적으로 무시한다는 의도를 고정하지 않는다.
- 미래 조건: `heap_scancache_end`가 실제 오류를 반환하도록 변경될 때 `lock_dump_resource`의 반환형과
  두 호출자를 포함해 오류 전달 경로 전체를 다시 설계한다.
- 권고: 현재 호출을 그대로 둔다.
- 사용자 결정: **승인** (2026-07-31)

## D-019 — `compactdb.c::process_value` existence-probe comment

- source line: `src/executables/compactdb.c:564`
- 정확한 결정: 새로 추가된
  `/* existence probe: recdes is NULL, so no record body is consumed (CBRD-26847) */` 주석을 현재 문구
  그대로 둔다.
- 근거: 바로 아래 `heap_get_visible_version` 호출은 `recdes` 인자로 `NULL`을 전달하고 호출자는
  `SCAN_CODE`만 소비한다. 따라서 existence-only 및 no-body 설명이 실제 코드와 일치한다.
- 안전성: 주석은 실행 동작을 바꾸지 않고 D-001 policy의 근거를 호출부 가까이에 보존한다.
- 미래 조건: `recdes`가 non-NULL로 바뀌면 주석과 policy를 함께 다시 감사한다.
- 권고: 현재 문구 그대로 둔다.
- 사용자 결정: **승인** (2026-07-31)

## D-020 — `compactdb_sr.c::process_value` existence/class-probe comment

- source line: 변경 전 `src/storage/compactdb_sr.c:108`
- 정확한 결정: 새 주석의 `existence probe`를 `existence/class probe`로 바꾸어 다음 한 줄로 만든다.

  ```c
  /* existence/class probe: recdes is NULL, so no record body is consumed (CBRD-26847) */
  ```

- 근거: 바로 아래 호출은 `recdes = NULL`이므로 record body를 반환하지 않지만, 별도 out-parameter인
  `ref_class_oid`도 얻는다. 호출자는 `SCAN_CODE`와 `ref_class_oid`를 모두 소비한다.
- 안전성: 실행 코드가 아닌 주석 한 줄만 바꾸며, D-002에 기록한 실제 소비자와 설명을 일치시킨다.
- 권고: 위 정확한 문구로 교체한다.
- 사용자 결정: **승인** (2026-07-31)

## D-021 — `server_class_installer::locate_class_for_all_users` comment

- source line: `src/loaddb/load_server_loader.cpp:246`
- 정확한 결정: 새로 추가된
  `// record is consumed only through the attribute layer (CBRD-26847)` 주석을 현재 문구 그대로 둔다.
- 근거: visible record fetch 후 `recdes`의 유일한 소비는 `heap_attrinfo_read_dbvalues`이며, 이후 코드는
  attribute cache의 `DB_VALUE`에서 사용자 이름 속성을 찾는다. raw record 복사·비교·전송·직접 파싱은 없다.
- 안전성: 주석은 실행 동작을 바꾸지 않고 D-003 policy의 attribute-layer 근거를 호출부 가까이에 보존한다.
- 미래 조건: raw-body consumer가 추가되면 주석과 policy를 함께 다시 감사한다.
- 권고: 현재 문구 그대로 둔다.
- 사용자 결정: **승인** (2026-07-31)

## D-022 — `xserial_get_current_value_internal` fetch comment

- source line: `src/query/serial.c:231`
- 정확한 결정: 기존 `/* get record into record desc */`를 확장해 추가된
  `/* get record into record desc; consumed only through the attribute layer (CBRD-26847) */` 주석을
  현재 문구 그대로 둔다.
- 근거: 이 함수에서 `recdesc` 본문의 유일한 소비는 `heap_attrinfo_read_dbvalues`이고 요청 속성은
  `current_val` 하나다. 결과도 attribute cache의 논리 `DB_VALUE`에서 얻는다.
- 안전성: 주석만 바뀌며 D-004 policy의 실제 소비 근거를 정확히 설명한다.
- 미래 조건: raw-body 또는 header 직접 소비가 추가되면 주석과 policy를 다시 감사한다.
- 권고: 현재 문구 그대로 둔다.
- 사용자 결정: **승인** (2026-07-31)

## D-023 — `serial_update_cur_val_of_serial` fetch comment

- source line: 변경 전 `src/query/serial.c:509`
- 정확한 결정: 부정확한
  `/* record is consumed only through the attribute layer (CBRD-26847) */`를 다음 한 줄로 교체한다.

  ```c
  /* record body is consumed through the attribute layer; record type is copied separately (CBRD-26847) */
  ```

- 근거: OOS가 존재할 수 있는 record body는 `heap_attrinfo_read_dbvalues`와
  `heap_attrinfo_transform_to_disk` 경로로 소비하지만, `serial_update_serial_object`는 `recdesc->type`을
  직접 읽어 새 record에 복사한다.
- 안전성: 주석 한 줄만 바꾸며, D-005의 실제 body 및 type consumer를 모두 명시한다.
- 권고: 위 정확한 문구로 교체한다.
- 사용자 결정: **승인** (2026-07-31)

## D-024 — `xserial_get_next_value_internal` fetch comment

- source line: 변경 전 `src/query/serial.c:647`
- 정확한 결정: 부정확한
  `/* record is consumed only through the attribute layer (CBRD-26847) */`를 다음 한 줄로 교체한다.

  ```c
  /* record body is consumed through the attribute layer; record type is copied separately (CBRD-26847) */
  ```

- 근거: 이 함수도 `recdesc`를 `serial_update_serial_object`에 전달한다. OOS 가능 본문은 attribute
  read/transform 경로로 소비하지만 record type은 `recdesc->type`에서 직접 복사한다.
- 안전성: 주석 한 줄만 바꾸며, D-006의 실제 body 및 type consumer를 모두 명시한다.
- 권고: 위 정확한 문구로 교체한다.
- 사용자 결정: **승인** (2026-07-31)

## D-025 — `sp_get_code_attr` fetch comment

- source line: 변경 전 `src/sp/sp_code.cpp:88`
- 정확한 결정: 오해의 여지가 있는 `the single code attribute`를 `the requested attribute`로 바꾸어
  다음 한 줄로 만든다.

  ```cpp
  /* get record into record desc; the requested attribute is read through the attribute layer (CBRD-26847) */
  ```

- 근거: 함수는 `scode`/`ocode`에 한정되지 않고 `SP_CODE_ATTR_LIST`에서 `attr_name`으로 지정한 임의
  속성 하나를 attribute layer로 읽는다.
- 안전성: 주석 한 줄만 바꾸며 실제 `attr_name → attr ID → heap_attrinfo_read_dbvalues` 흐름과 일치시킨다.
- 이력: D-007에서는 policy만 승인되어 주석 수정을 보류했고, 이번 별도 질문에서 명시적으로 승인받았다.
- 권고: 위 정확한 문구로 교체한다.
- 사용자 결정: **승인** (2026-07-31)

## D-026 — `heap_first` hardcoded-policy comment

- source lines: 변경 전 `src/storage/heap_file.c:8231-8232`
- 정확한 결정: attribute-layer/no-body만 언급해 fixed-layout 직접 소비자를 누락한 주석을 다음 두 줄로
  교체한다.

  ```c
  /* hardcoded HEAP_RECDES_DONT_CONSUME_RAW_BYTES: callers use the attribute layer, ignore the body, or read
   * fixed-layout records that cannot contain OOS stubs (CBRD-26847 audit) */
  ```

- 근거: dblink 경로는 attribute layer를 사용하고 scanrange/existence 경로는 body를 버리지만,
  `tde_get_keyinfo`와 `boot_get_db_parm`은 내부 fixed-layout record body를 직접 읽는다. 이 내부 record는
  클래스 인스턴스 속성 record가 아니어서 OOS stub를 포함할 수 없다.
- 안전성: 실행 코드가 아닌 주석 두 줄만 바꾸며 `heap_first`의 실제 caller 세 범주를 모두 명시한다.
- 권고: 위 정확한 두 줄로 교체한다.
- 사용자 결정: **승인** (2026-07-31)

## D-027 — `heap_last` hardcoded-policy comment

- source lines: 변경 전 `src/storage/heap_file.c:8261-8262`
- 정확한 결정: 일반적인 “all callers” 설명을 다음 두 줄의 sole-caller 계약으로 교체한다.

  ```c
  /* hardcoded HEAP_RECDES_DONT_CONSUME_RAW_BYTES: the sole caller uses the returned OID for
   * positioning and ignores the record body (CBRD-26847 audit) */
  ```

- 근거: `heap_last`의 유일한 호출자는 `heap_scanrange_to_prior`이며 반환 OID/scan 위치만 사용하고 local
  `recdes` 본문은 읽지 않는다.
- 안전성: 주석 두 줄만 바꾸며 현재 단일 호출자 계약을 정확히 명시한다. 새 호출자가 생기면 “sole caller”가
  policy 재감사 필요성을 드러낸다.
- 권고: 위 정확한 두 줄로 교체한다.
- 사용자 결정: **승인** (2026-07-31)

## D-028 — `heap_scanrange_to_following` positioning-fetch comment

- source line: `src/storage/heap_file.c:8425`
- 정확한 최종 결정: 이해하기 어려운 `positioning fetch` 표현을 제거하고 다음 한 줄로 교체한다.

  ```c
  /* only the fetch result and updated page watcher are used; the local record body is discarded (CBRD-26847) */
  ```

- 근거: local `recdes`는 fetch/next의 출력 버퍼로만 쓰이고, 이후 범위 결정은 `SCAN_CODE`, OID,
  page watcher와 record type을 사용한다. record body 바이트는 읽지 않는다.
- 안전성: 주석은 실행 동작을 바꾸지 않고 D-008 policy의 no-body 근거를 정확히 설명한다.
- 별도 follow-up: non-NULL/non-NULL_OID `start_oid` branch는 `first_oid = *start_oid`로 저장한 뒤
  visible fetch에는 `&scan_range->last_oid`를 전달해 API 설명과 어긋나 보인다. 현재 repo의 유일한 호출자는
  `start_oid = NULL`이라 해당 branch를 타지 않고, 이번 변경이 만든 문제도 아니므로 이 결정에서는
  수정하지 않는다.
- 권고: 위 명시적 문구로 교체한다.
- 사용자 결정:
  - 최초 `positioning fetch` 문구 유지: 승인 후 사용자가 의미가 불명확하다고 재검토 요청
  - 최종 명시적 문구 교체: **승인** (2026-07-31)

## D-029 — `heap_scanrange_to_prior` positioning-fetch comment

- source line: `src/storage/heap_file.c:8537`
- 정확한 최종 결정: 이해하기 어려운 `positioning fetch` 표현을 제거하고 다음 한 줄로 교체한다.

  ```c
  /* only the fetch result and updated page watcher are used; the local record body is discarded (CBRD-26847) */
  ```

- 근거: 이 branch는 `scan_range->last_oid = *last_oid`로 저장한 같은 OID를 fetch한다. local `recdes`는
  fetch/prev 출력 버퍼일 뿐이며 이후 범위 결정은 `SCAN_CODE`, OID, page watcher와 record type을 사용한다.
- 안전성: 주석은 실행 동작을 바꾸지 않고 D-009 policy의 no-body 근거를 정확히 설명한다.
- 권고: 위 명시적 문구로 교체한다.
- 사용자 결정:
  - 최초 `positioning fetch` 문구 유지: 승인 후 사용자가 의미가 불명확하다고 재검토 요청
  - 최종 명시적 문구 교체: **승인** (2026-07-31)

## D-030 — `heap_scanrange_next` first-record comment

- source lines: 변경 전 `src/storage/heap_file.c:8634-8635`
- 정확한 결정: 모호한 `it`을 제거하고 다음 두 줄로 교체한다.

  ```c
  /* Retrieve the first object; the sole caller reads the record body only through the attribute layer,
   * matching the heap_next fetches below (CBRD-26847) */
  ```

- 근거: 유일한 호출자 `scan_manager.c`는 data filter와 rest attributes를 OOS-aware
  `heap_attrinfo_read_dbvalues` 경로로 읽는다. 속성이 필요 없으면 body를 무시한다. fallback `heap_next`도
  동일한 non-Expand policy를 사용한다.
- 안전성: 주석 두 줄만 바꾸며 `it`이 record body임을 명시하고 D-010의 실제 소비 계약과 일치시킨다.
- 권고: 위 정확한 두 줄로 교체한다.
- 사용자 결정: **일괄 승인** (2026-08-03, “yes to all”)

## D-031 — `HEAP_RECDES_CONSUMPTION_POLICY` contract comment

- source lines: 변경 전 `src/storage/heap_file.h:363-364`
- 정확한 결정: 특정 시점의 audit 완료 사실을 적은 주석을 다음 영속적인 사용 계약으로 교체한다.

  ```c
  /* Use CONSUME_RAW_BYTES only when the caller needs materialized logical RECDES bytes outside the OOS-aware
   * attribute layer; otherwise preserve the stored RECDES (CBRD-26847). */
  ```

- 근거: “every call site ... was audited”는 새 호출부가 생기는 즉시 낡을 수 있는 과거 사실이다. enum 옆에는
  caller가 앞으로도 적용할 수 있는 선택 기준이 있어야 한다. materialized logical bytes가 필요한 raw-body
  consumer만 CONSUME을 쓰고, OOS-aware attribute consumer는 stored RECDES를 보존한다.
- 안전성: 주석 두 줄만 바꾸며 실행 동작에는 영향이 없다. ADR-0003의 durable contract와 일치한다.
- 권고: 위 정확한 두 줄로 교체한다.
- 사용자 결정: **일괄 승인** (2026-08-03, “yes to all”)

## D-032 — `locator_update_force` MVCC old-record comment

- source line: `src/transaction/locator_sr.c:5797`
- 정확한 결정: 새로 추가된
  `/* old record is read via the MVCC header and the attribute layer only (CBRD-26847) */` 주석을 현재 문구
  그대로 둔다.
- 근거: MVCC-enabled branch는 `or_mvcc_get_header`로 old-record header를 읽고,
  `locator_update_index`에서 index/filter/key 속성을 OOS-aware attribute layer로 읽는다. 그 밖의 raw-body
  consumer는 없다.
- 안전성: 주석은 실행 동작을 바꾸지 않고 D-011의 header+attribute 소비 계약과 일치한다.
- 권고: 현재 문구 그대로 둔다.
- 사용자 결정: **일괄 승인** (2026-08-03, “yes to all”)

## D-033 — `locator_update_force` non-MVCC old-record comment

- source line: 변경 전 `src/transaction/locator_sr.c:5941`
- 정확한 결정: non-MVCC branch에서 MVCC header를 잘못 언급한 주석을 다음 한 줄로 교체한다.

  ```c
  /* old record is read only through the attribute layer for index maintenance (CBRD-26847) */
  ```

- 근거: 이 branch에서 fetched `oldrecdes`의 유일한 후속 소비는 `locator_update_index`다. 이 함수는 old
  index/filter/key 값을 OOS-aware attribute reader로 얻으며, 이 branch는 `or_mvcc_get_header`를 호출하지 않는다.
- 안전성: 주석 한 줄만 바꾸며 D-012의 실제 non-MVCC 소비 경로와 일치시킨다.
- 권고: 위 정확한 한 줄로 교체한다.
- 사용자 결정: **일괄 승인** (2026-08-03, “yes to all”)

## D-034 — `locator_delete_lob_force` per-attribute Resolve comment

- source line: `src/transaction/locator_sr.c:6582`
- 정확한 결정: 새로 추가된
  `/* LOB locators are resolved per attribute by heap_attrinfo_delete_lob (CBRD-26847) */` 주석을 현재 문구
  그대로 둔다.
- 근거: fetched record의 유일한 body consumer는 `heap_attrinfo_delete_lob`이다. 이 함수는 각 BLOB/CLOB
  attribute를 `heap_attrvalue_read`로 Resolve해 논리 `DB_ELO` locator를 얻은 뒤 external LOB를 삭제한다.
- 안전성: 주석은 실행 동작을 바꾸지 않고 D-013의 per-attribute OOS/LOB 소비 계약과 일치한다.
- 권고: 현재 문구 그대로 둔다.
- 사용자 결정: **일괄 승인** (2026-08-03, “yes to all”)

## Source line audit completion

- 원래 patch의 policy argument 16개와 comment block 19개를 모두 개별 감사했다.
- 승인된 추가 오류 처리:
  - serial attribute Resolve 오류를 계산 전에 전파
  - LOB delete fetch 오류 보존 및 primary-error 우선/scan-cache-error fallback
  - MVCC reevaluation scan-cache cleanup 오류를 `V_ERROR`로 변환
- 최종 source 검증: `git diff --check` 통과, 새 주석 120자 제한 확인, `debug_gcc` 전체 build/install 통과
  (2026-08-03).

## D-035 — audit inventory count correction

- source of truth: `AUDIT-INVENTORY.freeze-6816023df.tsv`는 header 포함 262줄, data 261행이다.
- 재집계: forward 114 + reverse 147 = 261; CORRECT 167 + EXCLUDED 64 + OVER_EXPAND 25 + FOLLOWUP 5 = 261.
- 정확한 결정:
  - `prompt-2026-07-31.md`의 256/109 수치를 261/114로 정정한다.
  - `FINDINGS.md` 요약을 261행(forward 114, reverse 147)으로 정정한다.
  - `SEARCH-LEDGER.md` 재개 블록을 261행 closure 및 `F-001..F-048`로 정정한다.
  - `SEARCH-LEDGER.md` 최종 tally를 261/CORRECT 167로 정정한다.
  - 정확한 freeze TSV는 수정하지 않는다.
- 안전성: 조사 결과나 verdict를 바꾸지 않고 closure pass에서 추가된 F-044..F-048 다섯 행을 요약 문서에
  반영한다. OVER_EXPAND 25, distinct source site 16, FOLLOWUP 5 결론은 변하지 않는다.
- 사용자 결정: **승인** (2026-08-03)

## D-036 — final build and OOS test verification

- 정확한 검증:
  - `direnv exec . just build`: `debug_gcc` 전체 build/install 성공
  - `direnv exec . just build-test`: OOS CTest 24개 중 24개 통과, 실패 0개
  - CTest 총 실행 시간: 42.18초
  - `git diff --check`: 통과
- 의미: 승인된 policy 변경, 오류 전파, 주석 정정이 현재 worktree에서 컴파일되고 기존 OOS 단위/서버/SQL
  테스트 묶음을 깨뜨리지 않았음을 확인했다.
- 한계: 이 결과는 기존 OOS suite의 회귀 검증이다. 원래 16개 policy call site 각각을 독립적으로 실행하고
  Expand 호출 횟수까지 단언하는 전용 테스트가 모두 존재한다는 뜻은 아니다.
- 사용자 결정: 앞서 승인된 변경의 최종 검증 결과를 감사 로그에 기록 (2026-08-03)

## D-037 — visible-version regression test design

- 정확한 결정: `unit_tests/oos/sql/test_oos_sql_visible_version.cpp`에 다음 두 회귀 테스트를 추가한다.
  - `ScanrangeNextFirstObjectFetchDoesNotExpandWholeRecord`: 64 KiB `BIT VARYING` 값을 가진 행을 만든 뒤
    `heap_scanrange_to_following (..., start_oid = NULL)`로 range를 설정하고, NULL current OID로
    `heap_scanrange_next`를 호출해 `oos_debug_counters.read_many_calls == 0`을 단언한다.
  - `LargeOldRecordUpdateDoesNotExpandWholeRecord`: OOS 대상 payload와 인덱스 키를 가진 행에서 키만 갱신한 뒤
    OOS batch read가 발생하지 않았고 payload의 길이와 값이 보존되었음을 확인한다.
- 근거: 첫 테스트는 production과 같은 NULL 시작 경계로 range를 설정한 뒤 감사 대상
  `heap_scanrange_next`의 first-object fetch를 직접 실행한다. sole caller가 body를 attribute layer로 읽는
  경로에서 전체 OOS materialization이 없어야 한다는 계약을 계측한다. 두 번째 테스트는 사용자가 보는 SQL
  갱신 결과의 무결성을 보강한다.
- 안전성: 테스트 전용 테이블과 기존 OOS debug counter만 사용한다. production 동작이나 공개 API를 바꾸지
  않으며 각 fixture 종료 시 데이터베이스를 정리한다.
- 사용자 결정: 다음 단계인 전용 회귀 테스트 추가를 진행하도록 승인 (2026-08-03)

## D-038 — scanrange test red/green proof

- red 검증: 감사 대상 `heap_scanrange_next` first-object fetch의 정확한 policy를 일시적으로
  `HEAP_RECDES_CONSUME_RAW_BYTES`로 바꾸고 다시 빌드했을 때
  `ScanrangeNextFirstObjectFetchDoesNotExpandWholeRecord`가 실패했다. 실제 `read_many_calls`는 1, 기대값은 0이었다.
- green 검증: 같은 줄을 승인된 `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`로 복구하고 다시 빌드했을 때 테스트가
  통과했으며 `read_many_calls`는 0이었다.
- 근거: 테스트가 단순히 SQL 결과만 확인하는 것이 아니라 감사 대상 policy의 잘못된 회귀를 실제로 검출함을
  red/green으로 입증한다.
- 안전성: red 검증용 production 변경은 즉시 복구했다. 최종 diff와 최종 빌드에는 승인된
  `HEAP_RECDES_DONT_CONSUME_RAW_BYTES`만 남는다.

## D-039 — locator SQL coverage limitation and external testcase results

- `LargeOldRecordUpdateDoesNotExpandWholeRecord`의 한계: locator의 old-record fetch policy를 일시적으로
  `CONSUME_RAW_BYTES`로 바꿔도 이 SA SQL 테스트는 red가 되지 않았다. 이 실행 형태에서는 update 경로가 감사한
  fetch 지점에 NULL oldrecdes를 공급하거나 해당 fetch를 우회하므로, 이 테스트를 locator 두 호출 지점의 직접
  policy 증명으로 해석하지 않는다.
- CTP shell: CS mode의 `shell/_40_guava/cbrd_26847` 테스트는 1건 중 1건 통과했다. 64 KiB OOS payload를
  넣고 인덱스 키만 갱신한 뒤 길이와 전체 값 보존을 확인했다.
- CTP SQL: 전용 case/answer는 작성했지만 로컬 CTP가 `cubrid.sql.CUBRIDOID` 등 JDBC class를 찾지 못해 case를
  실행하지 못했다. runner의 exit code 0은 테스트 성공이 아니며 자동 answer 비교는 미검증 상태다.
- 근거: 직접 계측 증거, 사용자 관점의 결과 회귀, 인프라 실패를 구분해야 각 테스트가 실제로 보장하는 범위를
  과장하지 않는다.
- 안전성: red 탐색용 locator 변경은 모두 복구했다. CTP 실행 뒤 남아 있던 broker도 명시적으로 중지했다.

## D-040 — final regression verification after adding dedicated tests

- 정확한 검증:
  - `direnv exec . just build`: `debug_gcc` 전체 build/install 성공
  - `direnv exec . just build-test`: 새 `test_oos_sql_visible_version`을 포함한 OOS CTest 25개 중 25개 통과,
    실패 0개
  - 새 test binary: 2개 테스트 모두 통과
  - CTest 총 실행 시간: 42.82초
- 의미: 승인된 source 변경과 새 회귀 테스트가 함께 컴파일되며 기존 OOS test suite를 깨뜨리지 않는다.
- 한계: `heap_scanrange_next` call site는 red/green으로 직접 증명했지만 scanrange following/prior 변경 branch와
  locator 두 old-record fetch call site는 직접 도달하지 않는다. 이 지점은 별도의 lower-level 주입 테스트
  없이는 같은 수준의 계측 증명이 아니며 소비 흐름의 정적 감사 근거를 사용한다.

## D-041 — non-NULL scanrange start OID follow-up separation

- 정확한 결정: `heap_scanrange_to_following()`의 non-NULL/non-NULL_OID `start_oid` branch는 CBRD-26847 source
  변경에 포함하지 않고 별도 Correct Error 이슈 자료로 분리한다.
- 근거:
  - 함수 계약은 지정한 `start_oid`를 range의 첫 객체로 사용한다고 명시한다.
  - 구현은 `scan_range->first_oid = *start_oid`를 수행한 직후 visibility fetch에
    `&scan_range->last_oid`를 전달한다.
  - `heap_scanrange_start()` 직후 `last_oid`는 NULL이다. 유효한 첫 heap OID를 non-NULL `start_oid`로 전달한
    임시 lower-level 테스트에서 `heap_prepare_object_page()`의 `!OID_ISNULL (oid)` assertion으로 abort함을
    재현했다.
  - 현재 repository의 유일한 production caller는 `start_oid = NULL`을 전달하므로 일반 grouped query scan은
    이 branch를 타지 않는다.
- 안전성: 이번 OOS policy 변경이 만든 결함이 아니고 현재 caller가 사용하지 않는 API branch이므로, 이미
  검증한 CBRD-26847 patch에 동작 수정을 섞지 않는다. 재현용 임시 테스트는 결과 확인 후 제거했고 source를
  다시 빌드해 committed state와 local binary를 일치시켰다.
- 후속 자료:
  `/home/vimkim/gh/my-cubrid-jira/issues/heap-scanrange-following-nonnull-start-oid_ab42c48_codex.md`
- 사용자 결정: CBRD-26847 완료 뒤 별도 후속 이슈 자료로 순서대로 분리하도록 승인 (2026-08-03)

## D-042 — PR base and latest OOS integration

- 정확한 결정: PR base를 `develop`이 아니라 `feat/oos`로 사용하고, source branch에 최신
  `origin/feat/oos`를 merge한다.
- 근거: merge 전 branch는 `origin/feat/oos`보다 16개 commit 뒤, CBRD-26847 commit 2개 앞이었다.
  `develop` 기준 PR은 OOS 기반 작업까지 83개 commit으로 보이지만 `feat/oos` 기준은 이 티켓의 2개 commit만
  분리된다. merge-tree 사전 검사는 conflict가 없음을 확인했다.
- 결과: 최신 base merge 뒤 reviewer 지적을 반영한 test 보강 commit까지 포함한 최종 HEAD는
  `89937d7bdac3d928c06b077fb80f0e6a12985a12`다. 기준 브랜치 대비 의도한 11개 파일, 196 insertions,
  26 deletions이며 `git diff --check`를 통과했다.
- 안전성: OOS feature branch의 최신 상태 위에서 티켓 변경만 review하도록 범위를 보존한다. 사용자 local
  submodule·설정·debug 파일은 merge, stage, commit 대상에서 제외했다.
- 사용자 결정: 최신 `feat/oos` merge와 검증 진행을 승인 (2026-08-03)

## D-043 — post-merge build and regression gate

- 정확한 검증:
  - debug GCC 전체 build/install 성공
  - 새 `test_oos_sql_visible_version`을 포함한 OOS CTest 25개 중 25개 통과, 실패 0개
  - 최종 CTest 총 실행 시간 45.40초
- 근거: 최신 OOS base와 CBRD-26847 변경을 함께 컴파일하고 전체 OOS suite로 회귀 여부를 다시 확인해야
  merge 전 검증 결과에만 의존하지 않는다.
- 한계: scanrange policy는 red/green 계측으로 직접 검증했지만 locator old-record fetch 두 지점은 전용
  lower-level 주입 계측까지 제공하지 않는다.

## D-044 — push hook exception and one-shot CI contract

- 정확한 결정: 게시 승인 뒤 source push에만 `git push --no-verify`를 사용한다. PR은
  `CUBRID/CUBRID:feat/oos` <- `vimkim:CBRD-26847-oos-visible-version`으로 만들고, 생성 뒤 exact-head를 다시
  검증한다. CI는 현재 head 이후의 기존 trigger와 실행 중 check를 모두 확인한 뒤 `/run all`을 최대 한 번만
  게시한다.
- 근거: local pre-push hook은 모든 branch에 최신 `origin/develop` 포함을 요구하지만, 올바른 PR base인 최신
  `origin/feat/oos` 자체가 그 조건을 만족하지 않는다. 따라서 이 hook 실패는 source freshness 실패가 아니라
  base 불일치에 의한 false block이다. `/run all`은 사용자가 요청한 SQL, medium, shell 전체 CI에 대응한다.
- 안전성: hook 우회는 push 한 번에만 한정한다. 우회 전에 build, OOS CTest, diff 범위, whitespace 검사를
  완료했고, CI 중복 방지 검사를 별도로 유지한다.
- 사용자 결정: 올바른 `feat/oos` 기준의 hook 우회, push, PR 생성, 전체 CI trigger를 승인 (2026-08-03)

## D-045 — independent grill finding and exact changed-line regression

- 발견: 최초 scanrange 테스트는 `heap_scanrange_to_following (..., start_oid = NULL)`까지만 호출해 이번 diff가
  바꾼 세 scanrange policy 지점이 아니라 기존 `heap_next (...DONT)`만 계측했다. 따라서 최초 D-038/D-040의
  “변경 call site 직접 증명” 해석은 과장이었다.
- 정확한 결정: range 설정 뒤 NULL current OID로 `heap_scanrange_next`를 직접 호출하도록 테스트를 보강하고,
  이 함수의 first-object policy 한 줄을 대상으로 red/green을 다시 수행한다. following/prior 변경 branch는
  직접 동적 검증했다고 주장하지 않고 정적 소비 흐름 감사로 한정한다.
- 검증: 임시 `CONSUME_RAW_BYTES`에서 `read_many_calls = 1`로 테스트가 실패했고, 최종
  `DONT_CONSUME_RAW_BYTES` 복구 후 해당 테스트와 전체 OOS CTest 25/25가 통과했다. 임시 production 변경은
  남아 있지 않다.
- 문서 정정: OOS 풀네임을 규범 문서의 `Out-of-row Overflow Storage`로 고치고, ADR 링크를 실제 원격인
  `vimkim/cubrid-oos-context`로 고쳤다.
- 안전성: 휴면 non-NULL following 오류를 수정하지 않고, 이번 diff의 기존 `heap_scanrange_next` 동작만
  실제로 실행하는 test code를 추가했다. 독립 reviewer의 major 1건과 minor 2건을 모두 해소한다.
