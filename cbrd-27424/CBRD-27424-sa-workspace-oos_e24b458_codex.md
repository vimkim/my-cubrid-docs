# CBRD-27424: standalone workspace 쓰기의 OOS 지원

https://jira.cubrid.org/browse/CBRD-27424

## Purpose

OOS (Out-of-row Overflow Storage)는 큰 컬럼 값을 별도 페이지에 저장하는 기능이다. 이 변경은 standalone 객체 적재와 같은 경로를 사용하는 CSQL 쓰기에서 빠져 있던 OOS 변환을 연결한다.

- AS-IS: `loaddb -S`와 CSQL의 workspace 쓰기는 큰 값을 정확히 저장하지만 OOS 변환을 호출하지 않아 값을 행 내부에 둔다.
- TO-BE: 해당 쓰기도 기존 OOS 정책에 따라 큰 값을 분리하고, 원래 값과 객체 참조를 유지한다.

기준 커밋은 `f4299ac0cd777a2a964c1f197ae5ebf9841a4936` (`feat/oos`)이며, 변경 커밋은 `e24b458bfea4d49cc763328c055c5c5374694b06`이다. PR #7695의 변경을 이 브랜치에 포함하지 않고 별도로 호환성을 확인했다.

### Workspace란 무엇인가

Workspace는 CUBRID의 클라이언트 측 객체 관리 계층이다. 이 문서에서 객체는 클래스의 인스턴스, 즉 테이블의 한 행에 대응한다. 조회하거나 생성한 객체의 메모리 표현과 변경 상태를 프로세스 안에서 관리하고, 변경한 객체를 저장 계층으로 전달한다. SA는 클라이언트 기능과 저장 엔진을 한 프로세스에서 실행하므로 SA에도 이 계층이 존재한다.

| 구성 요소 | 역할 | OOS 문제와의 관계 |
|---|---|---|
| OID | 저장된 객체의 식별자. 새 객체는 영구 OID 할당 전 임시 OID를 가질 수 있다 | 객체 참조를 디스크 표현으로 바꿀 때 올바른 식별자가 필요하다 |
| MOP (`DB_OBJECT *`) | OID, 클래스 MOP, 객체 데이터 포인터, 상태 비트를 가진 메모리 핸들 | 다른 객체가 아직 적재되지 않았어도 참조할 핸들을 유지한다 |
| 메모리 객체 (`MOBJ`) | 속성 값의 메모리 표현 | `tf_mem_to_disk`가 이를 디스크 레코드 표현으로 직렬화한다 |
| dirty 목록 | 변경된 객체를 클래스별로 추적 | locator가 flush할 대상을 찾는다 |
| `LC_COPYAREA` / `RECDES` | 직렬화한 레코드를 전달하는 버퍼 / 레코드 설명자 | 기존 SA 경로는 이 표현을 OOS planner 없이 heap에 전달했다 |

