# CBRD-27785 읽기 최적화 발표 원고와 예상 답변

일반 행 읽기의 OOS 준비 비용을 어떻게 줄이고 기존 버퍼 수명 계약을 지켰는지 팀원에게 설명하는 원고다.
코드 해설은 `f1b99031c`에 고정한다. 핵심은 OOS 전용 준비의 분리와 기존 layout의 재사용이다.
과거 일반 heap 측정의 개선과 원댓글 전체 수치의 동일 재현 미확인을 함께 설명한다.

작성일과 수정일은 2026-10-31, Asia/Seoul이다. 관련 이슈는 [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785)다.
관련 PR은 [OOS 통합 #7990](https://github.com/CUBRID/cubrid/pull/7990)과 [성능 수정 #8299](https://github.com/CUBRID/cubrid/pull/8299)다.
현재 PR 전체나 이후 UPDATE 구현을 설명하는 문서는 아니다.

5분을 목표로 분량을 나눴지만 낭독 시간은 실측하지 않았다. 발표 시간은 확정된 제약이 아니다.
예상 질문은 팀원에게 답할 내용을 준비한 것이며, 학습자에게 퀴즈나 재답변 검사를 요구하지 않는다.

## 설명 대상과 자료

소스 저장소는 `CUBRID/CUBRID`다. 다음 revision을 서로 다른 역할로 사용한다.

| 역할 | 고정 commit |
| --- | --- |
| 코드 변경 전 feature | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 학습 소스 | `f1b99031c0402d521a785815f107be7a83b27717` |
| 해설서의 공유용 소스 링크 | `bcb900d1696756a120ec0a2b7885c212f71ebc07` |
| 성능 증가율의 분모인 통합 전 develop | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| 원문 SQL 재실행의 feature | `4408135c0833ec959da3590f12c14efa69610c7e` |

학습 소스와 공유용 revision의 `src`·`unit_tests`·`contrib`가 같다는 확인은
[해설서의 snapshot 기록](CBRD-27785-code-walkthrough_f1b99031c_codex.md#scope)에 있다.
이번 작성에서는 기존 해설과 보고서를 재사용하고 현재 학습 소스의 읽기 분기·정리를 대조했다.
새 빌드·DB 실행·성능 측정·CI는 수행하지 않았다.

## 발표 원고

아래 네 부분의 시간은 발표 분량을 잡기 위한 가안이다. 함수명과 상세 조건은 뒤의 예상 답변에서 찾는다.

### 일반 행에서도 공통 reader를 거친다, 약 45초

이번 변경은 OOS에 저장한 큰 값을 가져오지 않는 일반 행 읽기의 비용을 줄이는 작업입니다.
일반 정수나 inline 문자열도 공통 속성 reader를 거칩니다.
변경 전에는 이 reader가 OOS Resolve용 큰 지역 scratch 배열까지 가지고 있었습니다.

여기서 지역 배열 선언을 매번 malloc하거나 배열 전체를 초기화한다는 뜻으로 설명하면 안 됩니다.
소스의 배열 선언, 생성된 stack frame, 실행 instructions는 각각 확인해야 합니다.
이번에는 OOS 전용 준비를 실제 필요한 경로로 옮겼습니다.

### 실제 OOS 필드에서만 전용 준비를 한다, 약 1분 30초

수정 후 일반 정수와 inline 문자열은 큰 OOS scratch가 없는 scalar reader에서 bytes를 찾습니다.
실제 OOS 필드일 때만 별도 reader로 들어가 scratch를 준비하고 Resolve합니다.
여러 OOS 값을 함께 준비하는 grouped 상태도 별도 함수로 옮겼습니다.

record의 HAS_OOS는 요약 정보입니다. 그 행에 OOS 값이 있다는 뜻이지 요청한 모든 속성을 Resolve한다는 뜻은 아닙니다.
요청한 OOS 속성이 없으면 Resolve하지 않고, 하나면 scalar, 둘 이상이면 grouped 경로를 사용합니다.
이 선택 정책은 기존 정책을 유지한 것입니다.

inline 가변값의 위치를 찾는 작업도 줄였습니다.
기존 record layout에 있는 offset table과 offset 폭을 사용해 두 entry를 읽습니다.
layout cache를 새로 만든 것이 아니라 이미 계산한 정보를 더 사용한 변경입니다.

### Resolve 결과를 변환한 뒤 임시 bytes를 정리한다, 약 1분 15초

함수를 나눌 때는 임시 bytes의 수명을 함께 봐야 합니다.
Resolve 결과는 지역 scratch에 들어갈 수도 있고, 더 크면 heap buffer에 들어갈 수도 있습니다.
Resolve만 helper로 옮기고 지역 scratch 주소를 반환하면 호출자가 변환할 때 이미 수명이 끝난 bytes를 사용할 수 있습니다.

그래서 OOS reader 안에서 Resolve와 값 변환을 끝냅니다.
변환에는 COPY를 요청하고, heap buffer를 사용했다면 변환 결과를 받은 뒤 해제합니다.
grouped로 준비한 OOS 값도 공통 변환에 COPY를 요청한 뒤 payload를 정리합니다.

일반 값과 OOS 값은 기존 변환 함수를 공유합니다.
NULL·기본값·구 representation·pending owner 처리와 오류 시 임시 buffer 정리도 유지합니다.
inline bytes의 실제 참조와 복사 처리는 기존 type handler의 계약을 따릅니다.

### 관측 결과에는 비교 대상과 한계를 붙인다, 약 1분 30초

기존 측정은 메모리에 올라온 일반 heap 20만 행의 두 스캔입니다.
수정본의 서버 user-space instructions는 OOS 통합 전 develop보다 약 1.11%, 1.36% 많았습니다.
수정 전 feature와의 코드 diff 기준과 이 증가율의 분모는 다릅니다.
이 수치는 당시 재구성한 두 스캔의 결과입니다.

당시 두 스캔에 적용한 잠정 2% 범위에는 들어왔습니다.
SQL 경과 시간이 같은 비율로 줄었다거나, 최신 PR 전체가 성능 기준을 통과했다는 뜻은 아닙니다.
과거 측정에는 DB 문자셋 조건 누락과 테스트 빌드 옵션 차이도 남아 있습니다.

이후 별도로 원문 SQL을 재실행하면서 같은 바이너리라도 DB 문자셋에 따라 instructions가 달라지는 영향을 관측했습니다.
하지만 리뷰어의 실제 locale이나 원댓글 전체 수치의 동일 재현은 확인하지 못했습니다.
그 재실행은 이번 읽기 최적화 소스의 재측정도 아닙니다.
발표에서는 코드 구조, 과거 최적화 측정, 원문 SQL 재실행의 결론을 각각 해당 범위에서 설명하겠습니다.

## 발표 중 보여줄 기존 그림

원고의 함수 흐름은 기존 해설서의 그림으로 설명한다. 그림의 생략 조건과 근거도 해당 절에 있다.

| 발표 지점 | 그림과 설명 순서 |
| --- | --- |
| 전용 준비의 분리 | [변경 전후 실행 흐름](CBRD-27785-code-walkthrough_f1b99031c_codex.md#flows)을 열고 일반 정수, inline 문자열, 실제 OOS 값 순으로 따라간다. grouped OOS는 scalar reader를 거치지 않고 공통 변환으로 간다는 점을 덧붙인다. |
| 버퍼 수명 | [Resolve와 변환의 수명 그림](CBRD-27785-code-walkthrough_f1b99031c_codex.md#ownership)을 열고 scratch 준비, Resolve, COPY 요청, heap buffer 해제, 반환 순서로 설명한다. |

## 수치와 조건을 찾을 위치

아래는 기존 기록의 요약이다. 이번 작성에서 새 측정이나 원시 계수 재감사를 수행한 결과가 아니다.

| 근거 | 발표에서 말할 범위와 남은 조건 |
| --- | --- |
| [과거 일반 heap 측정](CBRD-27785-oos-read-performance_bcb900d_codex.md#remarks) | 20만 행의 좁은 스캔과 여러 컬럼 스캔이다. 서버 `instructions:u`를 계수했다. 실행당 20회 스캔, 질의별 2라운드의 각 5회에서 첫 실행을 제외했다. 수정본은 통합 전 develop 대비 정순 +1.106605%·+1.362198%, 역순 +1.107484%·+1.362450%였다. 최종 표본 범위가 중앙값의 0.009% 미만이고 warm scan의 I/O read가 0이었다고 기록돼 있다. |
| 과거 측정의 빌드·환경 | GCC 11.5.0, RelWithDebInfo, O2·NDEBUG 조건이다. 기능 측에는 `CUBRID_UNIT_TEST_ENABLED`가 있고 baseline에는 해당 OOS 테스트 코드가 없었다. DB 생성 locale과 실제 charset·collation은 누락됐다. scratch 분리·inlining·코드 배치 각각의 절감 기여율은 분해하지 않았다. 위 과거 보고서의 조건과 수치를 함께 인용한다. |
| [원문 SQL 재실행](CBRD-27785-reviewer-reproduction_4408135c_20261031_codex.md) | 통합 전 develop `4781495f0`와 feature `4408135c`를 비교한 별도 실험이다. UTF-8·ISO-8859-1을 나눠 4라운드씩 실행했다. 문자셋 영향은 관측했지만 원댓글 전체 수치의 동일 재현은 미확인이다. |
| [문자셋을 포함한 비교 조건](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md#charset-conditions) | source SHA, 빌드, 설정, DB 생성 locale, 실제 charset·collation, UPDATE 초기 상태와 누적 횟수, 실행 순서, 계수 경계를 함께 기록한다. 새 실험의 조건을 누락된 과거 측정에 소급하지 않는다. |

## 예상 팀원 질문에 대한 답변

### 큰 지역 배열을 옮겨 malloc 비용을 줄인 것인가?

지역 scratch 배열은 stack 저장 공간이며 선언 자체가 malloc은 아니다.
배열 전체를 매번 초기화한다는 증거도 아니다. 함수 안의 블록 위치만 바꿔 stack frame 축소를 보장할 수도 없다.
이번 변경은 OOS scratch와 grouped 준비 상태를 별도 함수로 옮기고 공통 경로의 inlining 조건도 바꿨다.
각 변경의 성능 기여율은 별도로 측정하지 않았다.
[공통 reader의 비용 설명](CBRD-27785-code-walkthrough_f1b99031c_codex.md#background)과 [inline 조건](CBRD-27785-code-walkthrough_f1b99031c_codex.md#change-inline)에 근거한다.

### scratch 주소를 반환하고 나중에 변환하면 안 되는가?

지역 scratch의 수명은 해당 함수가 반환할 때 끝난다.
그 주소를 반환한 뒤 bytes를 변환하면 수명이 끝난 저장 공간을 읽을 수 있다.
현재 OOS reader는 Resolve, COPY를 요청하는 변환, heap buffer 해제를 같은 함수 안에서 끝낸다.
[버퍼 수명](CBRD-27785-code-walkthrough_f1b99031c_codex.md#ownership)에 순서와 소스 근거가 있다.

### COPY를 요청하면 항상 malloc과 전체 bytes 복사가 일어나는가?

COPY 요청은 임시 OOS bytes를 빌린 포인터가 결과에 남지 않도록 하는 type handler의 기존 계약이다.
모든 타입이 같은 방식으로 할당하거나 복사한다는 뜻은 아니다.
inline record bytes에는 이 임시 OOS용 COPY 요청을 하지 않으며 실제 참조·복사는 기존 type handler를 따른다.
`oos_owned_buffer`도 heap 할당 여부만 뜻하지 않는다. scratch에 담긴 임시 OOS bytes에도 설정된다.
[수명과 COPY 표](CBRD-27785-code-walkthrough_f1b99031c_codex.md#ownership)에 근거한다.

### HAS_OOS가 있으면 행의 모든 OOS 값을 읽는가?

요청한 OOS 속성 수를 기준으로 선택한다.
0개면 Resolve가 없고, 1개면 scalar, 2개 이상이면 grouped Resolve를 적용한다.
전체 컬럼 수나 행에 저장된 전체 OOS 값 개수가 기준은 아니다.
HAS_OOS는 record 요약이고 IS_OOS는 개별 필드 flag다.
이 정책은 [기존 grouped 선택](CBRD-27785-code-walkthrough_f1b99031c_codex.md#change-dispatch)을 유지한다.

### layout cache와 grouped 처리를 이번에 새로 만든 것인가?

둘 다 기존에 있었다. 이번에는 grouped 준비 상태를 별도 함수에 두고,
가변값 위치 계산에서 기존 layout의 `var_table`과 `offset_size`를 더 사용한다.
collection·LOB는 물리 순서가 속성 순서와 다를 수 있으므로 가장 가까운 더 큰 offset을 찾는 기존 길이 계산도 유지한다.
[기존 layout](CBRD-27785-code-walkthrough_f1b99031c_codex.md#mental-model)과 [variable 위치 계산](CBRD-27785-code-walkthrough_f1b99031c_codex.md#change-variable)에 근거한다.

### lazy 읽기가 회귀 원인이었는가?

lazy는 필요할 때 속성을 읽도록 시점을 미루거나 불필요한 읽기를 생략하는 방식이다.
실제 읽을 때 공통 scalar reader를 사용하므로 이번 수정의 영향을 받는다.
lazy 선택 로직 자체가 회귀 원인으로 입증된 것은 아니다.
통합 전에도 lazy reader가 있었고 코드 변경 전후 lazy 함수 본문은 같았다는
[T08 보충 기록](CBRD-27785-teaching-progress_f1b99031c_codex.md#t08-lazy-읽기와-회귀-원인의-구분)을 따른다.

### 모든 값이 scalar reader를 통과하고 모든 scratch가 사라졌는가?

grouped로 준비한 OOS bytes는 scalar reader를 건너뛰고 공통 변환에 직접 전달된다.
같은 행의 나머지 속성은 scalar reader로 읽는다.
index-key 소비자는 변경된 필드 분류 계약을 사용하지만 자체 큰 scratch와 COPY·정리 순서는 유지한다.
[실행 흐름](CBRD-27785-code-walkthrough_f1b99031c_codex.md#flows)과 [index-key 범위](CBRD-27785-code-walkthrough_f1b99031c_codex.md#change-index)에 근거한다.

### NULL·구 representation·pending과 오류 정리는 어떻게 되는가?

기존 공통 변환과 default·fixed 분기를 유지한다. pending owner도 기존 Resolve 경로까지 전달한다.
Resolve 오류 시 준비한 heap buffer를 해제하고, 변환 오류가 나도 OOS reader에서 heap buffer를 정리한다.
grouped prefetch가 일부만 성공한 경우에는 준비된 payload를 정리한다.
[수명·오류·representation 계약](CBRD-27785-code-walkthrough_f1b99031c_codex.md#ownership)에 근거한다.
이는 코드 설명이며 이번 작성에서 오류 경로를 재실행한 결과는 아니다.

### 1.11%와 1.36%는 성능이 그만큼 좋아졌다는 뜻인가?

통합 전 develop 대비 남아 있는 instructions 증가율이다.
수정 전 feature 대비 절감률이나 SQL 경과 시간 단축률이 아니다.
코드 diff의 base는 `dcbf09e4f`, 증가율의 분모는 `4781495f0`다.
대상은 재구성한 일반 heap 스캔 두 건이며 원댓글의 8개 workload 전체로 확대할 수 없다.
[해설서의 성능 비교 기준](CBRD-27785-code-walkthrough_f1b99031c_codex.md#verification)을 따른다.

### 2% 안이면 최신 PR 전체의 성능 검증이 끝난 것인가?

당시 두 일반 heap 스캔에 적용한 잠정 기준이다.
리뷰어가 전체 PR의 허용치로 승인한 값이 아니며 UPDATE, 큰 값 읽기, I/O 이득까지 통과했다는 뜻도 아니다.
과거 빌드 옵션 차이와 문자셋 미기록 조건도 함께 밝힌다.
[수락 기준 문서](CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md)에서 적용 범위를 확인할 수 있다.

### 문자셋이 원댓글 수치와의 차이를 모두 설명하는가?

같은 바이너리와 SQL에서도 DB 문자셋이 instructions에 영향을 준 것은 관측했다.
하지만 리뷰어의 locale은 모르며, 전체 수치가 같아진 것도 아니다.
예를 들어 ISO-8859-1의 LENGTH 전체 변화율은 +44.18%로 원문의 +40.6%와 다르다.
작은 컬럼 UPDATE도 +175.81%로 원문의 +73.7%와 다르다.
가까운 첫 라운드만 골라 성공으로 말하거나 차이를 모두 시간 노이즈로 설명하지 않는다.
상세 댓글의 feature 전체 SHA·compiler/runtime·UPDATE 초기화와 계수 순서 등의 공백도 남아 있다.
[재실행의 전체 결과와 한계](CBRD-27785-reviewer-reproduction_4408135c_20261031_codex.md)에 근거한다.

### 이 발표로 HA·복구·동시성까지 검증했다고 말할 수 있는가?

이번 diff에는 disk·WAL 형식, latch·transaction lock, MVCC 가시성 판단 변경이 없다는 코드 설명만 할 수 있다.
그 사실이 전체 HA·복구·동시성 회귀의 실행 검증을 대신하지는 않는다.
과거 집중 테스트 기록과 이번 작성의 정적 확인을 구분한다.
[검증 결과와 한계](CBRD-27785-code-walkthrough_f1b99031c_codex.md#verification)에 범위가 있다.
