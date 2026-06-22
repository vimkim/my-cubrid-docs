# [CBRD-26912] STORAGE PREFER_INLINE — 컬럼별 OOS 회피 우선순위

- JIRA: https://jira.cubrid.org/browse/CBRD-26912
- 대상 브랜치: `feat/oos`
- 종류: Improve (Function / Performance)

## Description

### OOS 가 무엇을 하는가

CUBRID 는 한 행(row)을 하나의 heap 레코드로 디스크에 저장하고, 레코드는 고정 크기 페이지(`DB_PAGESIZE`, 보통 16KB) 안에 담는다. 레코드가 너무 커지면 작은 컬럼 하나를 읽을 때도 큰 덩어리를 통째로 읽어야 해서 불필요한 디스크 I/O 가 생긴다.

OOS(Out-of-row Storage — 큰 가변 컬럼 값을 별도 파일로 떼어 저장하는 방식)는 이때 큰 가변 컬럼의 값을 OOS 파일로 떼어내고(이 동작을 demote 라 부른다), 레코드에는 그 값을 가리키는 16바이트짜리 OOS stub 만 남긴다. 이 stub 은 OOS OID(8바이트, 값이 저장된 OOS 위치) + 길이(8바이트)로 이루어진다(`OR_OOS_INLINE_SIZE = OR_OID_SIZE(8) + OR_BIGINT_SIZE(8) = 16`). 값이 레코드 안에 그대로 있으면 "인라인", OOS 파일로 떼어내면 "OOS" 상태다.

어떤 컬럼을 떼어낼지는 `heap_attrinfo_determine_disk_layout` (`src/storage/heap_file.c`) 가 정한다.

### 지금까지의 문제 — 고를 기준이 "크기" 하나뿐

기존 정책은 단순했다.

1. 레코드 총 길이가 `DB_PAGESIZE/4` (16KB 페이지에서 4KB) 이하면 아무것도 떼지 않는다.
2. 넘으면, 가변 컬럼 중 값이 `OR_OOS_INLINE_SIZE`(= OOS stub 크기, 16바이트)보다 큰 것을 후보로 모은다. stub 보다 작은 값은 떼어내도 레코드가 줄지 않으므로 제외한다.
3. 후보를 **크기 내림차순**으로 정렬해(`std::greater<std::pair<int,int>>`), 레코드가 `DB_PAGESIZE/4` 안에 들어올 때까지 큰 것부터 하나씩 demote 한다.

고르는 기준이 크기뿐이라, 자주 읽는(hot) 큰 컬럼이라도 크기만 크면 가장 먼저 OOS 로 빠진다. 그 컬럼을 읽을 때마다 `oos_read`(OOS 파일에서 값을 가져오는 추가 디스크 읽기) 비용이 든다. 사용자가 "이 컬럼은 가능하면 인라인에 둬 달라"는 의사를 SQL 로 표현할 방법이 없었다.

### 제안 — PostgreSQL TOAST 의 MAIN 에 대응하는 컬럼 힌트

PostgreSQL TOAST 의 `ALTER TABLE ... SET STORAGE MAIN`("가능하면 인라인 유지")에 대응하는 컬럼 옵션 `STORAGE PREFER_INLINE` 을 추가한다. PostgreSQL `STORAGE` 에는 압축 의미가 섞여 있지만(CUBRID OOS 에는 압축 개념이 없다), 여기서는 OOS demote 우선순위에만 한정해 두 값으로 정의한다.

```sql
CREATE TABLE t (
  id       INT,
  hot      BIT VARYING STORAGE PREFER_INLINE,  -- OOS 후순위: 가능하면 인라인 유지
  cold     BIT VARYING STORAGE DEFAULT          -- 현행 동작 (생략과 동일)
);

ALTER TABLE t MODIFY hot  BIT VARYING STORAGE DEFAULT;        -- 힌트 해제
ALTER TABLE t MODIFY cold BIT VARYING STORAGE PREFER_INLINE;  -- 힌트 부여
```

### 동작 정의 (전부 soft)

demote 는 레코드가 `DB_PAGESIZE/4` 를 넘을 때만 일어난다. `PREFER_INLINE` 은 "demote 를 할지 말지"가 아니라 "demote 한다면 어떤 컬럼부터 할지"의 **순서**만 바꾼다.

