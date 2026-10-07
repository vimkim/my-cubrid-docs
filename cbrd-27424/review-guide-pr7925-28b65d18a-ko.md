# PR #7925 리뷰 가이드: standalone workspace OOS 저장과 변환 레코드 소유권

<a id="revision-scope"></a>
## 비교 기준과 이 문서의 범위

이 문서는 `loaddb -S` 와 CSQL workspace 쓰기에 기존 OOS 저장 정책을 적용하는 이유, 실제 저장까지의 흐름, 그리고 완료한 리뷰 단순화 두 건을 설명한다. 분석 대상은 **사용자 승인으로 현재 로컬 PR 브랜치에 fast-forward한 `28b65d18a`** 이다. GitHub에 게시된 PR HEAD와 구분해서 읽어야 한다.

| 항목 | 기록 |
| --- | --- |
| 이슈 / PR | [CBRD-27424](https://jira.cubrid.org/browse/CBRD-27424) / [CUBRID/cubrid#7925](https://github.com/CUBRID/cubrid/pull/7925) |
| 분석한 로컬 HEAD | `28b65d18a9302b17d49281e06cb4621b86e9f24d` |
| 현재 로컬 브랜치 / 경로 | `CBRD-27424-oos-loaddb-sa` / `/home/vimkim/gh/cb/CBRD-27424-oos-loaddb-sa` |
| GitHub head repository / branch | `vimkim/cubrid` / `CBRD-27424-oos-loaddb-sa` |
| 조회 시 GitHub PR HEAD | `1c660d22e4340ee707336ad08c8b4bf4b69744de`; 로컬 통합 결과는 아직 미게시 |
| PR 대상 / 대상 tip | `feature/oos-merge` / `fb567a629cdb390fff920542173fa36f454c74a0` |
| 로컬 HEAD와 대상의 merge-base | `fb567a629cdb390fff920542173fa36f454c74a0` |
| 전체 비교 | 위 merge-base → 로컬 HEAD: 27개 파일 |
| PR7925 작업만 보는 비교 | 원래 dependency `4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c` → 원래 작업 HEAD `1932b3ec3d1b83bec83b7de1a6dd482f3a03b63d`: 8개 파일 |
| 기존 검증과의 관계 | `28b65d18a` 와 `1932b3ec` 의 전체 tracked tree가 동일: `d1e979eb0314aeb32cef369aebb010dbf84ccfae` |
| 자료 수집일 | 2026-10-07, Asia/Seoul; 수집 시점과 snapshot 범위는 [수집 기록](review-guide-evidence-28b65d18a/context.json) |

전체 diff에는 별도 이슈 CBRD-27089 / PR7927의 선행 구현이 포함된다. 이 문서에서는 그 인터페이스를 사용하는 데 필요한 책임도 설명하지만, 파티션 선택과 일반 destination/OOS 소유권 수정을 PR7925에서 새로 구현했다고 서술하지 않는다. [파일별 설명 대응표](review-guide-evidence-28b65d18a/coverage.json)는 전체 27개 파일을 해당 설명으로 연결한다.

새 HEAD는 로컬 커밋이므로 공개된 immutable GitHub 소스 URL을 제공할 수 없다. 새로운 코드의 근거 링크는 [커밋 고정 소스 찾아보기](review-guide-evidence-28b65d18a/source-map.md)로 연결한다. 각 항목에는 **full SHA, repository-relative path, 해당 커밋의 줄 번호, 짧은 발췌, `git show` 명령**이 있다. 과거 게시 소스는 해당 SHA의 GitHub 링크를 사용한다. 아직 존재하지 않는 공개 URL을 전제로 하지 않는다.

이슈 설명은 현재 조회에서 `Develop / Unresolved` 이며, 과거 구현과 Python 테스트를 기술한 부분도 남아 있다. 현재 소스와 다른 내용은 역사적 설명으로 취급한다. PR 본문, inline 1건, review summary 2건, conversation 21건을 각각 pagination하여 읽었다. 사람의 기존 APPROVED 리뷰는 게시 HEAD의 기록이며 새 로컬 HEAD에 대한 승인을 뜻하지 않는다.

### 목차

- [배경과 목표](#background)
- [코드를 읽기 전에](#reading-order)
- [force 플래그와 workspace 출처](#force-origin)
- [변환 레코드의 단일 소유권](#received-owner)
- [OOS 분리가 없는 행을 그대로 유지하는 이유](#inline-publication)
- [INSERT·예약 OID UPDATE·파티션 이동](#force-routing)
- [두 실제 저장 결과를 비교하는 테스트](#stored-row-comparison)
- [독립 기대값·컬렉션·스키마 변경](#comparison-contract)
- [실제 유틸리티 테스트와 빌드 등록](#utility-tests)
- [선행 구현: 준비·참조·finalize](#dependency-preparation)
- [선행 구현: loader·중복 키·저장 경계·복제](#dependency-callers)
- [오류·수명·성능·호환성 영향](#cross-cutting)
- [검증과 한계](#verification)
- [리뷰어 질문 찾아보기](#reviewer-questions)

<a id="background"></a>
## 배경과 목표

**작성자가 명시:** [이슈](https://jira.cubrid.org/browse/CBRD-27424)와 PR 본문의 요구는, 같은 큰 값을 일반 SQL INSERT로 저장할 때와 standalone 객체 경로로 저장할 때 기존 OOS 정책이 동일하게 적용되도록 하는 것이다. 예를 들어 5,000바이트 VARBIT 값을 읽으면 두 경로 모두 값이 맞더라도, 기존 workspace 경로는 값을 heap 행 안에 남겼다. 따라서 SELECT 값 일치만으로 원래 문제를 발견할 수 없다. 물리적인 OOS 저장도 확인해야 한다.

**코드에서 확인:** workspace 객체는 저장 전에 메모리에 있다가 직렬화된 `RECDES` 로 force 경계를 지난다. 반면 일반 SQL 쓰기는 heap attribute 변환기를 통해 OOS 배치를 결정한다. 원래 force 경로는 workspace 레코드를 바로 heap/index에 전달했다. 게시된 `1c660d22e` 는 `locator_oos_demote_workspace_record` 를 추가하여 실제 목적지를 고른 뒤 기존 attrinfo 변환기를 호출했다. 현재 구현은 선행 PR7927의 준비/finalize 경계와 그 메모리 소유자를 사용한다. [기존 helper](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L4945), [현재 force 경계](review-guide-evidence-28b65d18a/source-map.md#locator-finalize)

| 입력 | 기능 수정 전 요구를 위반한 결과 | 목표 결과 |
| --- | --- | --- |
| 일반 SQL로 큰 VARBIT INSERT | 기존 변환기가 OOS 저장 수행 | 논리 값을 유지하며 기존 정책 적용 |
| `loaddb -S` 객체 적재 | 읽은 값은 맞지만 OOS 분리가 빠짐 | 실제 OOS chunk record가 생성되고 원래 값을 읽음 |
| `csql -S` 에서 workspace INSERT 선택 | workspace 경로에 OOS 배치 결정이 빠짐 | 동일한 저장 정책 적용 |
| 작은 값·NULL·빈 값 | 기존 inline 동작 | 불필요한 OOS 분리 없이 기존 동작 |

`csql -S` 자체가 workspace 경로를 선택하는 것은 아니다. 테스트는 `insert_execution_mode=0` 이나 해당 UPDATE 경로의 트리거를 사용해 실제 workspace 쓰기를 선택한다. 또한 `STORAGE FORCE_OUTLINE` 은 작은 값에도 적용될 수 있으므로 단순한 레코드 길이 검사로 모든 변환을 건너뛰면 요구를 충족하지 못한다. [실제 utility 입력](review-guide-evidence-28b65d18a/source-map.md#utility-seed), [force 플래그](#force-origin)

이번 단순화의 목적은 새 직렬화기나 새 OOS 정책을 만드는 것이 아니다. 승인된 [spec](../.scratch/pr7925-review-simplification/spec.md)은 실제 두 행의 비교를 남기고 테스트용 세 번째 변환을 제거하며, 기존 소유자가 제공하는 변환 메모리 수명을 재사용하도록 요구한다. 파티션 선택 알고리즘, UPDATE chain 재사용, vacuum 및 저장 임계값 변경은 별도 범위다.

<a id="reading-order"></a>
## 코드를 읽기 전에

| 용어 | 여기서의 의미 |
| --- | --- |
| workspace 객체 | 아직 flush되지 않았거나 클라이언트 객체 관리 영역에서 보관하는 객체 |
| force | 최종 heap 쓰기와 관련 index 처리를 수행하는 locator 경계 |
| `RECDES` | 데이터 주소·길이·타입을 전달하는 view; 이 값만으로 데이터의 소유자가 되는 것은 아님 |
| `record_descriptor` | 레코드 버퍼를 관리하는 기존 C++ 객체 |
| OOS inline stub | heap의 변수 컬럼 자리에 남는 24바이트 참조; 저장된 것은 head OOS OID·전체 길이·identity stamp |
| OOS value chain | 한 속성의 직렬화 값을 담은 하나 이상의 OOS chunk record |
| prepared record | 실제 OOS 쓰기 전에 retained payload를 owner-local index로 참조하는 메모리상의 compact 레코드 |
| `heap_pending_record` | compact 레코드와 retained payload의 메모리 소유자; DB 페이지 롤백의 소유자는 아님 |
| publication 상태 | 다음 heap/replication 작업에 전달되는 OOS OID/LSA 상태; inline 행에도 초기화 경계가 필요 |

다음 순서로 읽으면 이유와 구현을 함께 볼 수 있다. 먼저 `locator_sr.h` 의 플래그로 workspace 출처를 확인하고, `xlocator_force` / multi-update → INSERT·UPDATE force → `locator_finalize_oos_record` 를 따른다. 그다음 `heap_pending_record` 와 prepare/finalize를 읽어 수명을 확인한다. 마지막으로 `OosWorkspaceBytes::check` 와 실제 utility 테스트를 읽어 관찰 가능한 계약을 확인한다.

```text
workspace 객체 / 받은 copy-area 행
  → xlocator_force 또는 multi-update
  → 실제 destination 선택
  → locator_finalize_oos_record
       → 필요하면 received owner로 prepare
       → destination에서 finalize / 저장 가능한 레코드 검증
  → heap 및 index 처리
  → force 반환 뒤 owner의 임시 메모리 해제

SQL 또는 server loader가 준비한 행
  → 호출자가 보유한 heap_pending_record
  → pending owner를 명시하여 partition / duplicate-key 읽기
  → 목적지에서 finalize
  → heap 및 index 처리
```

OOS의 record-level Expand, attribute-level Resolve, storage-level `oos_read` 는 서로 다른 책임이다. 비교 테스트는 Expand로 stub를 없애지 않은 실제 저장 이미지를 캡처하고, 선택된 속성 값만 `oos_read` 로 읽는다. [캡처 코드](review-guide-evidence-28b65d18a/source-map.md#comparison-capture)

<a id="force-origin"></a>
## 주요 변경 1: 플래그와 workspace 출처를 유지한다

`LOCATOR_FORCE_FLAG` 와 `locator_insert_force` 의 `force_flags` 는 호출자가 이미 갖고 있는 BU lock, 외래 키 검사 생략, bulk logging, workspace 출처를 전달한다. 이 책임이 필요한 이유는 같은 force 함수가 workspace, 일반 SQL, loader, replication, bulk insert를 모두 받기 때문이다. 모든 입력을 workspace로 취급하면 이미 준비된 입력에 불필요한 변환을 적용하고, 출처를 빼면 원래 workspace 지원이 다시 빠진다.

**무엇이 달라지는가:** merge-base의 연속 bool 인자들이 비트 플래그로 정리된다. 기존 게시 PR의 플래그 값과 의미는 현재 통합에서도 유지된다. PR7927의 `from_copyarea` 및 `pending` 인자는 별도의 입력 계약이다. `from_copyarea` 는 입력 버퍼를 다시 준비해야 하는지를, `from_workspace` 는 workspace 의미와 inline 원본 유지 분기를 나타낸다. 둘을 하나로 합치지 않는다. [플래그와 선언](review-guide-evidence-28b65d18a/source-map.md#force-flags), [workspace 전달](review-guide-evidence-28b65d18a/source-map.md#workspace-force)

| 플래그 / 입력 | 유지하는 책임과 현재 호출 |
| --- | --- |
| `LC_FORCE_FLAG_HAS_BU_LOCK` | bulk insert가 이미 보유한 BU lock 의미를 전달 |
| `LC_FORCE_FLAG_DONT_CHECK_FK` | loader가 사전에 검증한 외래 키를 force에서 다시 검사하지 않음 |
| `LC_FORCE_FLAG_BULK_LOGGING` | 기존 bulk page logging 선택 유지 |
| `LC_FORCE_FLAG_FROM_WORKSPACE` | workspace 직렬화 입력의 적용 경계와 inline 원본 유지 의미 |
| `from_copyarea=true` | 받은 행은 자체 received owner로 적응; SA에서 이 값을 일괄 false로 만들지 않음 |
| 호출자 `pending` | SQL/loader가 이미 보유한 prepared record의 소유권과 수명을 전달 |

**이 변경을 빼면:** 단순한 호출 인자 정리만 되돌린다면 런타임 이득의 문제보다 가독성과 호출 대응 검토 비용이 돌아온다. workspace 출처 전달을 빼면 reserved-OID UPDATE, 여러 행 UPDATE, partition 이동 대상 INSERT까지 기능 적용을 이어갈 수 없다. 기존 설계에 대한 [작성자의 리뷰 설명](https://github.com/CUBRID/cubrid/pull/7925#issuecomment-5725064785)은 연속 bool과 수명 중복을 실제 검토 부담으로 지적했다. 플래그화는 그 가독성 선택이며, 새로운 wire format이나 저장 형식은 아니다.

<a id="received-owner"></a>
## 주요 변경 2: 변환 레코드는 기존 received owner가 소유한다

`locator_finalize_oos_record` 는 destination 선택 후, heap/index 쓰기 전에 레코드를 준비하고 확정하는 공통 경계다. **이 책임이 필요한 이유**는 partition/constraint 판단에 필요한 논리 값과 실제 저장 가능한 OOS 참조를 서로 맞는 시점에 제공해야 하기 때문이다. 함수의 입력 `RECDES **record` 는 force의 현재 활성 view이고, `pending` 은 호출자가 이미 제공한 owner, `received` 는 받은 입력을 적응시키는 force-local owner, `converted` 는 그 버퍼를 빌리는 view다.

**왜 현재 변경이 필요한가:** 게시 PR은 `workspace_copyarea` 와 `workspace_recdes` 를 따로 두고 INSERT/UPDATE 각 종료 경로에서 copyarea를 수동 해제했다. pinned PR7927은 이미 `heap_pending_record received` 와 `RECDES converted` 를 제공한다. 기존 workspace eager 변환까지 병행하면 동일 입력을 두 번 준비하는 경로가 생긴다. 현재 구현은 별도 workspace helper·copyarea·수동 free를 없애고 `from_copyarea || from_workspace` 입력에 기존 received 준비 경계를 쓴다. [기존 INSERT 수명](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/src/transaction/locator_sr.c#L5038), [현재 finalizer와 force-local owner](review-guide-evidence-28b65d18a/source-map.md#locator-finalize)

owner는 INSERT/UPDATE 함수 진입에서 생성되고 해당 함수가 끝날 때까지 살아 있다. 따라서 `converted` 를 heap/index가 사용하는 동안 데이터가 유효하다. `heap_pending_record` 는 record 버퍼와 retained payload를 소유하며, payload는 destructor에서 해제하고 record는 기존 `record_descriptor` 의 수명 규칙을 따른다. 별도 workspace 전용 owner를 추가하지 않았다. [owner 선언·소멸](review-guide-evidence-28b65d18a/source-map.md#pending-owner)

**현재 구현을 빼고 두 변환을 유지하면:** 통합 기준 `b59f243fd` 에서 value/reference 검사 자체는 통과했지만 UPDATE 후 정확한 chunk 개수에 대한 utility 네 사례가 실패했다. 변경 후에는 동일 assertion을 유지한 채 통과했다. 이것은 해당 통합에서 중복 준비 경로 제거가 필요한 실증 근거다. 모든 UPDATE의 chain 재사용이나 vacuum 문제를 해결했다고 확대하지 않는다. [실패 기준과 수리 기록](../.scratch/pr7925-review-simplification/orchestration.md)

비용은 명시적인 `pending` 전달과 force-local view를 계속 따라야 한다는 점이다. 이를 모두 전역 상태나 숨은 owner lookup으로 바꾸지 않았다. **추론:** 이미 필요한 owner에 수명을 모으면 각 종료 경로의 workspace 전용 free를 검토할 부담이 줄어든다. 이것은 유지보수 이점이며 성능 개선의 측정 결과를 뜻하지 않는다.

<a id="inline-publication"></a>
## 주요 변경 3: OOS 분리가 없으면 원본 view를 유지하되 finalize는 생략하지 않는다

SA의 explicit workspace 입력에 대해 다음 조건을 모두 만족하면, 준비 결과로 활성 레코드를 교체하지 않는다: 별도 caller `pending` 이 없고, 원본과 준비 결과 모두 OOS가 없으며, 두 representation ID가 같다. 이 조건은 **이미 현재 표현인 inline workspace 행**에 한정된다. 오래된 표현, 이미 OOS가 있는 입력, 호출자가 owner를 제공한 입력, server 경로에는 일반 적응/finalize 규칙이 적용된다. [조건과 처리 순서](review-guide-evidence-28b65d18a/source-map.md#inline-preservation)

이 책임이 필요한 이유는 값이 inline으로 남는 경우에도 workspace가 이미 만든 현재 레코드와 header를 불필요하게 교체하지 않기 위해서다. 처음 ownership 단순화 후 Spec 리뷰에서 이 보존 조건의 누락이 발견되었고, 원래 `1932b3ec` 의 수리가 지금 HEAD에 유지된다.

```text
prepare 성공 → converted view 획득
inline 원본 유지 조건이면:
  prepared inline view를 먼저 finalize
  received의 record 버퍼를 해제하고 길이를 0으로 초기화
  converted view도 새 빈 상태로 갱신
  원본을 disk-record 규칙으로 검증한 결과 반환
그 외:
  활성 record를 converted로 전환 → owner와 함께 finalize
```

**왜 finalize를 먼저 실행하는가:** `heap_oos_finalize_record` 는 OOS가 없는 prepared 행에서도 `heap_oos_begin_insert_publication` 을 수행한다. 이전 작업의 OOS publication 상태를 정리하는 책임은 물리 OOS 분리 여부와 별개다. 단순히 버퍼를 해제하고 성공을 반환하면 이 전환과 오류 전파를 우회한다. 현재 분기는 finalize가 실패하면 그대로 오류를 돌려주며, 성공한 뒤에만 unused record 버퍼를 비운다. [inline finalize](review-guide-evidence-28b65d18a/source-map.md#heap-finalize), [버퍼 해제 동작](review-guide-evidence-28b65d18a/source-map.md#record-buffer-release)

이 분기는 OOS 판단을 위한 준비 자체를 없애지는 않는다. `FORCE_OUTLINE` 을 포함한 실제 선택 결과를 확인한 뒤 원본을 유지한다. 준비 비용이 사라졌다는 주장이나 모든 입력의 bytes가 항상 동일하다는 주장은 하지 않는다.

<a id="force-routing"></a>
## 주요 변경 4: INSERT·예약 OID UPDATE·partition 이동의 경계를 유지한다

`locator_insert_force` 는 먼저 `partition_prune_insert` 로 실제 class/HFID를 고른 뒤 공통 finalizer를 실행한다. `locator_update_force` 는 기존 객체 갱신, 예약된 주소 채움, partition 이동에 따른 다른 쓰기를 처리한다. `locator_move_record` 는 이동의 대상 INSERT에 `pending`, copyarea 출처, workspace 출처를 전달한다. 이 책임이 필요한 이유는 OOS file이 실제 destination heap에 속해야 하고, 객체 주소를 먼저 예약한 경우에도 변환이 빠져서는 안 되기 때문이다. [INSERT 순서](review-guide-evidence-28b65d18a/source-map.md#insert-force), [UPDATE와 이동](review-guide-evidence-28b65d18a/source-map.md#update-force)

**작성자가 명시:** [이슈의 수정 위치 비교](https://jira.cubrid.org/browse/CBRD-27424)는 공통 force 경계를 선택한 이유를 설명한다. loader에만 변환을 추가하면 CSQL workspace 쓰기가 빠진다. `tf_mem_to_disk` 에서 바로 OOS를 생성하면 최종 파티션과 force의 rollback 범위가 정해지기 전에 저장 부수 효과가 생긴다. 저수준 heap 쓰기에서 다시 판단하면 이미 변환한 SQL·loader·복제 입력까지 검토 범위가 넓어진다. force에서는 실제 목적지와 기존 rollback 범위를 함께 이용할 수 있으며, 그 비용으로 예약 OID UPDATE와 partition 이동까지 출처를 전달해야 한다. 이 비교는 작성자의 구조적 선택 근거이며 모든 대안을 구현한 성능 실험은 아니다.

현재 PR7925의 변화는 accepted destination을 소비하며 출처와 기존 owner를 이어주는 것이다. partition 선택 알고리즘 및 목적지 소유권 일반 수리는 [선행 구현 설명](#dependency-callers)에 속한다. 이동 호출에서 출처를 누락하면 원래 heap의 처리만 보면서 대상 INSERT의 workspace 계약을 놓친다. utility의 `WorkspaceInsertUsesReservedOid`, `PartitionMovementTransfersOwnership` 과 선행 구현의 raw copyarea/partition 사례가 이 경로를 확인한다.

이후 foreign-key 처리에서 활성 레코드가 다른 scratch 결과로 바뀔 수 있다. owner의 역할은 자신이 보유한 메모리 해제이며, destructor가 `record` 를 이전 값으로 되돌리지 않는다. 이 구분은 새 helper의 짧은 수명보다 heap/index 소비자가 실제 사용하는 view의 수명을 검토하게 한다. 일반 SQL·replication·bulk 호출의 lock/FK/logging 의미는 [플래그 대응](#force-origin)에서 함께 읽는다.

<a id="stored-row-comparison"></a>
## 주요 변경 5: 비교 테스트는 두 실제 저장 행을 따라간다

`OosWorkspaceBytes::check` 는 일반 SQL로 INSERT/commit한 행과, 그 논리 속성을 `db_get` / `db_put` 으로 새 workspace 객체에 옮겨 `locator_flush_instance` / commit한 행을 비교한다. 이 책임이 필요한 이유는 개별 변환 helper의 결과보다 실제 호출자가 저장한 행을 검증해야 하기 때문이다. 두 행 모두 OID로 캡처하므로 테이블의 우연한 순회 순서에 의존하지 않는다. [현재 check](review-guide-evidence-28b65d18a/source-map.md#comparison-check)

게시 HEAD의 테스트도 실제 workspace flush를 수행했지만, 먼저 `tf_mem_to_disk` 와 1MiB scratch 버퍼로 별도 직렬화 입력을 만들고, 추가 attrinfo 변환으로 세 번째 reference를 생성했다. 이 변환은 OOS 쓰기를 일으킬 수 있어 test-only system operation과 abort 정리가 필요했다. **별도 변환기 구현이 있었던 것은 아니다. 같은 기존 변환기를 테스트가 한 번 더 호출한 것이다.** 현재 코드는 이 수동 직렬화, 세 번째 변환, 이를 위한 system operation을 제거했다. [과거 세 번째 변환](https://github.com/vimkim/cubrid/blob/1c660d22e4340ee707336ad08c8b4bf4b69744de/unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp#L169)

| 함수 / 타입 | 책임이 필요한 이유와 변경 |
| --- | --- |
| `capture` | heap scan cache가 돌려준 bytes는 cache 종료 전 복사해야 한다. SQL/workspace 양쪽에 같은 OID 기반 캡처를 적용하고 view가 복사본을 가리키게 한다. |
| `storage_expectation` | 두 경로가 같은 오류를 내도 검출할 독립 기대값이다. 선택 속성, offset 폭, 첫 값의 직렬화 길이를 묶는다. 기대값은 변환기를 호출해 생성하지 않는다. |
| `expect_storage` | 선언 순서와 실제 저장 순서가 다를 수 있어 `def_order` 와 `location` 을 연결한다. per-attribute OOS bit, record HAS_OOS, offset 폭과 필요한 길이를 검사한다. |
| `compare` | 다른 row의 OOS OID는 일치할 필요가 없다. stub가 가리키는 값을 읽어 선택 여부와 값 자체를 비교한다. |
| 두 `check` overload | 일반 경우와 ALTER를 거친 old-representation 경우를 같은 실제 쓰기 흐름으로 실행한다. 일반 overload는 현재 기대값을 양쪽에 적용한다. |
| `TearDown` / `main` | 실제 테스트 transaction과 table 정리, SQL 환경/GoogleTest 실행을 유지한다. 없어진 test-only OOS 쓰기 정리와 구분한다. |

[캡처·기대값·비교 근거](review-guide-evidence-28b65d18a/source-map.md#comparison-capture)

**이 변경을 빼면:** 세 번째 변환에 필요한 임시 상태와 정리가 다시 필요해진다. 이는 소스 단순화의 유지보수 결과이지, 기존 테스트가 항상 틀린 결과를 냈다는 주장은 아니다. 실제 저장 비교만 남길 때는 아래의 독립 기대값을 함께 유지해야 한다. 두 경로가 공유하는 변환기에 대한 동등성 검사는 단독 oracle이 될 수 없다.

<a id="comparison-contract"></a>
## 주요 변경 6: 독립 기대값과 유효한 표현 차이를 함께 검증한다

**같은 오류를 두 경로가 공유하면 어떻게 잡는가:** `expect_storage` 는 각 행의 기대한 선택 속성과 offset 폭을 별도로 확인하고, SQL predicate는 두 행 모두 원래 값을 만족하는지 검사한다. `COUNT(*)=2` 는 하나의 경로가 행을 쓰지 않은 경우를 검출한다. schema 정보를 읽는 attrinfo는 domain 확인에 사용하며 추가 변환/OOS 쓰기를 하지 않는다. [기대값 검사](review-guide-evidence-28b65d18a/source-map.md#comparison-storage)

**왜 row bytes 전체를 `memcmp` 하지 않는가:** 서로 다른 commit 행의 MVCC header와 head OOS OID는 다를 수 있다. non-collection 값은 inline 직렬화 bytes 또는 읽은 OOS payload bytes를 비교한다. offset 폭은 같아야 하며 collection이 없으면 header를 제외한 record 길이도 비교한다. 컬렉션은 optional domain의 포함 여부로 올바른 직렬화가 달라질 수 있으므로 schema domain으로 decode하고 `tp_value_compare` 로 논리 값을 비교한다. collection이 있으면 body 길이 동일성은 요구하지 않는다. [비교 분기](review-guide-evidence-28b65d18a/source-map.md#comparison-values)

**스키마가 바뀐 경우:** `OldDiskRepresentationIsConvertedBeforeWorkspaceSerialization` 은 원래 5,000바이트 VARBIT 행을 저장한 뒤 새 default 컬럼을 추가한다. 기존 SQL 행은 이전 representation에 남아 있고, 새 workspace 행만 현재 레이아웃을 쓴다. 두 행의 값과 default, 각 representation에 맞는 OOS 선택, 첫 값의 직렬화 길이 5,008바이트를 독립적으로 검사한다. representation ID가 다름을 확인한 뒤 동일한 현재 raw layout을 요구하는 비교는 하지 않는다. 이전 컬럼과 새 default 검사는 생략하지 않는다. [스키마 변경 사례](review-guide-evidence-28b65d18a/source-map.md#comparison-schema)

유지한 비교 사례는 named 8개와 크기 경계 13개, 총 **21개**다. named 사례는 작은/NULL/빈 값, largest-first와 PREFER_INLINE, equal-size tie, offset-width 축소, 압축 문자열/JSON, 컬렉션, 넓은 VOT/다수 속성, old representation이다. 경계값은 `20, 21, 24, 25, 244, 248, 252, 3800, 4040, 4060, 32760, 32768, 65536` 이다. 논리 VARBIT 길이와 실제 직렬화 크기가 다른 점도 고정 기대값으로 검사한다. [사례 선언](review-guide-evidence-28b65d18a/source-map.md#comparison-cases)

<a id="utility-tests"></a>
## 주요 변경 7: 실제 utility 경로와 검증용 빌드 등록

`OosWorkspaceTest` 는 설치된 `cubrid loaddb -S` 와 `csql -S` 를 별도 프로세스로 실행한다. 이 책임이 필요한 이유는 `db_execute` 만으로 standalone object loader, forward/backward 객체 참조, 무시한 적재 오류를 통과하지 못하기 때문이다. `run` 은 shell 문자열 대신 argv로 실행하고, 자식에게 private registry/configuration을 지정한다. `check` / `expect_chunks` 는 논리 값 일치와 `Oos_num_recs` 를 함께 검사한다. [fixture와 utility 실행](review-guide-evidence-28b65d18a/source-map.md#utility-run)

각 사례는 독립 DB와 임시 경로를 갖는다. `seed_workspace`, `seed_references`, `seed_partitions` 는 해당 호출 경로를 만들며 `lob_files` 는 기존 외부 파일 이름과 내용을 비교한다. 성공한 DB는 native utility로 삭제하고, 실패하면 입력·출력·DB를 남기는 기존 fixture 계약을 유지한다. `SetUp` 은 16KiB DB와 결정적인 5,000바이트 VARBIT 입력을 만들고, `TearDown` 은 결과에 따라 정리한다.

| 13개 utility 사례 | 검증하는 계약 |
| --- | --- |
| `StandaloneLoaderStoresOos` | 실제 standalone loader에서 값과 물리 OOS 저장 |
| `LoaderRejectsOosBigoneButKeepsOrdinaryBigone` | OOS+bigone 거부와 일반 non-OOS bigone 허용 |
| `WorkspaceInsertUsesReservedOid` | 주소 예약 후 force되는 workspace INSERT |
| `LoaderPreservesForwardAndBackwardReferences` | 객체 간 앞/뒤 참조와 값 |
| `PartitionsOwnSeparateOosFiles` | 각 child heap의 OOS 소유권 |
| `InsertRollbackReclaimsFlushedChain` | flush 후 rollback의 OOS 정리 |
| `WorkspaceUpdateRollbackCommitAndDelete` | UPDATE rollback/commit 및 DELETE 후 값·chunk 개수 |
| `FailedUniqueLoadRollsBackWithoutOrphans` | 실패한 logged 적재의 rollback |
| `FilteredDuplicateLeavesNoOrphanAndContinues` | 무시한 중복 오류의 행별 정리와 다음 행 계속 처리 |
| `LoaderHonorsStoragePolicy` | NULL/empty/small, FORCE_OUTLINE, largest-first, multichunk |
| `WorkspaceUpdatePreservesExternalLobFiles` | 기존 BLOB/CLOB 파일 이름·내용 보존 |
| `PartitionMovementTransfersOwnership` | 이동 후 대상 heap의 소유권 및 rollback |
| `SuccessfulNoLoggingLoadStoresOos` | 성공한 no-logging 적재와 읽기 |

`unit_tests/oos/CMakeLists.txt` 는 utility 실행 파일과 serial CTest를 등록하며 전체 timeout은 240초다. `sql/CMakeLists.txt` 는 실제 저장 비교를 기존 OOS DB fixture에 연결한다. dependency deferred-write 테스트는 별도 target/180초 timeout을 쓰고, SHOW 테스트에서 fixture를 분리한다. 현재 commit은 과거 Python 회귀 파일을 추가하는 방식이 아니라 기존 OOS GoogleTest 체계를 사용한다. [빌드 등록](review-guide-evidence-28b65d18a/source-map.md#test-registration)

<a id="utility-timeout"></a>
### 실제 reviewer 질문: 느린 환경에서 정상 utility도 timeout될 수 있는가?

가능하다. `run` 의 자식은 `alarm(60)` 을 사용한다. 부모 CTest 전체 240초와 별개여서 정상적인 단일 createdb/loaddb가 60초를 넘으면 실패할 수 있다. [Greptile inline 의견](https://github.com/CUBRID/cubrid/pull/7925#discussion_r4198752049)은 바로 이 점을 지적한다. 해당 코드는 이번 단순화에서 변경하지 않았으며, assertion 약화나 timeout 조정도 수행하지 않았다. timeout 실패는 utility 출력과 종료 상태로 확인해야 한다. 현재 로컬 통과만으로 느린 CI 환경의 오탐 위험이 해소되었다고 말하지 않는다.

<a id="dependency-preparation"></a>
## 함께 읽어야 할 선행 구현: 준비·참조·finalize

아래 책임은 원래 pinned PR7927에서 가져온 것이다. PR7925는 이를 이용하며 같은 기능을 별도 helper로 다시 만들지 않는다. 단, 전체 merge-base diff에 포함되므로 리뷰어는 계약을 이해할 필요가 있다. 이 통합은 **`4be72fc` 기준 인터페이스**를 포함한다. 나중에 게시된 PR7927 `f3144ab` 의 `heap_oos_value_ref.hpp/.cpp` 분리까지 가져온 것은 아니다. 현재 `heap_oos_value_ref` 는 `heap_oos.hpp/.cpp` 에 있다.

<a id="pending-owner-contract"></a>
### `heap_pending_record`: bytes를 읽을 권한과 메모리 수명

준비 중인 행은 OOS 대상 값의 bytes를 실제 OOS file에 쓰기 전에 보관해야 한다. owner는 `m_record` 와 `m_values`, 합계 `m_bytes`, `empty/prepared/finalized/failed` 상태를 갖는다. `retain` 은 payload를 보관하고 index를 돌려주며 allocation 예외를 CUBRID 오류로 바꾼다. `resolve` 는 prepared 상태, 동일한 record allocation, index 범위, payload 길이를 모두 확인한다. `owns` 의 주소/길이 검사가 없다면 단순히 bytes를 복사한 레코드도 다른 owner의 payload를 참조할 위험이 있다. move는 allocation을 이어받고 원래 owner의 상태를 비우며 copy는 금지한다. `retained_bytes` 는 queue의 메모리 예산에 쓰인다. [owner 구현](review-guide-evidence-28b65d18a/source-map.md#pending-owner)

이 책임을 row bytes에 process pointer를 넣는 것으로 대체하지 않는다. [승인된 설계](../.scratch/pr7927-oos-review-cleanup/spec.md)의 intent는 owner를 명시하고 준비된 bytes만으로 외부 메모리 접근 권한을 주지 않는 것이다. 비용은 retained payload 복사와 명시적인 owner 전달이다. 기존 일반 `record_descriptor` 의 의미나 generic packing 형식을 전역 변경하지 않는다.

<a id="pending-reference-contract"></a>
### `heap_oos_value_ref` 와 읽기 계열: memory/disk를 같은 값 읽기 계약으로 제공

`encode_pending` 은 기존 24바이트 stub 공간에 null head OID, 전체 길이, owner-local payload index를 넣는다. 이것은 **로컬 준비 상태**다. persisted stub의 head OID/길이/identity stamp와 혼동하지 않는다. `decode` / `decode_stub` 는 속성 경계를 확인하고, null head이면 matching prepared owner로 검증한 retained bytes만 허용한다. 일반 disk 참조는 OID와 identity stamp로 해석한다. `read_into` 는 caller-owned 목적지에 memory copy 또는 `oos_read` 를 수행한다. [참조 해석](review-guide-evidence-28b65d18a/source-map.md#value-reference)

기존 attrinfo, partition 및 duplicate-key 소비자는 finalize 전에도 값을 읽어야 한다. 따라서 `heap_attrvalue_read_oos_inline`, individual/prefetched attrinfo 읽기, composite-key size/value 계산과 `heap_attrvalue_get_key` / `heap_attrvalue_get_index` 에 optional `pending` 을 전달한다. `heap_oos_read_grouped_payloads` 는 memory 참조를 복사하고 disk 참조만 `oos_read_many` 에 모은다. owner 없는 일반 호출은 disk-only 의미를 유지한다. 이 변경을 빼면 아직 OOS에 쓰지 않은 candidate의 key/partition 값을 일반 disk 참조처럼 읽을 수 없다. [읽기·index 대응](review-guide-evidence-28b65d18a/source-map.md#attribute-readers)

<a id="prepare-finalize-contract"></a>
### 준비와 확정을 나누는 이유

`heap_attrinfo_prepare_record` 는 기존 배치 계획과 직렬화를 사용하여 compact record와 retained payload를 만든다. `heap_oos_column_plan::pending_index` 는 해당 값이 아직 disk OID 대신 payload index를 써야 함을 나타낸다. `heap_attrinfo_transform_variable_to_disk` 는 그 index를 stub에 인코딩한다. `heap_prepare_oos_record` 는 받은/재분배한 기존 레코드를 읽고 LOB 복사를 제외하여 한 번 적응시키며, source MVCC header와 현재 representation을 맞춘다. [prepare 경계](review-guide-evidence-28b65d18a/source-map.md#heap-prepare)

`heap_oos_finalize_record` 는 **실제 목적지에서** retained payload의 batch를 삽입하고 같은 compact record의 stub를 OID/길이/identity stamp로 덮어쓴다. payload/result 항목을 먼저 모두 모은 뒤 batch result 주소를 빌려 vector 재배치로 주소가 깨지지 않게 한다. owner 없는 입력은 disk-record validator로 검사한다. 성공한 owner는 finalized가 되고, 실패한 owner는 failed가 되어 같은 준비의 재시도로 쓰지 못한다. 부분 OOS 쓰기가 생긴 실패는 enclosing operation이 rollback해야 한다. [확정 구현](review-guide-evidence-28b65d18a/source-map.md#heap-finalize)

이 분리를 없애고 prepare 시점에 바로 OOS를 쓰면 아직 승인되지 않은 duplicate candidate 또는 routing 전 root heap에 쓰기가 생길 수 있다. 기존 정책을 재사용하면서 쓰기의 시점을 늦추는 것이 선행 구현의 목적이다. largest-first/PREFER_INLINE/tie 정책 자체를 PR7925 단순화의 새 선택이라고 설명하지 않는다.

<a id="dependency-callers"></a>
## 함께 읽어야 할 선행 구현: 실제 호출자와 경계

<a id="dependency-loader"></a>
### Server loader와 partition

`server_object_loader` 는 `vector<record_descriptor>` 대신 `vector<heap_pending_record>` 를 보관한다. compact record만으로 queue 크기를 세면 큰 retained payload를 놓치므로 `m_retained_bytes` 와 vector capacity를 함께 세고 약 8MiB 기준에서 flush한다. 단일 큰 행은 기준을 넘을 수 있으며 즉시 flush하므로 엄밀한 최대 메모리 상한이라고 표현하지 않는다. `process_line` 은 value가 clear된 뒤에도 owner가 bytes를 보유하도록 하고 allocation 오류를 전달한다. 생성/reset/flush는 새 상태를 함께 초기화한다. [loader queue](review-guide-evidence-28b65d18a/source-map.md#loader-queue)

`m_pruning_type` 은 partition root/child를 구분한다. class 설치 단계에서 session이 child BU lock을 획득하고, worker는 그 lock을 사용한다. `flush_records` 는 partition/HA/filtered-error 경로를 행별 작업으로 처리하며 매 행의 목적지/pruning context를 만들고 owner를 force에 전달한다. partition 행은 context와 함께 unique 통계를 유지하려고 `SINGLE_ROW_INSERT` 를 사용한다. nonpartitioned bulk 경로는 `locator_multi_insert_force` 가 data page latch를 잡기 전에 OOS finalize를 끝낸다. [loader routing](review-guide-evidence-28b65d18a/source-map.md#loader-flush), [bulk 경계](review-guide-evidence-28b65d18a/source-map.md#bulk-finalize)

`partition_find_partition_for_record`, `partition_prune_insert/update` 는 prepared key 값을 읽을 때 `pending` 을 받는다. 이를 빼면 OOS로 보낼 partition key의 아직 쓰지 않은 값을 해석하지 못한다. 이 일반 routing 책임은 CBRD-27089에 있다. PR7925의 child별 값/chunk 검사 통과와 실제 shared branch에 prerequisite가 포함되었다는 것은 서로 다른 사실이다. [partition 읽기](review-guide-evidence-28b65d18a/source-map.md#partition-routing)

<a id="dependency-duplicates"></a>
### 일반 SQL, REPLACE/ODKU, 재분배

`locator_attribute_info_force` 는 attrinfo 결과를 owner로 준비하고 INSERT/UPDATE force에 전달한다. `qexec_remove_duplicates_for_replace` 와 `qexec_oid_of_duplicate_key_update` 는 candidate를 owner로 준비해 unique key와 composite/function key를 읽는다. duplicate 판정으로 폐기되는 candidate는 OOS를 쓸 필요가 없으므로 probe 시점에 finalize하지 않는다. 예전 probe 전용 copyarea free가 owner 수명으로 이동한다. 이 변경을 빼면 preparation과 실제 destination write를 분리했는데도 duplicate 검사만 기존 eager 경로에 남는다. [duplicate 경계](review-guide-evidence-28b65d18a/source-map.md#duplicate-probes)

`redistribute_partition_data` 는 source를 보존한 채 대상 INSERT용 prepared record를 만들고 owner를 전달한다. workspace/copyarea 입력과 달리 이미 caller-owned prepared row라는 사실이 명시된다. 관련 tests는 rollback, multichunk, unassigned 값, foreign-key/index 오류, duplicate candidate의 OOS 미생성을 각각 검사한다. 모든 관련 기능을 단순히 'bool 인자 정리'로 묶으면 이 계약 변화가 숨겨진다. [일반 SQL·재분배](review-guide-evidence-28b65d18a/source-map.md#sql-and-redistribution)

<a id="dependency-publication"></a>
### Heap 저장, LC_FETCH export, prefetch, replication

`heap_oos_validate_disk_record` 는 저장 직전에 정상 header와 schema에 맞는 OOS stub를 검사한다. `heap_insert_logical` / `heap_update_logical` 은 이 계약을 적용하여 owner-local index가 disk 참조처럼 저장되지 않게 한다. generic descriptor와 slotted-page metadata 전체를 row로 간주하지 않으며, root catalog/address reservation은 해당 예외를 유지한다. prepared row의 `REC_HOME` 타입만으로 disk 저장을 허용하는 것은 충분하지 않다. [disk validator와 저장 경계](review-guide-evidence-28b65d18a/source-map.md#storage-validation)

`locator_copyarea_add_fetch` 는 Expand를 요청한 fetch 생산자가 header가 올바르고 OOS stub가 없는 non-root 행만 `LC_FETCH` 에 싣도록 한다. `locator_return_object_assign`, `xlocator_fetch_all`, `xlocator_lock_and_fetch_all` 과 `heap_prefetch` 가 이 공통 export 경계를 사용한다. prefetch는 아직 Expand하지 않은 OOS 이웃을 건너뛴다. generic packing API를 바꾸는 대신 row를 내보내는 지점에서 계약을 적용한다. [export/prefetch](review-guide-evidence-28b65d18a/source-map.md#fetch-export)

`xlocator_repl_force::row_topop_active` 는 OOS 항목과 뒤따르는 heap 행을 같은 apply top operation에 묶는다. 행을 마무리하면 attach/abort하고, 불완전한 OOS group이 남으면 실패시킨다. 이를 빼면 OOS 항목과 heap 행의 실패 정리 경계가 달라질 수 있다. PR7925의 workspace flag 추가가 이 선행 replication 계약을 다시 설계하지는 않는다. [replication 작업 단위](review-guide-evidence-28b65d18a/source-map.md#replication-topop)

`test_oos_sql_heap_fixture.hpp` 의 공용 heap fixture와 분리된 deferred-write 36개 사례는 destination, payload 수명, memory/disk 접근, 오류 경계, publication을 검증한다. SHOW target은 SHOW 결과에 집중하고, eager/vacuum test builder는 정상 row header를 만드는 규칙에 맞춘다. server 테스트는 저장 guard를 추가로 확인한다. `cubrid/` 와 `sa/` CMake source list에는 owner 구현을 등록한다. 이 파일들의 변화도 [전체 coverage](review-guide-evidence-28b65d18a/coverage.json)에 포함된다.

<a id="cross-cutting"></a>
## 연결되는 영향

<a id="memory-versus-rollback"></a>
### 임시 메모리 해제와 DB rollback은 다른 책임이다

owner는 메모리만 해제한다. OOS finalize 뒤 unique/index/heap 오류가 발생하면 이미 변경한 페이지를 owner의 destructor로 되돌릴 수 없다. 기존 force/top operation과 loader의 행별 abort가 OOS·heap·index 변경을 함께 취소한다. 무시한 duplicate 오류는 해당 행을 abort한 뒤 다음 행을 처리한다. 실패 publication reset과 owner의 failed 상태도 다음 쓰기에 이전 상태를 넘기지 않기 위해 필요하다. [force/replication 경계](#dependency-publication), [실제 오류 utility 사례](#utility-tests)

<a id="metadata-and-lob"></a>
### CHN, 객체 참조, 외부 LOB와 active view

workspace 직렬화가 이미 수행한 객체 참조 배정, CHN, 외부 LOB 효과를 저장 표현 변경 때문에 반복하지 않는다. 받은 입력의 `heap_prepare_oos_record` 는 LOB 복사를 제외하고 source header를 현재 representation에 맞춘다. no-demotion 분기는 원본 header/view를 유지한다. 일반 SQL의 준비에서는 필요한 LOB 복사를 별도로 허용하므로 모든 호출에 `copy_lobs=false` 를 적용하지 않는다. 외부 LOB 데이터 파일의 lifecycle과 OOS로 분리할 수 있는 locator bytes의 eligibility는 별개의 계약이다. [prepare 구현](#prepare-finalize-contract)

현재 LOB utility는 **기존** BLOB/CLOB 파일이 UPDATE/rollback/commit 뒤에도 같은 이름과 내용을 갖는지 확인한다. 알려진 fresh-workspace LOB INSERT 결함의 전체 해결이나 모든 locator OOS 조합의 검증을 뜻하지 않는다. forward/backward 객체 참조와 reserved OID도 각각 실제 utility 사례로 확인한다.

<a id="compatibility-and-policy"></a>
### 저장 정책·동시성·복구 범위

OOS+bigone 거부는 새 단순화의 임의 제한이 아니라 기존 정책을 workspace에도 적용한 결과다. 거대 fixed 컬럼 때문에 OOS 분리 후에도 ordinary heap record로 들어가지 못하면 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE` (-1375)로 거부될 수 있다. non-OOS bigone은 계속 허용된다. no-logging은 성공한 적재/읽기를 검사하며 실패 rollback, crash recovery, same-slot identity uniqueness의 새 보장을 주장하지 않는다.

이 PR7925 작업은 SQL 문법, 외부 protocol, persisted OOS stub 크기, vacuum/UPDATE chain 재사용 정책을 바꾸지 않는다. 포함된 선행 준비 상태도 finalization 이후에는 정상 disk 참조로 바뀌어야 한다. 호출자 수명과 loader lock 순서를 확인한 로컬 회귀는 광범위한 concurrent workload나 HA/QA 전체 검증을 대신하지 않는다.

규범 OOS context는 2026-09-22 기록이다. 4-record physical target은 규범이며, 이 소스 계열의 기존 `DB_PAGESIZE/4` 사용과의 차이는 CBRD-27057의 별도 conformance gap이다. 이 문서의 특정 5,000바이트 fixture 설명을 규범 임계값의 변경으로 읽지 않는다. CDC/history 기능의 deferred scope 역시 CI 실패를 자동 면제하거나 PR7925의 merge readiness를 보장하지 않는다.

<a id="performance-evidence"></a>
### 단순화가 더 빠르다는 근거가 있는가?

현재 결론은 검토할 수명/변환 경로가 줄었다는 것이다. ticket02의 동일 Debug 구성에서 baseline `b59f243fd` 와 최종 `1932b3ec` 를 workload별 세 번 측정했다. 작은 입력의 elapsed median은 3.92→3.63초, OOS 입력은 7.40→6.73초였으나 범위가 겹친다. user/system CPU도 별도로 기록했다. **재현 가능한 regression이나 성능 개선을 주장하지 않는다.** [최종 측정 원본](../.scratch/pr7925-review-simplification/evidence/ticket02/benchmark-summary-final.json)

tree에 있는 `benchmark_workspace_oos.sh` 는 manual Release 측정 도구이고 CTest에 포함되지 않는다. private DB, 결정적인 small/large fixture, 값 검사 및 OOS 통계를 남긴다. 이 스크립트의 100,000/10,000행 설정과 위 proportionate Debug 측정의 50,000/5,000행 설정을 혼동하지 않는다. 이번 guide 작성 중 benchmark는 다시 실행하지 않았다. 과거 철회한 direct-byte 구현의 Release 측정은 [역사적 복원 근거](CBRD-27424-workspace-oos-revert-rationale_a142503dc_codex.md)이며 현재 ownership 변경의 성능 수치가 아니다.

<a id="verification"></a>
## 검증과 한계

### 소스에 있는 테스트와 이전 실행

비교 21개, 실제 utility 13개, 선행 deferred-write 36개가 tree에 존재한다. 이전 최종 private `1932b3ec` 의 configured OOS CTest는 38/38, 실제 GoogleTest는 32 XML의 374/374였으며 failure/skip/disabled는 0이었다. 별도 coordinator focus는 5 CTest의 70/70 사례를 실행했다. 최종 Standards/Spec의 source findings도 각각 0이었다. [이전 exact-revision 검증](../.scratch/pr7925-review-simplification/orchestration.md), [XML audit](../.scratch/pr7925-review-simplification/evidence/combined-final/coordinator-full-1932b3ec.json)

### 이 작업에서 실제 수행한 검증

| 이번 실행 | 결과와 범위 | 근거 |
| --- | --- | --- |
| 승인된 rebase + local fast-forward | 현재 PR 브랜치 `1c660d22e` → `28b65d18a`; 원래 private `1932b3ec` 와 전체 tracked tree 동일; merge commit 없음 | [통합 receipt](review-guide-evidence-28b65d18a/integration-receipt.json) |
| GCC Debug configure/build/install | 성공; 분석 source와 같은 rebased HEAD를 integration worktree에서 빌드 | [build log](review-guide-evidence-28b65d18a/rebased-build.log) |
| `ctest --test-dir build_preset_debug_gcc --output-on-failure --verbose` | **38/38 CTests**, 384.47초 | [현재 실행 log](review-guide-evidence-28b65d18a/rebased-ctest.log) |
| 같은 실행의 GoogleTest 감사 | **32개 실행 파일의 374/374 사례 통과**, RUN/OK identity와 binary summary 교차 확인; failure/skip/disabled 0 | [case audit](review-guide-evidence-28b65d18a/ctest-results.json) |
| 원래 사용자 수정 보존 | 현재 source의 기존 dirty CCI header SHA-256 동일; source/index에는 별도 미커밋 수정 없음 | [submodule 보존 receipt](review-guide-evidence-28b65d18a/integration-receipt.json) |

이번 case 감사는 현재 verbose log의 실제 RUN/OK 기록을 사용했다. 이번 실행에서 새 XML을 수집했다고 주장하지 않는다. 21개 비교·13개 utility·36개 dependency 사례를 포함한 374개 전체 실행이다. source 코드 변경 대신 동일한 tested tree를 rebase했고, 이번 문서 작성 중 engine 기능을 추가 수정하지 않았다.

소스 근거는 `git show` 로 고정된 commit에서 읽고, 문서의 local-only reference와 전체 file coverage를 검증한다. GitHub의 세 comment stream, PR/target 정보와 JIRA 설명을 새로 조회했다. 문서의 내부 anchor, 상대 링크, README의 파일별 index도 확인한다. 최종 실행 결과와 명령은 [verification.json](review-guide-evidence-28b65d18a/verification.json)에 기록한다.

`pr7925-simplification-integration` worktree와 branch는 남겼다. build/설치/workenv 및 verification 자료를 보존해야 하며 [doctor](review-guide-evidence-28b65d18a/cleanup-doctor.log)는 2,491개 PID의 inspection이 불가능하다고 기록한다. ready 상태는 무활동 증거가 아니므로 force 삭제나 전역 process/socket 정리는 하지 않았다. 원래 private source를 보존하는 `review/pr7925-combined-1932b3ec` 도 유지된다.

### GitHub CI와 실제 공유 통합의 한계

2026-10-07 조회에서 **게시된 `1c660d22e`** 의 [run37574973482](https://github.com/CUBRID/cubrid/actions/runs/37574973482)는 Debug/Release·SQL·medium 성공, shell 실패였다. 이 결과는 `28b65d18a` 의 CI가 아니다. 새 로컬 HEAD는 아직 push/회사 CI를 하지 않았다. 기존 APPROVED 리뷰도 새 HEAD의 승인으로 전환하지 않는다.

현재 branch가 pinned PR7927을 포함하더라도 shared `feature/oos-merge` 에 실제 prerequisite가 병합되었다는 뜻은 아니다. 최종 shared partition acceptance와 PR7925 준비 완료 판정은 별도다. 최신 PR7927의 extraction 또는 실제 squash 결과를 이후 통합할 때에는 API/include 차이를 재검토하고 관련 checks를 다시 실행해야 한다.

<a id="future-squash"></a>
### PR7927을 나중에 squash merge하면 어떻게 이어가는가?

원래 검증 결과 `1932b3ec` 와 정확한 dependency 경계 `4be72fc` 를 보존했다. 실제 승인된 updated feature tip이 생기면 별도 review branch에서 **원래 경계 뒤의 PR7925 여섯 commit만** transplant하는 방법을 유지할 수 있다. 현재 branch는 기존 PR HEAD 위에 dependency와 작업을 rebase했으므로, 아무 기준 없이 현재 전체 commit 목록을 다시 replay하지 않는다. 저장된 원래 series가 올바른 작업 경계를 복원하는 근거다. [통합 receipt](review-guide-evidence-28b65d18a/integration-receipt.json)

```sh
# 실행 예시이며 실제 source promotion을 미리 수행하는 명령은 아니다.
git rebase --onto <approved-updated-feature-tip> \
  4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c <separate-transplant-review-branch>
```

원래 경계와 tree가 같은 dependency squash를 모사했을 때 conflict 없이 동일 final tree가 나왔다는 기록은 있다. 실제 이후 `f3144ab` 변화와 feature 변경까지 무충돌이라고 보장하는 결과는 아니다. 현재 rebase에서도 초반 loader/locator 충돌을 조정했고, 최종 전체 tracked tree가 이전 tested tree와 일치함을 확인했다. 공유 통합의 불확실성은 그 실제 source 조합에서 검증한다.

<a id="reviewer-questions"></a>
## 리뷰어 질문 찾아보기

| 질문 | 답을 읽을 위치 |
| --- | --- |
| 지금 GitHub diff와 이 문서의 코드가 다른 이유는? | [분석한 로컬 HEAD와 게시 HEAD](#revision-scope) |
| 값이 원래도 맞았는데 이 기능이 필요한 이유는? | [논리 값과 물리 저장의 차이](#background) |
| `csql -S` 이면 언제나 workspace인가? | [경로를 실제로 선택하는 조건](#background) |
| 왜 loader 또는 직렬화기만 수정하지 않고 force에서 처리하는가? | [최종 목적지와 owner를 연결하는 흐름](#reading-order), [force routing](#force-routing) |
| `from_copyarea` 와 workspace 플래그가 중복인가? | [출처별 입력 계약](#force-origin) |
| `locator_oos_demote_workspace_record` 는 어디로 갔는가? | [기존 received owner 재사용](#received-owner) |
| owner 하나면 `RECDES` view는 왜 따로 두는가? | [메모리 소유권과 active view](#received-owner) |
| 분리할 값이 없는데 왜 finalize를 호출하는가? | [inline publication 전환](#inline-publication) |
| destructor가 실패한 OOS 페이지도 정리하는가? | [메모리 해제와 rollback](#memory-versus-rollback) |
| 예약한 OID로 들어오는 UPDATE와 partition 이동은? | [출처와 owner의 전달](#force-routing) |
| 비교 테스트에서 무슨 경로를 없앴는가? | [세 번째 테스트용 변환 제거](#stored-row-comparison) |
| 같은 converter의 오류가 두 행에 공통으로 생기면? | [독립 기대값과 실제 값 predicate](#comparison-contract) |
| 왜 byte equality와 컬렉션 equality가 다른가? | [MVCC/OID/optional domain 차이](#comparison-contract) |
| old representation을 현재 layout과 비교하지 않으면 약해지는가? | [값·default·storage를 독립 검사하는 ALTER 사례](#comparison-contract) |
| 실제 loader, references, ignore-error도 검증했는가? | [13개 utility 사례](#utility-tests) |
| 60초 child timeout에 대한 bot 의견은 해결됐는가? | [미변경 timeout과 느린 환경의 한계](#utility-timeout) |
| null OID가 메모리 포인터라는 뜻인가? | [index와 matching owner 검증](#pending-reference-contract) |
| preparing 중에 duplicate key/partition은 값을 어떻게 읽는가? | [memory/disk 읽기 계약](#pending-reference-contract), [duplicate probes](#dependency-duplicates) |
| loader queue의 큰 값 메모리가 제한되는가? | [retained bytes와 단일 큰 행 예외](#dependency-loader) |
| 아직 준비된 stub가 disk나 LC_FETCH로 나갈 수 있는가? | [저장과 export의 row 계약](#dependency-publication) |
| CHN, 외부 LOB, 객체 참조를 다시 만들지는 않는가? | [메타데이터와 LOB의 수명](#metadata-and-lob) |
| 기존에 성공한 bigone 적재가 실패할 수도 있는가? | [기존 OOS+bigone 정책 적용](#compatibility-and-policy) |
| no-logging이 crash/실패 rollback까지 보장하는가? | [검증한 성공 범위](#compatibility-and-policy) |
| 간결해진 코드가 더 빠른가? | [같은 구성의 측정과 주장 한계](#performance-evidence) |
| 38 CTests와 374 GoogleTests, CI 통과는 같은 말인가? | [서로 다른 검증 단위와 revision](#verification) |
| PR7927과 나중에 큰 squash conflict가 생기지 않는가? | [원래 경계와 여섯 작업 commit 보존](#future-squash) |
