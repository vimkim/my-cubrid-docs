# CBRD-27785: 박세훈 팀장님 성능 질문에 대한 추천 답변

작성일: 2026-10-27, Asia/Seoul. 대상 독자: PR #7990 작성자와 성능 리뷰어.
대상은 [박세훈 팀장님(shparkcubrid)의 성능 보고](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6434778190)에 있는 질문 1~5다.
댓글 게시 전 검토용 초안이며, 아래의 후속 측정이나 기능 구현을 새로 수행한 결과는 아니다.

핵심은 **일반 heap SELECT 수정안은 검증했지만, UPDATE·큰 값 스캔·OOS 비활성화·I/O 조건의 개선까지 완료한 것은 아니라는 점**이다.
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

<a id="reply-1-inline-reads"></a>
### 1. OOS 값이 없는 일반 테이블의 성능 저하

말씀하신 일반 테이블의 스캔 비용 증가를 별도 실험에서도 확인했습니다. OOS 값이 없는 행을 읽을 때도 OOS용 준비 작업을 거치던 부분과, 가변 컬럼 위치를 해석하는 비용을 줄인 수정안을 [PR #8299](https://github.com/CUBRID/cubrid/pull/8299)에 준비했습니다.

양쪽 모두 heap에만 저장되는 작은 행 20만 개로 비교했을 때, 수정 전에는 좁은 컬럼 스캔과 여러 컬럼 스캔의 instructions가 기준 대비 약 5.12%, 8.89% 증가했습니다. 수정 후에는 약 1.11%, 1.36% 증가로 줄었고, 실행 순서를 뒤집어도 같은 수준이었습니다. 다만 원본 SQL을 그대로 재실행한 결과는 아니며, 보고해 주신 조건에 맞춰 재구성한 실험입니다.

현재 확인한 범위는 이 두 SELECT 스캔입니다. 일반 테이블의 UPDATE를 포함한 나머지 CRUD까지 해결한 것은 아니며, PR #8299도 아직 PR #7990에 반영되기 전입니다.

<a id="reply-2-update-reuse"></a>
### 2. 작은 컬럼만 바꾸는 UPDATE와 변경 없는 OOS 값 재사용

작은 상태 컬럼 하나를 바꾸는 데 큰 OOS 값까지 다시 읽고 저장하는 비용을 줄여야 한다는 의견에 동의합니다. 해당 개선은 [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)으로 등록되어 있으며, UPDATE 문에서 값을 할당하지 않은 OOS 컬럼의 기존 저장 내용을 재사용하는 방향입니다. 현재 통합본에는 구현되어 있지 않습니다. 이 재적재 비용은 heap 집적도를 높이는 설계상 비용과 분리해서 볼 필요가 있습니다.

다만 값의 재적재만 생략하면 기존 값을 vacuum이 지우거나 이전 버전에서 읽지 못하는 문제가 생길 수 있어, 재사용한 값의 수명과 rollback·복구·복제를 함께 검증해야 합니다. 이번 머지에 포함할지는 아직 정하지 않았으며, 이 검증 범위와 구현 비용을 확인한 뒤 결정할 필요가 있습니다. 작은 컬럼 UPDATE의 비용과 뒤따르는 vacuum 비용도 나눠 비교하는 것이 좋겠습니다.

<a id="reply-3-large-value-scan"></a>
### 3. 큰 컬럼 스캔의 instructions 증가와 경과 시간 차이

보고하신 큰 컬럼 스캔에서 CPU 명령 수가 40% 늘고 경과 시간이 2.5배가 된 원인은 아직 확인하지 못했습니다. instructions 증가율과 경과 시간 증가율이 다르다는 사실만으로 병렬 스캔이 빠졌거나 OOS 페이지 접근 대기가 원인이라고 확정하기는 어렵습니다.

우선 같은 실행 계획과 병렬 worker 수인지 확인하고, 실제 page 접근 수, I/O read, CPU cycles와 대기 시간을 함께 비교할 필요가 있습니다. 기존 heap에서 OOS로 바뀐 경우인지, 기존 overflow를 OOS가 대체한 경우인지도 실제 저장 상태로 구분해야 합니다. 데이터가 메모리에 올라간 조건에서도 큰 값을 따라가서 읽고 조립하는 비용은 남기 때문에, 앞의 일반 heap SELECT 수정 결과와는 별도로 조사해야 합니다.

<a id="reply-4-disable-oos"></a>
### 4. OOS를 끄는 방법과 STORAGE FORCE_INLINE

컬럼 단위로 OOS 저장을 금지하는 `STORAGE FORCE_INLINE` 은 [CBRD-27259](https://jira.cubrid.org/browse/CBRD-27259)에 후속 기능으로 등록되어 있습니다. 다만 현재 통합본에는 구현되지 않아, 지금 사용할 수 있는 회피 방법으로 안내하기는 어렵습니다.

현재 지원하는 `STORAGE PREFER_INLINE` 은 해당 컬럼을 가능하면 heap에 남기도록 OOS 이동 순서를 늦추는 옵션입니다. 필요하면 그 컬럼도 OOS로 옮기므로 OOS 비활성화 옵션은 아닙니다.

`FORCE_INLINE` 이 추가되더라도 컬럼별 저장 정책이며, 전역 시스템 파라미터나 임계값 설정과는 별도입니다. 해당 컬럼을 OOS로 옮기지 않는다는 뜻이므로, 큰 record의 기존 overflow 저장까지 금지하는 것은 아닙니다. 기존 데이터의 소급 재배치도 별도 검토가 필요합니다. 따라서 요청하신 전역 비활성화·임계값 설정의 필요성은 이 기능과 구분하여 검토할 필요가 있습니다.

<a id="reply-5-io-benefit"></a>
### 5. OOS의 I/O 이득을 보여 주는 측정

좁은 컬럼 스캔에서 instructions가 23% 줄어든 점은 메모리 상주 조건에서도 확인된 이득으로 이해하고 있습니다. 말씀하신 대로 데이터가 모두 `data_buffer_size=4G` 에 올라간 이번 측정에서는, 디스크에서 불필요한 큰 컬럼을 읽지 않는 OOS의 추가 이득은 드러나기 어렵습니다.

추가 비교는 버퍼보다 큰 데이터를 순회하면서 작은 메타데이터만 읽는 조건이 적절하겠습니다. 특히 OOS 적용 전에는 16KB를 넘는 record가 overflow에 저장되고, 적용 후에는 작은 컬럼이 heap에 남는 경우를 구분해 볼 수 있습니다. 기존 overflow에서는 필요한 작은 컬럼을 얻기 위해 큰 record 본문을 가져오지만, OOS에서는 사용하지 않는 큰 컬럼의 본문 접근을 피할 수 있기 때문입니다.

이 조건에서는 I/O와 경과 시간이 줄어드는 효과를 기대하지만, 아직 정량 결과는 없습니다. 실제 실행 계획, page 접근 수, I/O read와 경과 시간을 함께 측정해 확인할 필요가 있습니다.

## 게시 전 사실 확인

### 현재 지원하는 옵션과 후속 이슈

[현재 PR의 STORAGE 문법](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/parser/csql_grammar.y#L10684)은 `DEFAULT`, `PREFER_OUTLINE`, `PREFER_INLINE`, `FORCE_OUTLINE` 을 제공한다. `FORCE_INLINE` 은 없다. [heap demotion 경로](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L13183)는 `PREFER_INLINE` 후보를 나중에 처리하지만 필요하면 밖으로 옮긴다.

2026-10-27 조회에서 [CBRD-27259](https://jira.cubrid.org/browse/CBRD-27259)는 Open·Unresolved·Unassigned였다. 이슈가 말하는 `FORCE_INLINE` 은 해당 컬럼 값을 OOS로 옮기지 않는 정책이다. **전체 record가 항상 heap page 안에 들어간다는 뜻은 아니며**, 큰 record의 기존 overflow 저장과 구분해야 한다. 테이블 전체나 시스템 전체를 끄는 옵션, 기존 OOS 값을 자동으로 되돌리는 기능으로 확대해서 설명하지 않는다.

### UPDATE 재사용은 설계와 구현을 나눠 설명한다

2026-10-27 조회에서 [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)은 Open·Unresolved·Unassigned였다. 이슈의 방향은 문장이 값을 할당하지 않은 컬럼의 기존 체인 재사용이다. 할당했으나 결과 값이 같은 컬럼까지 값 비교로 재사용한다는 뜻이 아니다.

검토한 `bcb900d` 소스의 [미할당 속성 읽기](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L13038)는 미할당 값을 읽으며, [OOS 적재 요청 준비](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/storage/heap_file.c#L13522)는 선택된 값을 직렬화해 새 적재 요청을 만든다. 기존 [vacuum의 옛 값 정리 경로](https://github.com/vimkim/cubrid/blob/bcb900d1696756a120ec0a2b7885c212f71ebc07/src/query/vacuum_oos.cpp#L248)도 남아 있다. 재사용이 이미 구현되었다는 근거로 일반 heap 읽기 수정안을 제시하지 않는다.

현행 사양의 재사용 계약은 전체 24B stub 보존과 commit 조건부 vacuum 알림, rollback·복구·복제까지 포함한다. 기존 JIRA 본문에 남은 20B·4B generation 표기는 오래된 분석이므로 이번 답변의 현재 형식 근거로 사용하지 않는다. [확인한 OOS 사양](https://github.com/vimkim/cubrid-oos-context/blob/3462a7f69a7ec0de8a0b97ad8da32b463ecf0e8c/OOS-CONTEXT.md#L208)을 기준으로 해석한다.

### I/O 측정에서 구분할 조건

16KB를 넘는 record가 많다는 이유만으로 heap 집적도가 낮다고 단정하지 않는다. [기존 overflow 저장 경로](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/heap_file.c#L21047)는 heap에 전달용 OID를 남기므로, 이 경우 핵심은 **작은 컬럼을 읽으려고 overflow 본문까지 가져오는 비용을 피하는 것**이다. [기존 overflow 읽기](https://github.com/CUBRID/cubrid/blob/4781495f01523a3ecc5891e3377ad62cf876a1cd/src/storage/heap_file.c#L6338)는 큰 record 본문을 가져오고, [OOS 값 읽기 준비](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_oos.cpp#L734)는 요청된 컬럼만을 대상으로 한다. 기존 heap record가 OOS로 바뀌면서 heap 집적도가 좋아지는 경우는 별도 비교다.

후속 측정안을 고른다면 다음 조건이 적절하다. 이는 제안이며 실행 결과가 아니다.

- 선언 길이보다 실제 저장 크기와 압축 결과를 확인하여 heap→OOS와 overflow→OOS를 구분한다. 원문 `w` 의 6KB 값과 16KB를 넘는 overflow fixture도 구분한다.
- `id` 만 읽는 쿼리가 인덱스만 읽고 끝나지 않도록, heap 접근이 필요한 작은 컬럼과 실제 실행 계획을 확인한다.
- 테이블 전체 크기뿐 아니라 순회 중 실제 읽는 working set과 버퍼 miss를 확인한다. OOS heap 부분이 버퍼에 남는 효과 자체도 측정 대상이다.
- 엔진 I/O read와 실제 저장장치 I/O를 구분한다. OS page cache에서 읽었다면 저장장치 I/O가 줄었다고 단정하지 않는다.
- 좁은 컬럼 스캔과 큰 값까지 읽는 스캔을 같은 조건에서 비교하고, page 접근 수·I/O read·instructions·경과 시간을 함께 남긴다.

기존 독립 측정과 정확성 검증의 정확한 조건·한계는 [일반 heap 읽기 분석·검증](CBRD-27785-oos-read-performance_bcb900d_codex.md)에 보존한다. 이 문서는 새 성능 수치나 구현 완료를 추가로 주장하지 않는다.
