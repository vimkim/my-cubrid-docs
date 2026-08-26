# CUBRID에서 이해하는 x86-64 Copy-and-Patch JIT

> 대상 독자: 컴파일러와 DBMS 수업을 들은 대학 4학년 수준의 개발자
>
> CUBRID 소스 기준: `95b79e7eda79da8f16f301dc50bd5362cd2f19cf`
>
> 문서 목적: Copy-and-Patch JIT가 무엇이며, CUBRID의 XASL 실행기에 어떻게 적용할 수 있는지 쉽게 설명한다.

## 1. 먼저 결론

- Copy-and-Patch JIT는 Rust 전용이 아니다. x86-64 Linux의 C++에서도 구현할 수 있다.
- CUBRID의 XASL을 바로 없애는 기술은 아니다.
- 현실적인 첫 적용 대상은 XASL 안의 `PRED_EXPR` 조건식 평가이다.
- CUBRID에는 이미 `SCAN_PRED::pr_eval_fnc`라는 함수 포인터가 있어서 기존 평가기와 JIT 평가기를 선택하기 좋은 지점이 있다.
- 성공하면 각 행마다 반복되는 트리 탐색, 타입 분기, 함수 호출의 일부를 쿼리 전용 기계어로 바꿀 수 있다.
- 단, SQL의 NULL, 타입 변환, collation, 오류 처리까지 기존 실행기와 완전히 같은 결과를 내야 한다.

한 문장으로 표현하면 다음과 같다.

> XASL은 실행 계획으로 남겨 두고, 그중 자주 반복되는 계산만 x86-64 전용 함수로 미리 구워서 실행한다.

### 이 문서에서 자주 쓰는 용어

| 용어 | 뜻 |
|---|---|
| Predicate | `WHERE b = 10`처럼 참·거짓·UNKNOWN을 계산하는 조건식 |
| Expression | `a + 1`처럼 값을 계산하는 식 |
| Host variable | SQL의 `?`처럼 실행할 때 값이 정해지는 입력 변수 |
| Fallback | JIT가 지원하지 않는 경우 기존 실행기로 돌아가는 것 |
| Pipeline | Scan, Filter, Projection 등 연속된 실행 단계를 하나의 흐름으로 처리하는 것 |
| JIT artifact | 생성한 기계어와 그 메모리·수명 정보를 묶은 실행 결과물 |
| XASL clone | 캐시된 XASL을 실제 실행에 사용하기 위해 복원한 실행용 복제본 |

## 2. JIT는 무엇인가?

JIT는 **Just-In-Time compilation**의 약자다. 프로그램이 실행되는 도중에 새로운 기계어 함수를 만들어 실행하는 기술이다.

일반적인 DB 실행기는 다음과 같은 코드를 모든 행에 반복한다.

```text
현재 노드 종류 확인
  → 왼쪽 피연산자 계산
  → 오른쪽 피연산자 계산
  → 타입 확인
  → 비교 함수 선택
  → 다음 노드로 이동
```

JIT는 쿼리가 준비될 때 조건식의 모양을 확인한 뒤, 그 조건식만 실행하는 기계어를 만든다.

```text
b 컬럼 로드
  → NULL이면 UNKNOWN
  → 정수 10과 비교
  → 결과 반환
```

두 방식은 같은 답을 내지만, JIT 쪽은 실행 중에 “무슨 연산을 해야 하지?”라고 계속 판단하지 않는다. 쿼리를 준비할 때 이미 그 답을 기계어에 넣었기 때문이다.

## 3. Copy-and-Patch는 무엇인가?

LLVM 같은 범용 컴파일러는 다음과 같은 일을 한다.

```text
중간 표현 생성
  → 최적화
  → 명령어 선택
  → 레지스터 할당
  → 기계어 생성
```

좋은 코드를 만들 수 있지만, DB 쿼리 실행 직전에 수행하기에는 컴파일 비용이 클 수 있다.

Copy-and-Patch는 자주 사용하는 기계어 조각을 미리 준비한다. 이 조각을 **스텐실(stencil)**이라고 부른다.

예를 들어 `정수 컬럼 > 상수` 스텐실은 개념적으로 다음과 같다.

