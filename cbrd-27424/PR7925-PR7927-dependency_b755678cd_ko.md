# PR #7925는 왜 PR #7927을 먼저 통합하려고 하는가?

**CBRD-27424의 원래 문제는 `feature/oos-merge`에서 독립적으로 고칠 수 있다. 실제로 이전 구현도 그렇게 동작했다.** 현재 PR #7925가 PR #7927에 의존하는 이유는, 이후 코드를 정리하면서 #7927의 공통 변환·메모리 관리·저장 경로를 사용하기로 했기 때문이다.

따라서 정확한 설명은 **“현재 구현을 유지하려면 #7927의 코드를 함께 통합해야 하며, 두 PR의 역할을 구분하려면 #7927을 먼저 병합하는 순서가 적절하다”**이다. “원래 버그는 #7927 없이는 고칠 수 없다”라고 설명하면 사실과 다르다.

작성·확인일: 2026-10-08, Asia/Seoul. 이 문서는 두 PR의 의존성에 집중하며, 전체 PR의 리뷰 가이드는 [기존 한글 가이드](review-guide-pr7925-28b65d18a-ko.md)를 참고한다.

| 비교 대상 | 고정된 소스 리비전 |
| --- | --- |
| `feature/oos-merge`의 확인 당시 tip 및 #7925와의 merge-base | `fb567a629cdb390fff920542173fa36f454c74a0` |
| #7925의 이전 독립 구현 | `1c660d22e4340ee707336ad08c8b4bf4b69744de` |
| [PR #7925](https://github.com/CUBRID/cubrid/pull/7925)의 현재 HEAD | `b755678cd9a3ab465215228d5664f7f1edf24846` |
| [PR #7927](https://github.com/CUBRID/cubrid/pull/7927)의 현재 HEAD | `f3144ab4b72fc2bf73f115c9da1cf193c756457a` |

#7925의 head 저장소는 `vimkim/cubrid`, 브랜치는 `CBRD-27424-oos-loaddb-sa`, 병합 대상은 `feature/oos-merge`이다. 두 PR은 확인 당시 모두 열려 있으며, #7927의 실제 공유 브랜치 병합은 아직 이루어지지 않았다.

## 읽는 순서

- [두 이슈는 무엇을 고치는가?](#two-problems)
- [왜 원래 문제는 독립적으로 고칠 수 있었는가?](#independent-fix)
- [현재 구현에서는 무엇을 재사용하는가?](#current-dependency)
- [#7927을 먼저 병합하면 무엇이 좋아지는가?](#merge-order)
- [다른 선택과 확인 범위](#choices-and-evidence)
- [리뷰어 질문 찾아보기](#reviewer-questions)

<a id="two-problems"></a>
## 두 이슈는 무엇을 고치는가?

OOS는 큰 컬럼 값을 행 밖의 별도 파일에 저장하는 기능이다. 행에는 그 값을 찾아갈 수 있는 참조 정보만 남긴다. 여기서 **heap은 행을 저장하는 파일**이고, **workspace는 저장하기 전 객체를 메모리에 보관하는 영역**이다.

| 이슈 | 문제가 생기는 이유 | 고치려는 동작 |
| --- | --- | --- |
| CBRD-27424 / #7925 | standalone loader와 일부 CSQL workspace 쓰기가 OOS 변환을 건너뜀 | 이 경로에도 기존 OOS 저장 정책을 적용 |
| CBRD-27089 / #7927 | 일반 쓰기 경로가 실제 목적지 heap을 고르기 전에 OOS 값을 저장할 수 있음 | 목적지 heap을 정한 뒤 그 heap의 OOS 파일에 값을 저장 |

예를 들어 5,000바이트 VARBIT 값을 저장한다고 하자. #7925의 원래 문제는 일반 SQL에서는 이 값이 OOS로 분리되는데, standalone workspace 경로에서는 행 안에 그대로 남는 것이었다. 값 조회는 정상일 수 있어도 저장 방식이 달라지는 문제다. [원래 문제와 목표](https://github.com/CUBRID/cubrid/pull/7925).

#7927은 저장할 **위치**가 잘못되는 문제를 다룬다. 파티션 테이블의 부모를 대상으로 INSERT하면 실제 행은 어느 자식 파티션에 들어갈지 결정해야 한다. 일반 SQL 경로에서는 변환기가 먼저 OOS 값을 기록하고, 그 뒤 locator가 파티션을 선택했다. 이 순서에서는 큰 값은 부모 heap의 OOS 파일에, 행은 자식 heap에 들어갈 수 있다. 코드에서 확인한 순서는 아래와 같다. [변환 후 force 호출](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7698-L7713), [변환 중 OOS 삽입](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13813-L13821), [입력 class에 속한 OOS 파일 선택](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_oos.cpp#L635-L657).

```text
기존 일반 SQL 경로에서 생길 수 있는 문제
부모 class를 기준으로 큰 값을 OOS에 저장
→ 자식 파티션 선택
→ 자식 heap에 행 저장

#7927의 처리 순서
큰 값의 바이트를 메모리에 준비
→ 자식 파티션 선택
→ 선택한 자식 heap의 OOS 파일에 큰 값 저장
→ 같은 자식 heap에 행 저장
```

<a id="independent-fix"></a>
## 왜 원래 문제는 독립적으로 고칠 수 있었는가?

이전 #7925 구현인 `1c660d22e`는 workspace 입력을 그대로 받아 먼저 `partition_prune_insert`를 호출했다. 여기서 실제 목적지인 `real_class_oid`와 `real_hfid`를 얻은 뒤, `locator_oos_demote_workspace_record`를 호출했다. 따라서 workspace 경로에서는 #7927 없이도 올바른 목적지를 기준으로 OOS 값을 저장할 수 있었다. [파티션 선택](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5071-L5072), [선택한 목적지로 변환](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5144-L5155).

```text
이전 #7925의 workspace 경로
workspace에서 직렬화한 행
→ 목적지 파티션 선택
→ 기존 변환기로 큰 값을 OOS에 저장
→ heap/index 쓰기
```

이 helper는 기존 heap attrinfo 변환기를 사용했다. 새 OOS 변환기를 만든 것이 아니다. OOS로 보낼 값이 없으면 원래 행을 유지하고, workspace가 이미 갱신한 변경 번호(CHN)를 보존했다. UPDATE로 파티션을 이동할 때도 workspace에서 온 입력이라는 정보를 목적지 INSERT로 전달했다. [이전 helper](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L4946-L4995), [UPDATE와 이동 처리](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L6084-L6152).

이전 리비전의 공개 검증 기록에는 Debug/Release 빌드 성공과 CTest 37/37 통과가 남아 있다. 13개 loader/workspace 사례와 21개 비교 사례를 포함한다. 이는 이번 문서 작성 중 다시 실행한 결과가 아니라, **이전 독립 구현이 실제로 동작했다는 과거 검증 근거**다. 일반 SQL의 모든 파티션 문제까지 고쳤다는 뜻은 아니다. [해당 리비전의 검증 댓글](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-6031418768).

<a id="current-dependency"></a>
## 현재 구현에서는 무엇을 재사용하는가?

현재 #7925는 이전 workspace 전용 helper와 별도 copyarea 해제 코드를 제거했다. 대신 #7927이 제공하는 공통 경로를 사용한다. 바뀐 핵심은 다음과 같다. [현재 locator 경로](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/transaction/locator_sr.c#L4947-L5027).

| 코드 | 쉽게 설명한 역할 | 필요한 이유 |
| --- | --- | --- |
| `heap_pending_record` | 변환한 행과 아직 OOS에 쓰지 않은 큰 값의 바이트를 보관하는 객체 | 파티션 선택·실제 저장이 끝날 때까지 임시 데이터가 살아 있어야 함 |
| `heap_prepare_oos_record` | 받은 행을 읽고 저장할 표현을 메모리에 준비 | 기존 OOS 정책을 적용하면서, 최종 목적지가 정해지기 전에 값을 디스크에 쓰지 않도록 함 |
| `heap_oos_finalize_record` | 목적지의 OOS 파일에 값을 쓰고 임시 참조를 실제 OOS 참조로 바꿈 | heap에 저장하는 행이 실제로 읽을 수 있는 OOS 값을 가리켜야 함 |
| `locator_finalize_oos_record` | 목적지 선택 후, 위 준비·최종 저장 단계를 연결 | workspace 입력도 공통 처리에 넣고, 이어지는 heap/index 쓰기에 사용할 행을 전달 |

큰 값이 아직 메모리에만 있을 때도 파티션 선택이나 키 검사에서 그 값을 읽을 수 있어야 한다. #7927은 읽는 쪽에도 보관 객체를 전달하고, 그 객체에 있는 바이트를 읽을 수 있도록 한다. 실제 OOS 저장은 목적지를 정한 뒤 수행한다. [메모리 값의 보관](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/storage/heap_file.c#L13935-L13965), [목적지 기준 최종 저장](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/storage/heap_oos.cpp#L120-L240).

여기서 두 종류의 소유권을 구분해야 한다. **저장 소유권**은 행과 OOS 값이 어느 heap에 속하는지를 뜻한다. **메모리 소유권**은 누가 임시 버퍼를 보관하고 해제하는지를 뜻한다. `heap_pending_record`가 메모리를 해제한다고 해서 이미 쓴 DB 페이지까지 롤백되는 것은 아니다. DB 변경 취소는 기존 트랜잭션·force 작업 범위가 담당한다. [객체의 메모리 해제](https://github.com/vimkim/cubrid/blob/b755678cd9a3ab465215228d5664f7f1edf24846/src/storage/heap_pending_record.cpp#L51-L58), [기존 가이드의 롤백 설명](review-guide-pr7925-28b65d18a-ko.md#memory-versus-rollback).

이 공통 API들은 기준 브랜치 `fb567a629`와 이전 독립 구현 `1c660d22e`에는 없다. 따라서 **현재 workspace 코드만 떼어 기준 브랜치에 적용하면 필요한 API가 빠진다.** 의존성을 없애려면 이전 독립 변환 경로를 되살리거나, 그에 해당하는 처리를 별도로 구현하고 검증해야 한다.

<a id="merge-order"></a>
## #7927을 먼저 병합하면 무엇이 좋아지는가?

첫째, 같은 입력을 변환하는 경로를 하나로 정리할 수 있다. workspace 전용 변환과 #7927의 공통 준비 경로를 함께 유지하면, 어떤 입력이 어느 단계에서 변환되는지와 버퍼를 누가 해제하는지를 두 군데에서 확인해야 한다. 현재 구현은 기존 force-local 보관 객체를 재사용하므로 이 책임을 공통 경로에서 확인할 수 있다. [변환 레코드 소유권 설명](review-guide-pr7925-28b65d18a-ko.md#received-owner).

둘째, 두 이슈의 리뷰 범위를 구분할 수 있다. #7927에서 일반 SQL·loader·파티션의 목적지 및 OOS 소유권 문제를 먼저 검토하고, #7925에서는 workspace 입력을 그 경로에 연결하는 변경을 검토한다. 현재 #7925의 전체 diff는 기준 브랜치 대비 29개 파일이지만, #7927의 현재 소스를 기준으로 비교하면 8개 파일이다. **병합 순서를 나누는 이유는 현재 설계의 공통 코드를 한 번 통합하고, 각 PR의 책임을 명확히 하기 위해서다.** 이 부분은 확인한 소스 차이에 근거한 통합 순서 판단이다.

셋째, 실제로 공유 브랜치에 반영된 #7927의 결과를 기준으로 #7925를 확인할 수 있다. #7927이 squash merge되거나 추가 수정되면 실제 결과가 지금 비교한 리비전과 같은지 확인하고, workspace·파티션 관련 검증을 다시 해야 한다. 기존 테스트 결과만으로 이후 통합 결과까지 보장할 수는 없다.

다만 **GitHub에서 #7927이 먼저 병합되어야 현재 #7925 코드를 실행할 수 있다는 뜻은 아니다.** 현재 #7925 브랜치는 이미 #7927의 구현을 포함한다. 확인한 storage·partition·query의 관련 소스는 #7927과 동일하다. 지금 #7925 전체를 먼저 병합하면 #7927에 해당하는 구현도 함께 들어가므로, 별도 이슈의 변경까지 #7925를 통해 통합하는 셈이 된다.

<a id="choices-and-evidence"></a>
## 다른 선택과 확인 범위

| 선택 | 가능한가? | 고려할 점 |
| --- | --- | --- |
| 이전 방식으로 `feature/oos-merge`에서 workspace 문제만 독립 수정 | 가능. 이전 구현과 검증 기록이 있음 | 별도 변환·메모리 관리 경로를 유지하고, 이후 #7927이 들어올 때 두 경로를 조정해야 함 |
| 현재 공통 경로를 유지하고 #7927부터 통합 | 현재 구현에 맞는 순서 | 실제 #7927 병합 결과에 #7925를 맞추고, 통합 검증이 필요 |

이번 설명에서는 고정된 소스 비교, PR 정보, 기존 검증 기록과 문서 링크를 확인했다. 빌드·DB 테스트·CI는 새로 실행하지 않았으며 엔진 코드도 변경하지 않았다. 문서는 병합 준비 완료나 현재 HEAD의 CI 통과를 판정하지 않는다.

아래 명령으로 주요 소스 비교를 재현할 수 있다. 첫 두 명령은 차이가 없고, 마지막 명령은 #7927 대비 workspace 변경 8개 파일, 967줄 추가·31줄 삭제를 보여 준다.

```sh
git diff fb567a629 1c660d22e -- src/storage/heap_file.c src/query/partition.c
git diff f3144ab4b b755678cd -- src/storage/heap_file.c src/storage/heap_oos.cpp src/storage/heap_pending_record.cpp src/storage/heap_pending_record.hpp src/storage/heap_oos_value_ref.cpp src/storage/heap_oos_value_ref.hpp src/query/partition.c src/query/query_executor.c
git diff --stat f3144ab4b b755678cd
```

추가 근거와 이전 통합 과정의 검증 범위는 [상세 조사 기록](PR7925-PR7927-dependency_b755678cd_codex.md)에 정리되어 있다. 그 기록의 절대 경로 링크는 로컬 서버에 보관된 자료를 가리키며, 외부 독자는 이 문서의 GitHub 소스·공개 검증 링크로 핵심 설명을 확인할 수 있다.

<a id="reviewer-questions"></a>
## 리뷰어 질문 찾아보기

| 질문 | 설명 |
| --- | --- |
| #7927 없이 원래 문제를 고칠 수 있는가? | [이전 독립 구현](#independent-fix) |
| 두 PR은 같은 버그를 고치는가? | [적용 누락과 저장 위치 문제의 차이](#two-problems) |
| 현재 코드만 기준 브랜치로 옮기면 왜 부족한가? | [공통 API와 메모리 보관 객체](#current-dependency) |
| #7927을 먼저 병합하는 이유는 무엇인가? | [변환 경로와 리뷰 범위를 정리하는 통합 순서](#merge-order) |
| 병합 전에는 현재 코드를 실행할 수 없는가? | [이미 포함된 구현과 실제 병합의 차이](#merge-order) |
| 이전 테스트 통과가 현재 통합의 성공을 보장하는가? | [선택별 고려 사항과 확인 범위](#choices-and-evidence) |