- `STORAGE DEFAULT`(또는 옵션 생략): 현행대로 크기 내림차순.
- `STORAGE PREFER_INLINE`: 해당 컬럼을 후보 정렬의 **맨 뒤**로 보낸다. 다른 후보를 모두 OOS 로 보내고도 레코드가 `DB_PAGESIZE/4` 안에 안 들어오면, 그제야 마지막 수단으로 이 컬럼을 demote 한다.

PREFER_INLINE 컬럼도 끝까지 후보로 남기 때문에 "레코드는 항상 페이지에 들어간다"는 기존 OOS 불변식이 깨지지 않는다. 이것이 soft 인 이유다.

### soft 방식의 한계 (의도된 범위)

- **떼어낼 다른 컬럼이 없으면 효과가 없다.** 큰 가변 컬럼이 하나뿐인 레코드에서 그 컬럼에 PREFER_INLINE 을 걸어도, 레코드가 `DB_PAGESIZE/4` 를 넘으면 결국 그 컬럼이 OOS 로 간다.
- **모든 가변 컬럼이 PREFER_INLINE 이면 DEFAULT 와 같다.** 후보가 전부 같은 우선순위(맨 뒤)에 모이면 그들끼리 다시 크기순으로 정렬되므로 결과가 현행과 같아진다. 힌트는 일부 컬럼만 PREFER_INLINE 일 때 의미가 있다.
- **공짜 이득이 아니라 비용의 이동이다.** hot 컬럼을 보호하면 그만큼 다른 컬럼이 대신 OOS 로 가고, `oos_read` I/O 가 그쪽으로 옮겨간다. 보호 대상이 더 자주 읽힐 때에만 전체적으로 이득이다.

## Implementation

`INVISIBLE` 컬럼 옵션이 이미 "PT 노드 → `SM_ATTRIBUTE.flags` 비트 → `OR_ATTRIBUTE` 비트필드 → 소비" 라는 똑같은 경로를 거치므로, 그 선례를 그대로 따랐다. 카탈로그 disk 포맷과 시스템 테이블 컬럼은 바뀌지 않는다(플래그 정수 안의 빈 비트 하나만 쓴다).

### 데이터 흐름

```
[파서]   STORAGE PREFER_INLINE  (client-side: libcubridcs.so)
   csql_lexer.l  : STORAGE / PREFER_INLINE 토큰을 렉싱하는 flex 규칙
   csql_grammar.y: column_storage_def 규칙
        -> PT_ATTR_DEF.info.attr_def.attr_storage = PT_ATTR_STORAGE_PREFER_INLINE
[스키마] execute_schema.c
   CREATE : do_add_attribute           -> att->flags |= SM_ATTFLAG_OOS_PREFER_INLINE
   ALTER  : build_attr_change_map      -> P_OOS_PREFER_INLINE 변경 추적 (GAINED/LOST/UNCHANGED)
            do_change_att_schema_only  -> found_att->flags 비트 set/clear
        -> SM_ATTFLAG_OOS_PREFER_INLINE (storage_common.h, 0x1000)
[직렬화] transform_cl.c (기존 코드, 수정 불필요)
   or_put_int(buf, att->flags) 로 flags 정수 전체를 쓰고 같은 방식으로 읽는다.
   0x1000 비트가 flush/재기동 후에도 살아남는다.
[복원]   object_representation_sr.c : or_get_current_representation  (server-side)
        -> att->oos_prefer_inline = (flags & SM_ATTFLAG_OOS_PREFER_INLINE) ? 1 : 0
[소비]   heap_file.c : heap_attrinfo_determine_disk_layout
   (!) demote 후보 정렬의 1차 키에 prefer_inline 을 추가 -> PREFER_INLINE 컬럼을 맨 뒤로
```

`(!)` 로 표시한 곳이 실제 정책이 바뀌는 유일한 지점이다. 나머지는 플래그를 끝까지 실어 나르는 배선이다.

### 변경 파일 (10개)