`DB_OBJECT`에는 `class_mop`, `object`, `dirty_link`, `lock`, `mvcc_snapshot_version`, `dirty/deleted/pinned` 등의 필드가 있다. OID→MOP 해시와 클래스별 dirty 목록은 객체의 정체성과 변경 상태를 관리한다. 이것은 SQL 임시 테이블도, 디스크 페이지를 캐시하는 page buffer도 아니다. Workspace의 객체 표현과 저장 엔진의 페이지 표현은 별도 계층이다. [구조체 정의](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/object/work_space.h#L110), [해시·목록 관리](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/object/work_space.c#L76)

Flush는 dirty 객체를 저장 계층에 반영하는 작업이다. **Flush와 COMMIT은 다르다.** Flush되어 heap/OOS 페이지가 만들어져도 트랜잭션을 롤백할 수 있어야 한다. `ws_intern_instances`는 클래스 인스턴스를 flush/decache하고 dirty 목록을 정리한 다음 회수 가능한 MOP를 정리한다. 따라서 “loader가 workspace를 쓴다”는 말은 전체 입력 파일을 끝까지 메모리에 보관한다는 뜻이 아니다. [flush와 회수](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/object/work_space.c#L1549)

### 왜 SA loaddb가 workspace를 사용하는가

현재 SA loader는 객체 파일의 클래스·속성·객체 번호·객체 간 참조를 해석하고 기존 객체 API로 인스턴스를 구성한다. 아직 등장하지 않은 객체를 참조하는 forward reference도 처리한다. 단순히 각 입력 행을 독립적인 SQL INSERT 문으로 바꾸는 구현이 아니다.

`load_sa_loader.cpp`는 새 인스턴스에 `db_create_internal`을 호출하고, 이미 forward reference로 예약한 인스턴스에는 `ws_mop`으로 기존 핸들을 찾는다. 속성을 채우는 동안 객체와 클래스를 pin하고, 객체 번호와 OID의 대응 및 임시 OID 목록을 관리한다. 적재 마무리에서는 영구 OID 할당을 수행하고, `ldr_flush` → `ws_intern_instances`로 저장한다. [인스턴스 생성·예약 객체 재사용](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/loaddb/load_sa_loader.cpp#L4620), [영구 OID 할당과 flush 순서](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/loaddb/load_sa_loader.cpp#L4840), [객체 번호 매핑](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/loaddb/load_sa_loader.cpp#L5558)

이 구조에서 workspace를 사용하는 이점은 객체 참조와 속성 변환, 변경 추적, 묶음 flush를 기존 객체 계층으로 처리할 수 있다는 점이다. 이는 현재 소스 구조에서 도출한 설계 해석이며, 최초 도입 당시의 의사결정 기록을 확인했다는 뜻은 아니다. SA라는 실행 모드 자체가 workspace 사용을 강제하지는 않는다. loader를 다른 경로로 재구현할 수 있지만, 객체 파일의 의미와 오류·트랜잭션 처리를 함께 보존해야 한다.

### 왜 일부 csql -S 쓰기만 workspace를 사용하는가

`-S`는 서버 프로세스에 접속하는 대신 standalone 엔진을 사용한다는 선택이다. INSERT를 query execution 경로로 처리할지 객체 API/workspace 경로로 처리할지는 별도의 판단이다. 소스의 “server insert”라는 이름도 SA에서는 같은 프로세스의 query execution 경로를 뜻할 수 있다.

`is_server_insert_allowed`는 `insert_execution_mode`의 INSERT VALUES/SELECT 허용 비트와 문장 속성을 검사한다. 값이 0이면 해당 비트가 없어서 server insert를 허용하지 않는다. 일반 속성이 아닌 대상, INTO 변수, check option, 관련 트리거 등도 경로 선택에 관여한다. UPDATE에도 트리거 등에 따라 workspace를 선택하는 판단이 있다. 이 목록은 소스에서 확인한 조건의 예시이며 모든 SQL 형태에 대한 지원표는 아니다. [INSERT 판단](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/query/execute_statement.c#L12310), [UPDATE 트리거 판단](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/query/execute_statement.c#L9843)

| 실행 예 | 실제 쓰기 경로 | 이번 누락의 영향 |
|---|---|---|
| `cubrid loaddb -S` 객체 파일 적재 | SA loader → workspace → locator force | 영향 있음 |
| 기본 설정의 단순 `csql -S` INSERT | query execution → 기존 heap attribute 변환 | 이 재현에서는 영향 없음 |
| `insert_execution_mode=0` 이후 `csql -S` INSERT | 객체 생성 → workspace → locator force | 영향 있음 |
| 회귀 테스트의 행 트리거가 있는 UPDATE | workspace 변경 → 여러 객체 force | 영향 있음 |
| `loaddb -C`, 일반 `csql -C` INSERT 대조군 | 기존 서버 적재/SQL 경로 | 동일 값의 OOS 저장 정상 확인 |

CSQL workspace 재현에서는 다음 설정을 사용한다. 구체적인 payload와 테이블 생성까지 포함한 전체 쉘은 아래에 있다. 기본 INSERT 대조군은 설정이 섞이지 않도록 **새 CSQL 프로세스**에서 실행한다.

```sql
SET SYSTEM PARAMETERS 'insert_execution_mode=0';
```

### Workspace의 장단점과 이번 수정의 비용

| 관점 | 장점 | 비용 또는 주의점 |
|---|---|---|
| 객체 정체성과 참조 | MOP와 OID 매핑으로 객체 그래프 및 forward reference 처리 가능 | 임시→영구 OID 전환과 예약 객체의 UPDATE를 빠짐없이 처리해야 한다 |
| 변경 추적과 묶음 처리 | dirty 객체를 모아 flush하며 객체 API 구현을 재사용 | 객체·메타데이터 메모리와 pin/decache/회수 관리 비용이 발생한다 |
| 객체 단위 의미 | 트리거 등 객체 계층이 필요한 경로를 지원 | query execution과 별도 쓰기 경로여서 OOS 같은 저장 기능의 누락 위험이 있다 |
| 이번 공통 경계 변환 | 기존 직렬화·참조 처리를 유지하며 OOS planner를 재사용 | 직렬화된 레코드를 DB_VALUE로 읽고 다시 직렬화하는 CPU·임시 메모리 비용이 추가된다 |

이는 구현 구조에서 예상되는 비용·이점이다. 처리량이나 최대 메모리를 비교한 벤치마크 결과는 없으므로 성능 개선 또는 무시할 수 있는 비용이라고 단정하지 않는다. 특히 OOS 대상이 아닌 variable attribute 레코드도 planner 판단까지의 비용은 발생할 수 있다.

### 재현과 원인

압축 영향을 피하기 위해 고정 난수로 만든 5,000바이트 VARBIT 값을 사용했다. 커밋 후 새 연결에서 정확한 값 일치와 `;oos_stats`의 실제 OOS 레코드 수를 함께 확인했다.

| 쓰기 경로 | 변경 전 OOS 레코드 수 | 변경 후 OOS 레코드 수 | 값 일치 |
|---|---:|---:|---|
| `loaddb -S` | 0 | 1 | 모두 통과 |
| 일반 INSERT, `csql -S` | 1 | 1 | 모두 통과 |
| 일반 INSERT, `csql -C` | 1 | 1 | 모두 통과 |
| `loaddb -C` | 1 | 1 | 모두 통과 |
| CSQL workspace INSERT | 0 | 1 | 모두 통과 |

CSQL은 `-S`만으로 workspace 경로를 선택하지 않는다. `insert_execution_mode=0`으로 해당 경로를 선택하여 별도로 확인했다.

디버거에서 SA loader는 `tf_mem_to_disk`를 한 번 호출했지만 `heap_attrinfo_determine_disk_layout`과 `oos_insert_many`를 호출하지 않았다. 일반 CSQL INSERT는 두 함수를 각각 한 번 호출했다. 문제는 값 손실이나 OOS 정책의 거절이 아니라 변환 호출의 누락이었다.

## Implementation

### 변환 위치의 대안과 선택 근거

해결해야 할 조건은 “큰 값을 분리한다”보다 넓다. 최종 파티션의 OOS 파일에 저장하고, 객체 참조와 CHN을 유지하며, heap/index 실패 시 새 OOS 조각까지 롤백해야 한다. loader만 고치면 같은 workspace를 사용하는 CSQL 문제는 남는다.

| 대안 | 얻는 점 | 문제와 판단 |
|---|---|---|
| SA loader에만 변환 추가 | 재현 지점 가까이 수정 가능 | CSQL workspace INSERT/UPDATE를 해결하지 못해 제외 |
| `tf_mem_to_disk`에 OOS 생성 추가 | workspace 직렬화 경로 전체를 포괄 | 클라이언트 직렬화 계층에 저장 엔진 작업이 들어간다. 최종 파티션과 force의 rollback 경계보다 일러서 책임이 섞이고 CS까지 고려해야 하므로 제외 |
| **SA locator force 경계에서 기존 변환기 재사용** | 최종 저장 대상과 기존 top operation을 이용하며 공통 workspace 쓰기를 포괄 | decode/re-encode 및 호출 경로 표식이 필요하지만 현재 결함을 가장 좁은 범위에서 해결하므로 선택 |
| loader/CSQL 객체 경로를 query execution 경로로 교체 | 장기적으로 쓰기 경로 중복을 줄일 가능성 | 객체 참조, 예약 OID, 트리거, 필터 오류와 적재 의미를 재설계해야 하므로 이번 결함 수정 범위를 넘음 |

선택은 단순한 변경 줄 수가 아니라 **대상 heap 결정 시점, 트랜잭션 원자성, 영향 경로의 포괄성, 기존 객체 의미의 보존**에 근거한다. 기존 planner를 호출하므로 OOS 임계값과 컬럼 선택 규칙을 loader용으로 복제하지 않는다. 아래 실패 후 조각 수 검증과 파티션 이동 테스트가 이 판단의 핵심 검증이다.

### 변경 전후 호출 흐름

```text
SA loaddb 객체 파일                  CSQL 객체 경로
  db_create_internal / ws_mop          객체 생성·속성 변경
                 \                    /
                 workspace dirty 객체
                          |
             locator_mem_to_disk → tf_mem_to_disk
                          |  직렬화된 RECDES / copyarea
                   locator force
                          |
            INSERT / 예약 OID UPDATE / 여러 행 UPDATE
                          |
               실제 파티션·heap 결정
                          |
       [추가] locator_demote_workspace_record (SA만)
          RECDES → DB_VALUE → 기존 heap attribute 변환기
                 → OOS planner → OOS 조각 + 참조
                          |
                   heap / index 쓰기
       < OOS 생성과 heap/index 쓰기는 기존 force top operation 안 >
```

변경 전에는 추가한 단계 없이 직렬화된 레코드가 heap으로 갔다. `tf_mem_to_disk`의 직렬화가 성공했다는 사실만으로 OOS planner가 실행되었다고 볼 수 없다. 일반 SQL 경로는 이미 heap attribute 변환기를 사용하므로 같은 누락이 없었다. [workspace 직렬화](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/transaction/locator_cl.c#L4366), [flush copyarea와 예약 OID 처리](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/transaction/locator_cl.c#L4038)

### 공통 force 경계에서 변환

`src/transaction/locator_sr.c`의 `locator_demote_workspace_record`가 SA workspace 레코드를 읽고 기존 heap attribute 변환기를 호출한다. 새 OOS 선택 정책을 추가하지 않는다.

- `from_workspace` 인자로 workspace 쓰기를 구분한다. INSERT, 예약된 OID를 채우는 UPDATE, 여러 행 UPDATE를 포함한다.
- 실제 파티션과 heap이 결정된 뒤 변환한다. 파티션 이동은 대상 INSERT까지 이 구분을 전달한다.
- 기존 force top operation 안에서 OOS 생성과 heap/index 쓰기를 수행한다. 전체 롤백뿐 아니라 오류를 무시하고 계속하는 적재의 객체별 롤백도 같은 범위에 들어간다.
- 별도 copyarea에 변환 결과를 만들고 성공·실패 경로에서 해제한다. 호출자의 원본 버퍼를 덮어쓰지 않는다.
- OOS 분리가 선택되지 않으면 원본 레코드를 유지한다. 분리되면 workspace에서 정한 CHN (캐시 변경 번호)을 보존한다.
- 이미 변환한 레코드와 클래스 정의는 제외한다. SERVER 모드에서는 새 변환을 수행하지 않는다.
- `LOB_FLAG_EXCLUDE_LOB`로 이미 저장된 외부 BLOB/CLOB를 다시 복사하지 않는다.

`src/transaction/locator_sr.h`에는 호출 경로를 구분하는 기본 인자를 추가했다. 기존 SQL 실행기, CS loader, 복제 경로는 기존 호출 동작을 유지한다.

### 구현을 읽는 순서와 불변 조건

1. **입구를 구분한다.** `xlocator_force` 및 여러 행 UPDATE의 force 호출에서 `from_workspace`를 전달한다. `locator_insert_force`, `locator_update_force` 등의 기본값은 false이므로 기존 SQL/CS loader/복제 호출에 새 변환을 자동 적용하지 않는다. forward reference로 OID를 먼저 예약하면 flush 작업이 UPDATE가 될 수 있으므로 INSERT만 처리해서는 부족하다.
2. **소유자를 먼저 정한다.** INSERT는 partition pruning 이후 실제 클래스에 대해 변환한다. UPDATE로 파티션이 바뀌면 `locator_move_record`가 표식을 대상 INSERT까지 넘긴다. 원본 파티션에서 조각을 만들고 대상 레코드에 넣는 순서가 되면 안 된다.
3. **레코드를 해석한다.** helper는 SA에서만 동작한다. root class 레코드와 이미 OOS 표시가 있는 입력을 건너뛴다. `heap_attrinfo_start` 후 variable attribute가 없으면 종료하고, 나머지는 `heap_attrinfo_read_dbvalues_without_oid`로 읽는다. INSERT의 출력 OID는 아직 유효하지 않을 수 있으므로 이 단계에서 그 OID에 의존하지 않는다.
4. **기존 정책으로 다시 만든다.** `locator_allocate_copy_area_by_attr_info`에 `LOB_FLAG_EXCLUDE_LOB`를 넘긴다. workspace 직렬화에서 처리한 외부 LOB를 다시 복사하지 않으면서 기존 OOS planner를 사용한다. 결과에 OOS 표시가 없으면 새 버퍼를 해제하고 입력 레코드를 그대로 쓴다. 분리했다면 입력 CHN을 결과에 복원한다. workspace 직렬화가 이미 갱신한 캐시 변경 번호를 이 변환만으로 다시 바꾸지 않는다.
5. **수명과 실패를 묶는다.** attribute 정보는 helper에서 정리하고 copyarea는 caller가 heap/index 처리 후 성공·오류 경로에서 해제한다. 원본 flush 버퍼를 덮어쓰지 않는다. OOS 생성은 기존 force top operation 안에서 수행되며, 무시 가능한 오류가 난 객체의 하위 top operation도 포함된다. 버퍼 해제는 메모리 정리이고 OOS 페이지의 rollback은 트랜잭션 작업이라는 구분이 중요하다.

[helper 전체](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/transaction/locator_sr.c#L4931), [INSERT 적용 지점](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/transaction/locator_sr.c#L5130), [파티션 이동 전달](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/transaction/locator_sr.c#L5455), [UPDATE 적용 지점](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/src/transaction/locator_sr.c#L6119), [전체 변경 diff](https://github.com/CUBRID/cubrid/commit/e24b458bfea4d49cc763328c055c5c5374694b06)

### 회귀 테스트

`unit_tests/oos/scripts/test_workspace_oos.py`를 `test_oos_workspace_cli`라는 CTest로 등록했다. 설치된 `cubrid`와 `csql`, Python 3.7 이상이 필요하다 (`subprocess.run(text=True)` 사용). 전용 DB 등록 파일과 16 KiB 페이지의 임시 DB를 만들고 실제 CLI 경로를 실행한다.

테스트는 논리 값뿐 아니라 실제 OOS 조각 수를 확인한다. 성공한 임시 DB는 삭제하며 실패 시 출력과 DB를 남겨 원인을 조사할 수 있다.

## Remarks

### 독자가 실행할 수 있는 최소 재현

아래 쉘은 세 경로를 같은 데이터로 비교한다. 입력 SQL과 객체 파일을 직접 생성하므로 별도 fixture가 필요하지 않다. 설치된 대상 빌드의 `CUBRID`, `PATH`, 라이브러리 경로가 설정되어 있고 `cubrid`, `csql`, Python 3.7+를 실행할 수 있어야 한다. OOS 기능이 없는 일반 릴리스가 아니라 위에 명시한 `feat/oos` 기준 빌드와 수정 빌드를 비교한다.

기본 `/tmp` 대신 충분한 여유 공간이 있는 디렉터리를 `TMPDIR`로 지정할 수 있다. 작은 초기 볼륨을 지정해도 catalog 생성과 자동 확장에 추가 공간이 필요하므로 여러 GiB의 여유 공간을 권장한다. 쉘은 전용 DB 등록 파일과 설정 파일을 사용한다. 성공 시 DB를 삭제하고 입력·출력 파일은 출력된 `Evidence:` 디렉터리에 남긴다. 실패 시 DB도 남기므로 그 디렉터리를 조사할 수 있다.

아래 내용을 `CBRD-27424-repro_e24b458_codex.sh`로 저장한다. [동일한 검증 완료 쉘](https://github.com/vimkim/my-cubrid-jira/blob/1c3c5c2/issues/CBRD-27424-repro_e24b458_codex.sh)도 사용할 수 있다.

```bash
#!/usr/bin/env bash
set -euo pipefail
expected=${1:?Usage: bash CBRD-27424-repro_e24b458_codex.sh before|after}
case "$expected" in before|after) ;; *) exit 2 ;; esac
repro_dir=$(mktemp -d "${TMPDIR:-/tmp}/cbrd27424-repro.XXXXXX")
export CUBRID_DATABASES="$repro_dir"
export CUBRID_CONF_FILE="$repro_dir/cubrid.conf"
cd "$repro_dir"
printf '[common]\ndata_buffer_size=64M\nlog_buffer_size=16M\n' > cubrid.conf
printf 'Evidence: %s\n' "$repro_dir"
cubrid createdb --db-page-size=16K --db-volume-size=32M --log-volume-size=32M -F "$repro_dir" oos27424 en_US.utf8 > createdb.out 2>&1
python3 - <<'PY'
from pathlib import Path
import random
rng = random.Random(27424)
payload = bytes(rng.randrange(256) for _ in range(5000)).hex()
Path('schema.sql').write_text('CREATE TABLE t_load(v BIT VARYING);\nCREATE TABLE t_ws(v BIT VARYING);\nCREATE TABLE t_normal(v BIT VARYING);\nCOMMIT;\n')
Path('load.objects').write_text("%%class t_load (v)\nX'%s'\n" % payload)
Path('workspace.sql').write_text("SET SYSTEM PARAMETERS 'insert_execution_mode=0';\nINSERT INTO t_ws VALUES (X'%s');\nCOMMIT;\n" % payload)
Path('normal.sql').write_text("INSERT INTO t_normal VALUES (X'%s');\nCOMMIT;\n" % payload)
for table in ('t_load', 't_ws', 't_normal'):
    Path(table + '.sql').write_text("SELECT CASE WHEN COUNT(*)=1 AND SUM(CASE WHEN v=X'%s' THEN 1 ELSE 0 END)=1 THEN 'VALUE_OK' ELSE 'VALUE_BAD' END AS verdict FROM %s;\n;oos_stats %s\n" % (payload, table, table))
PY
csql -S -u dba --no-auto-commit oos27424 < schema.sql > schema.out 2>&1
cubrid loaddb -S -u dba -d load.objects oos27424 > load.out 2>&1
csql -S -u dba --no-auto-commit oos27424 < workspace.sql > workspace.out 2>&1
# 새 CSQL 프로세스에서 기본 INSERT 경로를 실행한다.
csql -S -u dba --no-auto-commit oos27424 < normal.sql > normal.out 2>&1
for table in t_load t_ws t_normal; do
    csql -S -u dba --no-auto-commit oos27424 < "$table.sql" > "$table.out" 2>&1
done
python3 - "$expected" <<'PY'
from pathlib import Path
import re
import sys
expected = [0, 0, 1] if sys.argv[1] == 'before' else [1, 1, 1]
for table, wanted in zip(('t_load', 't_ws', 't_normal'), expected):
    output = Path(table + '.out').read_text()
    assert "'VALUE_OK'" in output and "'VALUE_BAD'" not in output, output
    match = re.search(r'Live OOS records\s*:\s*(\d+)', output)
    actual = int(match[1]) if match else 0 if 'has no OOS file' in output else None
    print('%s: VALUE_OK, OOS=%s (expected %s)' % (table, actual, wanted))
    assert actual == wanted, output
PY
cubrid deletedb oos27424 > deletedb.out 2>&1
```

각 빌드를 활성화한 별도 쉘에서 실행한다. `before|after`는 기대 결과를 선택하며 소스나 DB 동작을 바꾸는 옵션이 아니다.

```bash
# f4299ac0cd777a2a964c1f197ae5ebf9841a4936 빌드 환경
bash CBRD-27424-repro_e24b458_codex.sh before

# e24b458bfea4d49cc763328c055c5c5374694b06 빌드 환경
bash CBRD-27424-repro_e24b458_codex.sh after
```

```text
# before
 t_load: VALUE_OK, OOS=0 (expected 0)
 t_ws: VALUE_OK, OOS=0 (expected 0)
 t_normal: VALUE_OK, OOS=1 (expected 1)
# after
 t_load: VALUE_OK, OOS=1 (expected 1)
 t_ws: VALUE_OK, OOS=1 (expected 1)
 t_normal: VALUE_OK, OOS=1 (expected 1)
```

위 쉘은 두 빌드에서 실제 통과했다. `before` 빌드에 `after` 인자를 주면 첫 OOS 수 assertion이 실패하는 회귀 조건이 된다. `schema.sql`, `load.objects`, `workspace.sql`, `normal.sql`을 읽으면 사용한 명령과 정확한 5,000바이트 literal을 확인할 수 있다. 각 테이블의 검증 SQL은 새 연결에서 **전체 값 일치와 실제 OOS 레코드 수**를 검사한다. SELECT가 성공하거나 값 길이가 같다는 것만으로는 이 결함을 검출할 수 없다. 난수 seed는 고정되어 있고 압축하기 쉬운 반복 문자열을 피한다.

### 확장 회귀를 직접 실행하는 방법

수정 커밋의 소스 디렉터리에서 해당 빌드의 설치 환경을 활성화하고 실행한다. 이 방식은 CTest 등록 여부와 독립적으로 동일한 assertion을 실행한다.

```bash
python3 unit_tests/oos/scripts/test_workspace_oos.py
```

[전체 회귀 소스](https://github.com/CUBRID/cubrid/blob/e24b458bfea4d49cc763328c055c5c5374694b06/unit_tests/oos/scripts/test_workspace_oos.py)는 입력 SQL/객체 파일을 생성하고 실패 시 경로와 출력을 남긴다. 예상 결과는 12개 시나리오의 `PASS:` 출력과 정상 종료이다.

| 메서드 / 시나리오 | 구체적인 검증 |
|---|---|
| `basic_loader`, `workspace_sql` | 각각 5,000바이트 값 일치와 OOS 1개 |
| `references` | 상호 객체 참조와 OOS 2개 |
| `partitions` | 각 파티션 OOS 1개, 부모 0개 |
| `rollback` | flush한 INSERT를 rollback한 뒤 OOS 수 2→1 |
| `update_cleanup` | 행 트리거 UPDATE rollback/commit 후 값·조각 확인, DELETE 후 0개 |
| `failed_load` | 중복 키로 전체 적재 실패 후 기존 OOS 1개 유지 |
| `filtered_load` | 오류 670을 무시한 뒤 정상 행을 계속 적재, 최종 OOS 2개로 실패 행의 고아 조각 배제 |
| `external_lobs` | 기존 BLOB/CLOB의 내용·경로·파일 바이트를 rollback/commit 후 비교 |
| `storage_policy` | NULL/빈 값/작은 값은 0개, FORCE_OUTLINE과 큰 컬럼 우선 선택, 50,000바이트는 4개 조각 |
| `partition_move` | 원본 파티션 0개, 대상 파티션 2개 |
| `no_logging` | 별도 DB에서 성공한 no-logging 적재와 새 연결 읽기, OOS 1개 |

### Python 의존성의 후속 수정 상태

`e24b458`은 CLI 테스트를 등록하면서 Python을 무조건 요구했다. CircleCI job 154424는 `unit_tests/oos/CMakeLists.txt`의 Python 탐색에서 실패했다. 아래는 그 엔진 커밋에 포함되지 않은 **로컬 검토 중 후속 수정**이다.

`UNIT_TEST_OOS_WORKSPACE_CLI`를 기본 OFF로 두고, ON일 때만 Python 3.7 이상을 필수로 찾으며 기존 테스트를 등록한다. 일반 빌드는 Python 없이 구성할 수 있지만, 명시적으로 켠 테스트가 Python 부족으로 조용히 생략되지는 않는다. 기존 Python assertion은 변경하지 않는다.

후속 수정 적용 후 프로젝트의 CMake 구성 옵션에 `-DUNIT_TEST_OOS_WORKSPACE_CLI=ON`을 추가하고 설치 빌드를 준비한 뒤 다음과 같이 실행한다. `<build-directory>`는 실제 구성한 빌드 디렉터리로 바꾼다.

```bash
ctest --test-dir <build-directory> --output-on-failure -R '^test_oos_workspace_cli$'
```

CMake의 `CMAKE_DISABLE_FIND_PACKAGE_Python3=TRUE`로 Python 탐색을 차단한 검증에서 기본 OFF 구성은 통과했고 ON 구성은 요구대로 실패했다. 이것은 Python 부재를 구성 단계에서 모사한 결과이며 CircleCI 이미지 전체를 재현한 결과는 아니다. 호환 Python으로 ON 구성도 통과했다. 최신 실행 결과는 아래에 별도로 기록한다.

### 2026-09-11 후속 수정의 로컬 검증

| 검증 | 결과 |
|---|---|
| Python 탐색 차단, 기본 옵션 OFF | 구성 통과, 해당 CLI 테스트 등록 0개 |
| Python 탐색 차단, 명시적 옵션 ON | 필수 의존성 오류로 구성 실패: 의도한 동작 |
| 옵션 ON, Python 3.14.3 | 최소 3.7 조건 만족, 구성 통과 |
| GCC debug 빌드와 전체 CTest 첫 실행 | 빌드 성공, 27/28 통과. 마지막 CLI 시나리오의 createdb가 디스크 공간 부족으로 실패 |
| 충분한 공간의 TMPDIR에서 동일 CLI 재실행 | 1/1 CTest 및 12개 시나리오 통과, 60.74초 |

실패 로그에는 마지막 DB의 자동 확장에 필요한 공간이 부족하다는 오류가 있었다. assertion 또는 엔진 코드를 변경하지 않고 임시 디렉터리만 다른 파일시스템으로 옮겼다. 따라서 오늘의 결과는 “전체 실행 27/28 + 실패 테스트 집중 재실행 통과”이며, 아래의 과거 단일 실행 28/28과 구분한다. 후속 변경은 아직 커밋·push하지 않았으며 새 CI 결과는 없다.

### Test Plan — 최초 엔진 수정 검증

| 검증 | 결과 |
|---|---|
| 변경 전 최소 SA loader 회귀 테스트 | 값 일치는 통과, OOS 수가 0이므로 실패 |
| 변경 전 GCC debug CTest | 27/27 통과 |
| 변경 후 GCC debug 빌드 및 CTest | 28/28 통과, 176.16초 |
| 새 CLI 회귀 테스트 | 12개 시나리오 통과, 62.86초 |
| SA/CS loader 및 일반 CSQL 4개 경로 재실행 | 모두 통과, 17.48초 |
| PR #7695 head에 동일 패치 적용 및 빌드 | 통과 |
| PR #7695 head에서 새 CLI 회귀 테스트 | 12개 시나리오 모두 통과 |
| 코드 표준·스펙 리뷰 및 포맷 검사 | 확인된 코드 결함 없음, 포맷 일치 |

12개 시나리오는 기본 SA loader, CSQL workspace INSERT, 앞뒤 객체 참조, 파티션별 소유권, INSERT 롤백, UPDATE/DELETE 정리, 전체 적재 실패, 무시한 중복 키 이후 적재 계속, 기존 외부 LOB 보존, 저장 정책 및 여러 조각, 파티션 이동, no-logging 적재이다.

저장 정책 검증에는 NULL·빈 값·작은 값, FORCE_OUTLINE, 큰 컬럼 우선 선택, 50,000바이트의 4개 조각 저장을 포함한다. 오류를 무시하는 테스트는 거절된 중복 행의 OOS 조각이 남지 않고 다음 정상 행이 커밋되는지 확인한다.

### 호환성과 범위

[PR #7695](https://github.com/CUBRID/CUBRID/pull/7695)의 `eaf1165bbc76d5f22b6ff34f08ccd8deca0c11b4`에서 동일한 추가·삭제 코드와 동일한 테스트를 별도 빌드 및 새 DB로 실행했다. 이는 빌드와 집중 회귀 검증 결과이며, 해당 PR의 전체 테스트나 CI 결과를 뜻하지 않는다.

이 변경은 OOS 참조의 디스크 형식이나 크기 선택 기준을 바꾸지 않는다. 현재 기준 브랜치의 16바이트 참조와 PR #7695의 identity stamp 변경은 각각 유지했다. no-logging은 성공한 적재와 읽기를 검증했으며, 실패 후 복구나 식별자 유일성을 새로 보장하지 않는다.

기존 외부 LOB 검증은 다른 컬럼을 OOS로 분리하면서 BLOB/CLOB 내용, 파일 이름, 파일 바이트가 롤백·커밋 후 유지되는지 확인한다. LOB locator 자체를 OOS로 분리하는 모든 조합을 검증한 것은 아니다. 새 외부 LOB를 workspace INSERT로 만들 때의 별도 기존 결함은 수정 범위에 포함하지 않았다.