```text
정수 컬럼을 ??? 위치에서 로드
NULL이면 UNKNOWN으로 이동
??? 상수와 비교
크면 TRUE, 아니면 FALSE
```

JIT 컴파일 시점에는 물음표만 채운다.

```text
컬럼 위치  → b 컬럼의 실제 위치
비교 상수  → 10
분기 위치  → TRUE/FALSE 처리 코드의 주소
```

즉, 런타임 컴파일 과정이 복잡한 최적화보다 다음 작업에 가까워진다.

```text
스텐실 복사 + 상수와 주소 패치 + 스텐실 연결
```

이 때문에 아주 짧은 시간 안에 코드를 만들 수 있다. 다만 원문이 말하는 약 5μs는 pgrust JIT에 대한 주장이고, 원문의 표는 장난감 정규식의 **실행 시간**을 측정한 것이다. 그 표만으로 5μs의 컴파일 시간을 독립적으로 검증할 수는 없다.

## 4. x86-64의 C++에서도 가능한가?

가능하다. 필요한 것은 Rust가 아니라 다음 네 가지다.

1. x86-64 명령어를 byte 단위로 만들 수 있어야 한다.
2. 코드를 쓸 수 있는 메모리를 운영체제에서 할당해야 한다.
3. 쓰기가 끝난 메모리를 실행 가능하게 바꿔야 한다.
4. 그 메모리 주소를 C++ 함수 포인터로 호출해야 한다.

Linux에서는 대체로 다음 순서를 사용한다.

```text
mmap(RW)
  → 기계어 복사 및 패치
  → mprotect(RX)
  → 함수 포인터로 호출
  → 더 이상 필요 없으면 munmap
```

여기서 `RW`는 읽기/쓰기, `RX`는 읽기/실행 권한이다. 쓰기와 실행 권한을 동시에 오래 열지 않는 원칙을 **W^X(Write XOR Execute)**라고 한다.

ARM64 예제와 다른 점도 있다.

| 구분 | ARM64 | x86-64 |
|---|---|---|
| 명령어 길이 | 대부분 고정 4바이트 | 1바이트부터 여러 길이까지 가변 |
| 스텐실 저장 | `uint32_t` 배열이 편리 | byte 배열이 편리 |
| 분기 패치 | 명령어 bit field 수정 | 주로 `rel32` 변위 수정 |
| 명령 캐시 | 플랫폼에 따라 명시적 flush 필요 | 일반적인 x86 환경에서는 I/D cache가 일관적이지만 플랫폼 인터페이스는 지키는 편이 안전 |

C++ 스텐실은 개념적으로 다음처럼 표현할 수 있다.

```cpp
struct patch_point
{
  std::size_t offset;
  enum class kind { immediate, relative_branch, helper_address } type;
};

struct stencil
{
  const std::byte *code;
  std::size_t size;
  std::vector<patch_point> patches;
};
```

실제 구현에서는 직접 opcode를 작성할 수도 있고, 별도의 빌드 단계에서 C/C++ 스텐실을 컴파일한 뒤 object file의 코드와 relocation 정보를 추출할 수도 있다. 후자가 명령어를 일일이 손으로 관리하는 부담을 줄여 준다.

## 5. XASL은 SQL AST인가?

완전히 같은 개념은 아니다.

SQL AST는 사용자가 입력한 SQL 문법 구조에 가깝다.

```text
SELECT
  ├─ 출력식: a + 1
  ├─ FROM: t
  └─ WHERE: b = 10
```

XASL은 최적화가 끝난 뒤 서버가 실행할 수 있도록 만든 실행 계획에 가깝다.

```text
SQL Parse Tree
  → 의미 분석
  → Query Optimizer
  → XASL 생성
  → XASL stream 직렬화
  → 서버에서 unpack
  → Query Executor 실행
```

`XASL_NODE`에는 다음과 같은 정보가 들어 있다.

- `BUILDLIST_PROC`, `BUILDVALUE_PROC`, `HASHJOIN_PROC`, `UPDATE_PROC` 등의 실행 노드 종류
- 테이블 또는 인덱스 접근 방법을 표현하는 access spec
- predicate와 출력 expression
- 하위 XASL과 correlated subquery
- LIMIT, 정렬, 집계, DML 관련 정보
- XASL cache와 실행 상태 관련 정보