| File | Change |
|------|--------|
| `src/parser/csql_lexer.l` | `STORAGE`, `PREFER_INLINE` 의 flex 렉서 규칙 추가 (**필수**). 일반 식별자 규칙은 무조건 `IdName` 을 반환하므로, 키워드별 규칙이 없으면 토큰이 생기지 않고 파싱이 `syntax error` 로 실패한다. `<cptr>` 토큰이라 `csql_yylval.cptr = pt_makename(yytext)` 를 설정한다. |
| `src/parser/csql_grammar.y` | `%token <cptr> STORAGE`, `%token <cptr> PREFER_INLINE`. `COLUMN_CONSTRAINT_STORAGE (0x400)` define(파서가 컬럼 옵션 중복을 검사하는 일시적 마스크 — 아래 `SM_ATTFLAG_OOS_PREFER_INLINE 0x1000` 과는 무관한 별개 비트 공간이다). `column_storage_def` 규칙(`STORAGE PREFER_INLINE` / `STORAGE DEFAULT`)을 `column_constraint_and_comment_def` 에 추가. `identifier` 규칙에 두 키워드 echo 추가(빠뜨리면 `storage`/`prefer_inline` 식별자 스키마가 깨진다). |
| `src/parser/keyword.c` | `{STORAGE, "STORAGE", 1}`, `{PREFER_INLINE, "PREFER_INLINE", 1}` (세 번째 인자 1 = 비예약). `pt_is_reserved_word` 판정 테이블. |
| `src/parser/parse_tree.h` | `PT_ATTR_STORAGE_SETTING` enum(UNSET/DEFAULT/PREFER_INLINE) 추가. `pt_attr_def_info` 에 `attr_storage:2` 비트필드 추가(`attr_invisible:2` 와 동일 패턴). |
| `src/parser/parse_tree_cl.c` | `pt_print_attr_def` 에 PREFER_INLINE 출력 블록 추가(SHOW CREATE / unloaddb 라운드트립). |
| `src/storage/storage_common.h` | `SM_ATTFLAG_OOS_PREFER_INLINE = 4096 (0x1000)` 추가(다음 빈 비트). |
| `src/query/execute_schema.c` | CREATE 경로(`do_add_attribute`): PT 값이 PREFER_INLINE 이면 플래그 set. `att` 포인터가 앞 단계(예: auto_increment 처리)에서 이미 잡혀 있을 수 있어 `if (att == NULL)` 일 때만 `smt_find_attribute` 로 찾은 뒤 `att->flags |= SM_ATTFLAG_OOS_PREFER_INLINE`. ALTER 변경 추적 슬롯 `P_OOS_PREFER_INLINE` 추가 후 `build_attr_change_map`(detect) + `do_change_att_schema_only`(apply) 에서 GAINED/LOST/UNCHANGED 처리. |
| `src/base/object_representation_sr.h` | `OR_ATTRIBUTE` 에 `unsigned oos_prefer_inline:1;` 추가(`is_invisible:1` 옆). 생성자 memset 범위라 기존 테이블은 0 으로 자동 초기화. |
| `src/base/object_representation_sr.c` | `or_get_current_representation` 에서 플래그 비트를 `oos_prefer_inline` 로 복원하는 한 줄. |
| `src/storage/heap_file.c` | demote 후보 정렬 키 변경(아래). |

### 정렬 키 변경 (핵심)

기존:

```cpp
std::vector<std::pair<int, int>> oos_candidates;  /* {column_size, attr index} */
...
std::sort (oos_candidates.begin (), oos_candidates.end (), std::greater<std::pair<int, int>> ());
```

변경 후 — 후보에 `prefer_inline` 플래그를 함께 담고 이를 1차 정렬 키로 쓴다:

```cpp
struct oos_cand { int prefer_inline; int size; int idx; };  /* prefer_inline: 0=일반, 1=후순위 */
std::vector<oos_cand> oos_candidates;
...
if (!attr_info->values[i].last_attrepr->is_fixed && column_size[i] > OR_OOS_INLINE_SIZE)
  {
    int prefer_inline = attr_info->values[i].last_attrepr->oos_prefer_inline ? 1 : 0;
    oos_candidates.push_back ({ prefer_inline, column_size[i], i });
  }
...
std::sort (oos_candidates.begin (), oos_candidates.end (),
           [] (const oos_cand &a, const oos_cand &b) {
             if (a.prefer_inline != b.prefer_inline)
               return a.prefer_inline < b.prefer_inline;  /* 일반(0) 먼저, 후순위(1) 뒤로 */
             if (a.size != b.size)
               return a.size > b.size;                     /* 같은 등급 안에서는 큰 것 먼저 */
             return a.idx > b.idx;                          /* 크기 동률이면 idx 내림차순 */
           });
```

