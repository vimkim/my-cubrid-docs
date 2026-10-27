# CBRD-27785: 박세훈 팀장님 성능 질문에 대한 추천 답변

작성일: 2026-10-27, Asia/Seoul. 대상 독자: PR #7990 작성자와 성능 리뷰어.
대상은 [박세훈 팀장님(shparkcubrid)의 성능 보고](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6434778190)에 있는 질문 1~5다.
댓글 게시 전 검토용 초안이며, 아래의 후속 측정이나 기능 구현을 새로 수행한 결과는 아니다.

핵심은 **일반 heap 성능 저하, 기존 overflow와의 비교, 후속 최적화를 구분하여 답하는 것**이다.
`STORAGE FORCE_INLINE` 관련 이슈는 [CBRD-27259](https://jira.cubrid.org/browse/CBRD-27259)이며 현재 통합본의 사용 가능한 옵션이 아니다.

## 확인한 기준

| 구분 | 확인한 revision 또는 상태 |
| --- | --- |
| 성능 보고의 비교 | PR head `4408135c0833ec959da3590f12c14efa69610c7e` / develop `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| 조회한 PR #7990 | head `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`, base develop `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| 별도 성능 수정안 PR #8299 | Draft·Open, head `bcb900d1696756a120ec0a2b7885c212f71ebc07`, base `feature/oos-merge` 의 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |
| 소스 검토 범위 | `CUBRID/CUBRID` 의 위 PR revision과 `vimkim/cubrid` 의 수정안 `bcb900d` |
| 실행 근거 | 기존 [분석·검증 기록](CBRD-27785-oos-read-performance_bcb900d_codex.md)을 인용한다. 이번 답변 준비에서 빌드·벤치마크는 실행하지 않았다. |

PR 상태와 JIRA 상태는 2026-10-27 조회 시점의 관찰이다. PR #7990에 별도 수정안이 이미 반영되었다고 표현하지 않는다.

## 추천 답변 초안

찾아주셔서 감사합니다. 성능 회귀 관련 문제들은 신규로 생성한 [CBRD-27785](http://jira.cubrid.org/browse/CBRD-27785)에서 별도로 대응하겠습니다.

성능 시나리오는 [CBRD-26659](http://jira.cubrid.org/browse/CBRD-26659)의 테스트 케이스([PR #8128](https://github.com/CUBRID/cubrid/pull/8128))로도 관리하고 있습니다(5번 항목 - OOS에 불리한 시나리오 참고). 기능 검증을 마친 뒤, timeout으로 비활성화된 성능 시나리오들을 검토하며 개선해 나갈 예정입니다.

다만 말씀해 주신 내용 중 기존 develop의 일반 테이블 성능에도 영향이 큰 항목은 feature 머지 전에 먼저 반영할 수 있을지 검토하겠습니다.

<a id="reply-1-inline-reads"></a>
### 1. OOS 값이 없는 일반 테이블의 성능 저하

말씀하신 일반 테이블의 스캔 비용 증가를 별도 실험에서도 확인했습니다. OOS 값이 없는 행을 읽을 때도 OOS용 준비 작업을 거치던 부분과, 가변 컬럼 위치를 해석하는 비용을 줄인 수정안을 [PR #8299](https://github.com/CUBRID/cubrid/pull/8299)에 준비했습니다.

양쪽 모두 heap에만 저장되는 작은 행 20만 개로 비교했을 때, 수정 전에는 좁은 컬럼 스캔과 여러 컬럼 스캔의 instructions가 기준 대비 약 5.12%, 8.89% 증가했습니다. 수정 후에는 약 1.11%, 1.36% 증가로 줄었고, 실행 순서를 뒤집어도 같은 수준이었습니다. 다만 원본 SQL을 그대로 재실행한 결과는 아니며, 보고해 주신 조건에 맞춰 재구성한 실험입니다.

현재 확인한 범위는 이 두 SELECT 스캔입니다. 일반 테이블의 UPDATE를 포함한 나머지 CRUD까지 해결한 것은 아니며, PR #8299도 아직 PR #7990에 반영되기 전입니다.

<a id="reply-2-update-reuse"></a>
### 2. 작은 컬럼만 바꾸는 UPDATE와 변경 없는 OOS 값 재사용

기존 overflow도 UPDATE할 때 변경된 컬럼만 부분적으로 고치는 방식이 아니라, 변경 후 record 전체를 다시 기록합니다. OOS의 현재 UPDATE도 변경하지 않은 큰 값을 다시 저장한다는 점에서 기존 방식과 같습니다.

[CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)은 여기서 더 나아가, UPDATE 문에서 바꾸지 않은 큰 값은 기존 저장 내용을 재사용하도록 하는 최적화입니다. 기존 overflow에도 없던 추가 최적화이므로, 후속 최적화 이슈인 TODO로 분류해 두었습니다.

<a id="reply-3-large-value-scan"></a>
### 3. 큰 컬럼 스캔의 instructions 증가와 경과 시간 차이

보고하신 큰 컬럼 스캔의 성능 차이는 아직 재현하지 못했습니다. 가능하시다면 테이블 DDL, 데이터 생성 방법, 실행 SQL 등 좀 더 구체적인 재현 케이스를 공유해 주실 수 있을까요?

현재로서는 약 4~16KB 구간에서, 기존 엔진에서는 heap에 있던 값이 이번 PR로 인해 OOS로 옮겨진 경우 때문으로 추정합니다. [CBRD-27785](http://jira.cubrid.org/browse/CBRD-27785)에 설명한 **2번(heap → OOS)** 경우입니다. heap 집적도를 높이는 대신 큰 값을 별도로 읽는 비용이 생기는 설계 trade-off에 해당할 수 있습니다.

이 영향을 분리해 보기 위해, OOS 전환 임계값을 기존 overflow 기준에 맞춰 약 16KB로 높인 비교용 빌드에서 같은 케이스를 재측정해 볼 만하다고 생각합니다. 기존 엔진에서도 overflow에 저장되는 record를 대상으로 overflow와 OOS를 같은 조건에서 비교하는 측정도 필요합니다.

<a id="reply-4-disable-oos"></a>
### 4. OOS를 끄는 방법과 STORAGE FORCE_INLINE

PostgreSQL의 `MAIN`, `PLAIN`처럼 컬럼별로 저장 방식을 선택할 수 있도록 하는 방향입니다. 현재의 `STORAGE PREFER_INLINE` 은 가능하면 heap에 남기는 옵션이고, OOS로 옮기는 것을 막는 `STORAGE FORCE_INLINE` 은 [CBRD-27259](https://jira.cubrid.org/browse/CBRD-27259)에서 추후 별도 지원할 예정입니다.

<a id="reply-5-io-benefit"></a>
### 5. OOS의 I/O 이득을 보여 주는 측정

OOS의 장점은 **필요 없는 큰 컬럼을 디스크에서 읽지 않아도 된다는 것**입니다. 예를 들어 긴 본문이 있는 record에서 id나 상태 값만 조회할 때, 기존 overflow는 큰 record 본문까지 가져오지만 OOS는 heap에 남은 작은 컬럼만 읽을 수 있습니다.

이번 테스트는 데이터가 모두 4G 버퍼에 올라가 있어, 이처럼 디스크 읽기를 줄이는 효과가 드러나기 어렵습니다.

이 효과를 보려면 버퍼보다 큰 테이블에서 작은 컬럼만 읽는 비교가 필요합니다. 특히 기존에 16KB를 넘는 record가 overflow에 저장된 테이블이라면, OOS에서는 필요 없는 큰 값을 건너뛸 수 있어 더 적은 I/O와 더 나은 성능을 기대할 수 있습니다. 실제 개선 폭은 추가 측정으로 확인할 사항입니다.

## 게시 전 사실 확인

### 현재 지원하는 옵션과 후속 이슈

[현재 PR의 STORAGE 문법](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/parser/csql_grammar.y#L10684)은 `DEFAULT`, `PREFER_OUTLINE`, `PREFER_INLINE`, `FORCE_OUTLINE` 을 제공한다. `FORCE_INLINE` 은 없다. [heap demotion 경로](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L13183)는 `PREFER_INLINE` 후보를 나중에 처리하지만 필요하면 밖으로 옮긴다.

2026-10-27 조회에서 [CBRD-27259](https://jira.cubrid.org/browse/CBRD-27259)는 Open·Unresolved·Unassigned였다. 이슈가 말하는 `FORCE_INLINE` 은 해당 컬럼 값을 OOS로 옮기지 않는 정책이다. **전체 record가 항상 heap page 안에 들어간다는 뜻은 아니며**, 큰 record의 기존 overflow 저장과 구분해야 한다.

PostgreSQL의 `MAIN`·`PLAIN`을 참고한 저장 정책이라는 설명은 [기존 비교 문서](../cbrd-26979/CBRD-26979-storage-variable-type-validation_882f70f_codex.md)에 근거한다. 압축이나 큰 record 처리까지 PostgreSQL과 완전히 같은 동작이라는 뜻은 아니다.

### UPDATE 재사용은 기존 overflow보다 나아가는 후속 최적화다

기준 엔진의 [overflow UPDATE 진입점](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/heap_file.c#L6190)은 새 record를 `overflow_update` 에 넘긴다. [기존 overflow UPDATE 구현](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/overflow_file.c#L375)은 record 전체 길이를 순회하며 내용을 다시 기록한다. 컬럼별로 바뀌지 않은 큰 값을 재사용하는 방식은 아니다.

검토한 `bcb900d` 소스도 [미할당 속성 읽기](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L13038)와 [OOS 적재 요청 준비](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L13522)를 거쳐 값을 다시 저장한다. [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)은 UPDATE 문이 할당하지 않은 OOS 컬럼의 기존 저장 내용을 재사용하려는 최적화이며, 조회 시점에는 Open·Unresolved·Unassigned였다. 후속 최적화로 TODO에 둔 이유는 2026-10-27 제공받은 작성자의 설명을 반영한다.

### 4~16KB 구간이라는 설명은 아직 추정이다

3번의 미재현 상태는 2026-10-27 제공받은 작성자의 설명을 반영한다. 원문 `w`는 6KB 값을 사용한 측정이다. 이 크기는 기존에는 heap에 남지만 OOS 적용 후에는 큰 값이 밖으로 옮겨질 수 있는 구간에 해당한다. 다만 실제 경로는 header와 압축 결과를 포함한 저장 크기로 확인해야 하며, 아직 원본 fixture의 저장 상태를 검증한 것은 아니다.

OOS 전환 임계값을 기존 overflow 경계인 약 16KB에 맞춘 비교용 빌드는 저장 위치가 달라진 영향을 분리하기 위한 실험 제안이다. 예를 들어 약 6KB record가 양쪽 모두 heap에 남도록 하여 공통 경로 비용을 비교할 수 있다. 이는 제품의 기본 임계값 변경 결정이나 이미 제공되는 설정을 뜻하지 않으며, 이번 답변 준비에서 소스 변경·재측정을 수행한 것은 아니다.

큰 값의 외부 저장 방식 자체를 비교하려면 별도로 기존에도 overflow를 사용하는 fixture로 overflow→OOS를 비교한다. 이 비교 기준과 heap→OOS 구간의 성능 차이는 분리해서 설명한다.

### 회귀 대응과 기존 테스트 시나리오의 연결

2026-10-27 조회한 [CBRD-26659](https://jira.cubrid.org/browse/CBRD-26659)의 5번 분류는 저장 효율·회수·불리한 시나리오를 다룬다. [연결된 PR #8128](https://github.com/CUBRID/cubrid/pull/8128)의 head는 `e3589ae42d42b04eb020e1ae43e165b01d31b12a`이며, 두 testcase 저장소의 변경을 연결하는 engine PR이다. 시작 문단의 후속 개선 계획은 작성자가 제공한 문구를 반영한다. 비활성·장시간 시나리오를 성능 검증 통과로 계산하지 않는다.

### I/O 측정에서 구분할 조건

16KB를 넘는 record가 많다는 이유만으로 heap 집적도가 낮다고 단정하지 않는다. [기존 overflow 저장 경로](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/heap_file.c#L21047)는 heap에 전달용 OID를 남기므로, 이 경우 핵심은 **작은 컬럼을 읽으려고 overflow 본문까지 가져오는 비용을 피하는 것**이다. [기존 overflow 읽기](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/heap_file.c#L6338)는 큰 record 본문을 가져오고, [OOS 값 읽기 준비](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_oos.cpp#L734)는 요청된 컬럼만을 대상으로 한다. 기존 heap record가 OOS로 바뀌면서 heap 집적도가 좋아지는 경우는 별도 비교다.

후속 측정안을 고른다면 다음 조건이 적절하다. 이는 제안이며 실행 결과가 아니다.

- 선언 길이보다 실제 저장 크기와 압축 결과를 확인하여 heap→OOS와 overflow→OOS를 구분한다. 원문 `w` 의 6KB 값과 16KB를 넘는 overflow fixture도 구분한다.
- `id` 만 읽는 쿼리가 인덱스만 읽고 끝나지 않도록, heap 접근이 필요한 작은 컬럼과 실제 실행 계획을 확인한다.
- 테이블 전체 크기뿐 아니라 순회 중 실제 읽는 working set과 버퍼 miss를 확인한다. OOS heap 부분이 버퍼에 남는 효과 자체도 측정 대상이다.
- 엔진 I/O read와 실제 저장장치 I/O를 구분한다. OS page cache에서 읽었다면 저장장치 I/O가 줄었다고 단정하지 않는다.
- 좁은 컬럼 스캔과 큰 값까지 읽는 스캔을 같은 조건에서 비교하고, page 접근 수·I/O read·instructions·경과 시간을 함께 남긴다.

기존 독립 측정과 정확성 검증의 정확한 조건·한계는 [일반 heap 읽기 분석·검증](CBRD-27785-oos-read-performance_bcb900d_codex.md)에 보존한다. 이 문서는 새 성능 수치나 구현 완료를 추가로 주장하지 않는다.