소스는 [`src/query/xasl.h`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/xasl.h#L1116)에서 확인할 수 있다.

따라서 XASL 전체를 없애면 단순한 expression evaluator뿐 아니라 스캔, 조인, MVCC, 잠금, list file, 오류 처리, 캐시까지 다시 설계해야 한다.

## 6. 그렇다면 JIT는 XASL의 무엇을 바꾸는가?

다음 세 단계로 나눠 생각하면 쉽다.

| 단계 | JIT 대상 | XASL의 역할 |
|---|---|---|
| 1단계 | Predicate와 단순 expression | 실행 계획과 스캔을 계속 담당 |
| 2단계 | Scan → Filter → Projection pipeline | 계획, 메타데이터, 캐시와 fallback 담당 |
| 3단계 | XASL main block 대부분 | JIT 입력 IR 및 실행 관리 정보로 남음 |

첫 구현으로는 1단계가 적절하다. 효과를 측정하기 쉽고 기존 실행기를 fallback으로 유지할 수 있기 때문이다.

## 7. CUBRID의 현재 predicate 실행 흐름

CUBRID 서버는 XASL stream을 풀어 `XASL_NODE`를 복원하고 실행한다.

```text
stx_map_stream_to_xasl()
  → qexec_execute_query()
  → qexec_execute_mainblock()
  → scan manager
  → eval_data_filter()
  → SCAN_PRED::pr_eval_fnc(...)
```

관련 소스는 다음과 같다.

- XASL stream 복원: [`query_manager.c`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/query_manager.c#L1214)
- 최상위 실행 진입: [`query_executor.c`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/query_executor.c#L17097)
- main block 실행: [`query_executor.c`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/query_executor.c#L15664)
- predicate 함수 선택: [`query_evaluator.c`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/query_evaluator.c#L2590)
- data filter 평가: [`query_evaluator.c`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/query_evaluator.c#L2907)
- scan 중 함수 포인터 호출: [`scan_manager.c`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/scan_manager.c#L7184)

특히 `SCAN_PRED`에는 이미 다음 함수 포인터가 있다.

```cpp
typedef DB_LOGICAL (*PR_EVAL_FNC) (
  THREAD_ENTRY *thread_p,
  const PRED_EXPR *predicate,
  VAL_DESCR *values,
  OID *object_oid);
```

정확한 typedef와 `SCAN_PRED` 구조는 [`query_evaluator.h`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/query_evaluator.h#L59)에서 확인할 수 있다.

현재는 `eval_pred()` 또는 조금 더 특화된 `eval_pred_comp0()` 같은 기존 C/C++ 함수가 들어간다. JIT가 성공하면 여기에 생성된 x86-64 함수의 주소를 넣을 수 있다.

```text
지원하는 predicate
  → pr_eval_fnc = jit_generated_function

지원하지 않는 predicate
  → pr_eval_fnc = 기존 eval_pred 계열
```

이 지점이 좋은 이유는 scan manager가 JIT 내부 구현을 몰라도 되기 때문이다. 호출자는 지금처럼 함수 하나만 호출하고, 복잡한 코드 생성과 메모리 관리는 JIT 모듈 안에 숨길 수 있다.

## 8. 실제 SQL을 어떻게 컴파일하는가?

다음 쿼리를 생각해 보자.

```sql
SELECT a + 1
FROM t
WHERE b = 10 AND c < ?;
```

`?`는 실행할 때 전달되는 host variable이다.

### 기존 평가 방식

각 행마다 대략 다음 과정을 수행한다.

```text
AND 노드인지 확인
  → b를 나타내는 REGU_VARIABLE 평가
  → 정수 상수 10 평가
  → 비교 연산 종류 확인
  → b = 10 계산
  → FALSE면 short-circuit
  → c를 나타내는 REGU_VARIABLE 평가
  → host variable 위치 확인
  → c < ? 계산
  → 3-valued AND 계산
```

실제 `eval_pred()`도 `PRED_EXPR`를 순회하고, 피연산자를 얻기 위해 `fetch_peek_dbval()`을 호출한다. 각각 [`query_evaluator.c`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/query_evaluator.c#L1666)와 [`fetch.h`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/fetch.h#L43)에서 볼 수 있다.

### JIT 평가 방식

쿼리 준비 단계에서 predicate 구조를 한 번 읽고 다음 모양의 기계어를 만든다.

```text
b의 DB_VALUE 주소 로드
  → NULL이면 UNKNOWN 경로
  → 정수 10과 비교
  → 같지 않으면 FALSE 반환

c의 DB_VALUE 주소 로드
  → NULL이면 UNKNOWN 경로
  → VAL_DESCR에서 host variable 로드
  → 정수 비교
  → TRUE/FALSE 반환
```

여기서 `b = 10`의 `10`은 코드에 직접 넣을 수 있지만, host variable은 실행마다 달라지므로 `VAL_DESCR`에서 읽어야 한다.

## 9. 제안하는 JIT 모듈

호출자가 기계어와 메모리 보호 규칙을 알 필요가 없도록 작은 interface 뒤에 숨긴다.

```cpp
class jit_predicate
{
public:
  using entry_fn = DB_LOGICAL (*) (
    THREAD_ENTRY *, const PRED_EXPR *, VAL_DESCR *, OID *);

  static std::unique_ptr<jit_predicate> compile (const PRED_EXPR &predicate);

  entry_fn entry () const;
  bool is_compiled () const;

  ~jit_predicate ();  // executable memory 해제
};
```

내부 구현은 다음을 책임진다.

```text
지원 여부 검사
  → 스텐실 선택
  → 전체 코드 크기와 분기 위치 계산
  → RW 메모리 할당
  → 스텐실 복사 및 패치
  → RX로 권한 전환
  → 함수 포인터 제공
  → 소멸 시 메모리 해제
```

실제 interface에는 컴파일 실패, fallback 이유, 코드 크기, CPU 기능 조건도 포함되어야 한다. 생성 코드에 AVX2 같은 명령어를 사용한다면 해당 CPU 기능을 확인해야 한다.

## 10. JIT 코드는 어디에 저장해야 하는가?

기계어 주소를 XASL stream에 넣으면 안 된다.

- 프로세스가 달라지면 주소가 달라진다.
- 서버를 재시작하면 주소가 무효가 된다.
- ASLR 때문에 같은 코드도 매번 다른 주소에 놓일 수 있다.
- executable memory는 서버 프로세스 안에서만 의미가 있다.

따라서 다음 수명 주기가 적절하다.

```text
XASL stream 수신 및 unpack
  → 서버에서 JIT 컴파일
  → XASL cache entry 또는 clone에 JIT artifact 연결
  → 여러 실행에서 재사용
  → plan invalidation 또는 clone 폐기 시 executable memory 해제
```

CUBRID의 XASL cache는 packed stream과 실행용 clone을 관리한다. 구조는 [`xasl_cache.h`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/xasl_cache.h#L59)에서 확인할 수 있다.

초기 프로토타입은 clone별로 컴파일하고 함께 해제하는 편이 단순하다. 이후 컴파일 비용과 메모리 사용량을 측정한 다음, 포인터를 코드에 직접 박지 않는 형태로 바꾸어 cache entry 단위 공유를 검토할 수 있다.

## 11. 처음 지원할 범위

첫 단계에서 모든 SQL expression을 지원하려 하면 프로젝트가 너무 커진다. 다음처럼 좁게 시작하는 편이 좋다.

### 지원 후보

- 타입: `INTEGER`, `BIGINT`, `DOUBLE`
- 비교: `=`, `!=`, `<`, `<=`, `>`, `>=`
- 논리: `AND`, `OR`, `NOT`
- NULL: `IS NULL`, SQL 3-valued logic
- 피연산자: 컬럼, 상수, host variable
- 실행 위치: heap/list scan의 data filter

### 초기 미지원 후보

- 문자열 collation과 codeset 변환
- 암시적 타입 변환
- `NUMERIC` precision/scale 연산
- 날짜와 timezone 연산
- 함수와 stored procedure
- subquery와 correlated subquery
- `LIKE`, 정규식, collection 연산

미지원 노드를 만나면 쿼리 전체를 실패시키는 것이 아니라 기존 evaluator를 사용한다.

```cpp
auto compiled = jit_predicate::compile (*predicate);
if (compiled && compiled->is_compiled ())
  {
    scan_pred.pr_eval_fnc = compiled->entry ();
  }
else
  {
    scan_pred.pr_eval_fnc = eval_fnc (thread_p, predicate, &type);
  }
```

## 12. 가장 중요한 것은 SQL 의미 보존이다

JIT의 첫 목표는 빠른 코드가 아니라 **기존 CUBRID와 같은 결과를 내는 코드**여야 한다.

예를 들어 C/C++의 `bool`만 사용하면 SQL NULL을 제대로 표현할 수 없다.

```sql
NULL = 10          -- UNKNOWN
FALSE AND NULL     -- FALSE
TRUE AND NULL      -- UNKNOWN
NULL IS NULL       -- TRUE
```

CUBRID predicate는 다음 결과를 구분한다.

```text
V_TRUE
V_FALSE
V_UNKNOWN
V_ERROR
```

이 밖에도 JIT는 다음 규칙을 보존해야 한다.

- 정수 overflow와 `NUMERIC` 정밀도
- 서로 다른 DB 타입 사이의 coercion
- 문자열 collation 및 codeset
- 오류가 발생했을 때 `THREAD_ENTRY`와 error manager 상태
- query interrupt와 transaction abort
- `DB_VALUE`의 소유권과 수명
- schema 변경에 따른 plan invalidation

따라서 복잡한 연산은 처음부터 직접 구현하기보다 기존 CUBRID helper 함수를 호출하는 스텐실로 시작할 수 있다. 그 후 profiler로 비용이 큰 helper만 하나씩 특화한다.

## 13. 어떻게 정확성을 검증할까?

가장 중요한 테스트는 **differential test**다.

같은 `PRED_EXPR`와 입력을 기존 evaluator와 JIT evaluator에 모두 넣고 결과를 비교한다.

```text
expected = eval_pred(predicate, values)
actual   = jit_function(predicate, values)

assert expected == actual
assert 기존 오류 코드 == JIT 오류 코드
```

테스트 입력에는 정상 값만 넣으면 안 된다.

- NULL 조합
- 타입의 최솟값과 최댓값
- 양수, 음수, 0
- NaN과 infinity
- 잘못된 타입 조합
- short-circuit 중 오른쪽에서 오류가 나는 조건
- host variable 타입이 실행마다 달라지는 경우

가능하다면 무작위로 expression과 `DB_VALUE`를 생성하여 기존 evaluator와 비교하는 fuzz/differential test를 추가한다.

## 14. 어떻게 성능을 측정할까?

JIT의 총효과는 다음 식으로 생각할 수 있다.

```text
총 절약 시간
  = 행당 절약 시간 × 평가한 행 수
    - JIT 컴파일 비용
    - executable memory 관리 비용
```

따라서 다음을 따로 측정해야 한다.

1. JIT eligibility 검사 시간
2. 기계어 생성 시간
3. `mmap`/`mprotect` 또는 arena 관리 시간
4. 기존 evaluator의 행당 실행 시간
5. JIT evaluator의 행당 실행 시간
6. 생성 코드 크기와 instruction cache 영향
7. XASL cache hit/miss에 따른 재사용 횟수

테이블이 작거나 predicate가 한 번만 실행되면 컴파일 비용을 회수하지 못할 수 있다. 반대로 수백만 행에 같은 조건을 적용한다면 행당 몇 ns의 차이도 큰 효과가 된다.

첫 벤치마크는 I/O를 최소화하고 predicate 비용을 드러내야 한다.

```sql
SELECT COUNT(*)
FROM large_memory_resident_table
WHERE int_col > ? AND bigint_col < ?;
```

그 후 실제 디스크 I/O, index scan, join이 포함된 workload에서 전체 쿼리 응답 시간이 얼마나 개선되는지 확인한다.

## 15. 구현 로드맵

### 단계 0: 비용 확인

- 현재 `eval_pred()`와 `fetch_peek_dbval()`의 호출 횟수와 시간을 측정한다.
- 실제 workload에서 predicate evaluation이 병목인지 확인한다.

### 단계 1: 최소 프로토타입

- x86-64 Linux 전용으로 시작한다.
- `INTEGER column op constant` 한 종류만 지원한다.
- 기존 함수와 differential test를 작성한다.
- 설정값으로 JIT를 끌 수 있게 한다.

### 단계 2: 실용적인 predicate

- host variable과 NULL을 지원한다.
- `AND`/`OR` short-circuit를 지원한다.
- XASL clone 수명에 JIT artifact를 연결한다.
- 컴파일 실패 시 기존 evaluator로 자동 fallback한다.

### 단계 3: Projection과 pipeline

- 단순 산술 projection을 추가한다.
- Scan → Filter → Projection을 한 함수로 합치는 것을 실험한다.
- tuple materialization과 함수 호출 감소 효과를 측정한다.

### 단계 4: 범위 확대 여부 결정

- 지원 스텐실 증가에 따른 유지보수 비용을 평가한다.
- 다른 CPU 아키텍처 지원 전략을 결정한다.
- 전체 XASL JIT가 필요한지, expression/pipeline JIT만으로 충분한지 판단한다.

## 16. 자주 생기는 오해

### “JIT를 넣으면 optimizer가 필요 없나?”

아니다. Optimizer는 어떤 인덱스와 join 순서를 사용할지 결정한다. JIT는 결정된 계획을 더 싸게 실행하도록 돕는다.

### “XASL을 기계어로 바꾸면 XASL은 삭제해도 되나?”

대부분의 경우 아니다. 캐시, 직렬화, plan invalidation, fallback, 디버깅을 위해 계획 표현은 계속 필요하다.

### “x86-64 코드를 만들면 모든 CPU에서 동작하나?”

아니다. ARM64에서는 다른 emitter가 필요하다. x86-64 안에서도 AVX2, AVX-512 사용 여부에 따라 CPU feature 검사가 필요하다.

### “Copy-and-Patch면 자동으로 빠른가?”

아니다. 컴파일은 매우 빨라질 수 있지만, 생성 코드가 `DB_VALUE` helper를 계속 많이 호출하거나 병목이 I/O와 locking이라면 전체 쿼리 성능은 거의 변하지 않을 수 있다.

## 17. 최종 그림

```text
                    ┌──────────────────────┐
SQL ── optimizer ──▶│         XASL         │
                    │ scan/join/agg/DML 계획 │
                    └──────────┬───────────┘
                               │
                    predicate 지원 여부 검사
                               │
                   ┌───────────┴───────────┐
                   │                       │
              JIT 지원 가능            JIT 미지원
                   │                       │
         x86-64 stencil 복사·패치       기존 eval_pred()
                   │                       │
                   └───────────┬───────────┘
                               │
                         scan manager 실행
```

핵심 설계는 XASL을 버리는 것이 아니라, 기존 실행기와 JIT 실행기를 같은 predicate 평가 지점에서 교체할 수 있게 하는 것이다. 그러면 작은 범위부터 실험하고, 정확성과 성능이 확인된 범위만 점진적으로 넓힐 수 있다.

## 참고 자료

- [JIT Compiling Code in 5μs](https://malisper.me/jit-compiling-code-in-5-us/)
- [Stanford Compilers Lab: Copy-and-Patch Compilation](https://compilers.stanford.edu/software/copy-and-patch/)
- [Copy-and-Patch Compilation 논문](https://arxiv.org/abs/2011.13127)
- [Linux `mmap(2)`](https://man7.org/linux/man-pages/man2/mmap.2.html)
- [Linux `mprotect(2)`](https://man7.org/linux/man-pages/man2/mprotect.2.html)
- [CUBRID `XASL_NODE`](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/xasl.h#L1116)
- [CUBRID predicate evaluator](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/query_evaluator.c#L1666)
- [CUBRID scan predicate call site](https://github.com/CUBRID/CUBRID/blob/95b79e7eda79da8f16f301dc50bd5362cd2f19cf/src/query/scan_manager.c#L7184)