`idx` 내림차순 tiebreak 는 **회귀 방지를 위해 반드시 필요**하다. 기존 `std::greater<std::pair<int,int>>` 는 `{크기, idx}` 를 크기·idx 순으로 비교해 크기가 같아도 결정적 순서를 보장했다. `std::sort` 는 stable 정렬이 아니므로 idx 키를 빼면 크기가 같은 두 컬럼의 demote 순서가 빌드/STL 버전에 따라 달라져 회귀 테스트가 flaky 해진다. idx 키를 넣으면 PREFER_INLINE 미지정(DEFAULT) 컬럼만 있을 때 정렬 순서가 기존과 비트 단위로 동일해진다.

demote 루프와 후보 자격 필터는 그대로 둔다. PREFER_INLINE 컬럼도 후보로 남으므로(soft) 마지막 수단으로는 결국 demote 될 수 있다.

### ALTER 의 적용 시점 (사용자 가시 동작)

- `ALTER ... STORAGE PREFER_INLINE` 은 **그 이후의 INSERT/UPDATE 부터** 적용된다. 이미 OOS 로 나가 있는 기존 값은 ALTER 만으로 인라인으로 돌아오지 않는다(PostgreSQL `SET STORAGE` 와 동일). 소급 재배치는 후속 이슈.
- `ALTER ... MODIFY` 에서 `STORAGE` 절을 **생략하면 기존 힌트가 그대로 보존된다**. PT 계층은 3상태 enum(UNSET/DEFAULT/PREFER_INLINE)을 쓰고, UNSET(절 생략)이면 `build_attr_change_map` 이 `ATT_CHG_PROPERTY_UNCHANGED` 로 표시해 `do_change_att_schema_only` 가 기존 비트를 건드리지 않는다(`INVISIBLE` 의 change-map 방식). 명시적으로 되돌리려면 `STORAGE DEFAULT` 를 적는다.

### 라운드트립

저장 계층은 단일 비트(`oos_prefer_inline`)만 쓰므로 `STORAGE DEFAULT` 와 "절 생략" 은 **저장 시점**에 모두 비트 0 으로 같은 상태가 된다(의도된 동작). 그래서 `pt_print_attr_def` 는 비트가 1 일 때만 ` storage prefer_inline ` 을 출력하고 DEFAULT/생략은 아무것도 출력하지 않는다. 즉 라운드트립으로 보존되는 대상은 PREFER_INLINE 뿐이다. (둘이 같아지는 것은 저장 계층 한정이다 — PT 계층에서는 UNSET ≠ DEFAULT 이며, ALTER MODIFY 에서 생략(UNSET)은 기존 비트를 보존하고 명시적 `DEFAULT` 는 비트를 해제한다. 위 "ALTER 의 적용 시점" 참고.)

## Remarks

이 PR 의 범위는 **파싱 → 플래그 저장 → demote 동작 변경** 의 핵심 파이프라인이다. 아래는 이번 범위에서 **제외**했고 후속으로 분리한다.

- **시맨틱 검증 미포함**: OOS 대상이 될 수 없는 자리(진짜 고정 타입 컬럼, 뷰 VCLASS 컬럼)에 힌트를 붙여도 현재는 **거부하지 않고 받아들인 뒤 무시(inert)** 한다. 고정 타입 컬럼은 애초에 demote 후보 필터(`!is_fixed`)에서 걸러지므로 동작에는 영향이 없다. `semantic_check.c` 에서의 명시적 거부는 후속 작업이다. 또한 `STORAGE` 뒤에 `PREFER_INLINE`/`DEFAULT` 이외의 토큰(예: `EXTENDED`)을 쓰면 — 그 토큰을 따로 인식하는 경로가 없으므로 — 일반 bison `syntax error` 가 난다. `STORAGE` 전용의 읽기 쉬운 에러 메시지도 후속 작업이다. (`CHAR` 는 `CBRD-26663` 이후 가변 타입이라 정상적으로 보호 대상이 된다.)
- **catalog `_db_attribute.flags` 미노출**: `catcls_filter_attflag`(`src/storage/catalog_class.c`) 매핑과 `DB_ATTRIBUTE_OPTION_TYPE` 멤버를 추가하지 않았다. 플래그 기본값이 0 이라 기존 행/DEFAULT 컬럼의 카탈로그는 그대로이고, 나중에 무중단으로 추가할 수 있다. 배치 검증은 카탈로그 없이 `oos.log` 로 한다(아래 Test Plan).
- **hard 강제 미포함**: 컬럼을 절대 OOS 로 안 보내는 강제(`FORCE_INLINE` 등)는 overflow page 경로와의 상호작용 검증이 따로 필요해 제외한다.
- **소급 재배치 미포함**: ALTER 시 기존 데이터를 즉시 재배치하지 않는다.

기타:

- 파서/렉서는 클라이언트측(`libcubridcs.so`, `csql` 가 dlopen)에서 돌고, demote/플래그 복원 코드는 서버측(`cub_server`)에서 돈다.
- OOS-CONTEXT 문서의 옛 임계치(`DB_PAGESIZE/8`, 512B)는 폐기된 값이다. 실제 코드는 `DB_PAGESIZE/4` 와 `OR_OOS_INLINE_SIZE`(16B)를 쓴다.

## Test Plan

debug 빌드에서 검증했다. `DISK_SIZE()` 는 논리적 값 크기만 돌려줘 OOS 여부를 구분하지 못하므로, 배치는 debug 빌드의 `$CUBRID/log/oos.log` 에 찍히는 `oos_insert ... src.size=` 로 어느 컬럼이 demote 됐는지 확인한다(release 빌드에는 컬럼별 OOS 가시성이 없다 — CBRD-26871).

**1) 배치(placement) — 핵심 discriminating test.** 더 큰 컬럼을 PREFER_INLINE 으로 보호하면 더 작은 컬럼이 대신 demote 되어야 한다(크기순 기본 정책과 정반대 결과).

```sql
CREATE TABLE demo  (id INT, hot BIT VARYING STORAGE PREFER_INLINE, cold BIT VARYING);
CREATE TABLE demo2 (id INT, hot BIT VARYING,                       cold BIT VARYING);
INSERT INTO demo  VALUES (1, CAST(REPEAT('AA',3000) AS BIT VARYING), CAST(REPEAT('BB',2000) AS BIT VARYING));
INSERT INTO demo2 VALUES (1, CAST(REPEAT('AA',3000) AS BIT VARYING), CAST(REPEAT('BB',2000) AS BIT VARYING));
```

- 결과: `demo` 는 `src.size=2008`(작은 cold 가 demote, 큰 hot 은 인라인 보호) — **기대대로**.
- `demo2` 는 `src.size=3008`(큰 hot 이 demote, 현행 크기순) — **회귀 없음**.

**2) 값 정합성.** 인라인이든 OOS 든 값은 같아야 한다.

```sql
CREATE TABLE t (id INT, a BIT VARYING STORAGE PREFER_INLINE, b BIT VARYING);
INSERT INTO t VALUES (1, CAST(REPEAT('AA',1500) AS BIT VARYING), CAST(REPEAT('BB',1500) AS BIT VARYING));
SELECT (a = CAST(REPEAT('AA',1500) AS BIT VARYING)) AS a_ok,
       (b = CAST(REPEAT('BB',1500) AS BIT VARYING)) AS b_ok FROM t WHERE id = 1;
-- a_ok=1, b_ok=1  (검증됨)
```

**3) 파싱/스키마.** `CREATE TABLE` 컬럼 옵션과 `ALTER TABLE MODIFY ... STORAGE PREFER_INLINE | DEFAULT` 가 정상 파싱·반영된다(검증됨).

**4) 고정 타입 — accepted-inert.** 고정 타입 컬럼에 붙여도 에러 없이 통과하고 동작에 영향이 없다(현재 동작; 거부 검증은 후속). 검증됨.

**5) 식별자 호환.** `storage` 를 컬럼/식별자로 쓰는 기존 쿼리가 깨지지 않는다(예: `SELECT ... AS storage`). 검증됨.

**6) 통과해야 할 회귀.** 기존 OOS insert/select/update/delete, 크래시 복구, 복제 테스트.
