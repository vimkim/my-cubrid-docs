# CBRD-27781 수정 후보 선택 보고서

목표는 OOS 삭제 rollback이 다른 값의 슬롯이나 공간과 충돌하는 문제를 해결할 후보를 비교하고, 사용자가 선택한 방안으로 수정과 테스트를 담은 초안 PR을 만드는 것이다. **다음 실험 후보로 A, 임시 페이지 제외를 추천한다.** 기존 물리 undo를 유지하면서 슬롯과 바이트 재사용을 함께 차단하는 조건을 검증하기 좋기 때문이다. 원인 판단의 신뢰도는 높다. A를 먼저 실험할 판단의 신뢰도는 중간이다. A가 작은 안전 패치라는 근거는 아직 없다.

조사일은 2026-11-03, Asia/Seoul이다. 관련 이슈는 [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781)이다.

소스 기준은 `beb3facccf38c6374a7e2a29093fd84eceab98aa`이다. `/home/vimkim/gh/cb/CBRD-27781-fix-options`의 `review/CBRD-27781-fix-options` 브랜치와 clean 상태를 확인했다. 이전 기준 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`과 대조하면 삭제 함수 변경은 bestspace 인자 제거이다. 이전 호출이 `0`을 넘겼으므로 삭제 후 힌트 갱신 조건은 같다. 청크별 delete, latch 해제, undo 순서는 유지된다. [고정된 소스 비교](https://github.com/CUBRID/cubrid/compare/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67...beb3facccf38c6374a7e2a29093fd84eceab98aa).

소스에서 확인한 현재 데이터 구조는 물리 주소를 연결한 청크 체인이다. head 참조는 OID와 identity stamp를 가지며, 청크는 다음 청크 OID를 가진다. `oos_delete_chain`은 페이지 write latch 아래 이전 레코드 전체와 슬롯을 `RVOOS_DELETE`에 기록한 뒤 `spage_delete`를 호출한다. 반복 한 번이 끝나면 latch를 푼다. `ANCHORED`, `is_saving=false`인 OOS 페이지는 이때 슬롯과 정렬된 레코드 바이트를 재사용 가능하게 만든다. [초기화와 삭제](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/storage/oos_file.cpp#L3152-L3377), [슬롯과 공간 반환](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/storage/slotted_page.c#L2079-L2117).

undo는 `oos_rv_redo_insert`를 통해 원래 슬롯에 레코드를 넣는다. `spage_insert_for_recovery`는 그 슬롯이 비어 있다고 assert한다. 따라서 보호 대상은 **원래 슬롯, 복원할 바이트 공간, 페이지 자체**이다. 다른 슬롯에 들어간 레코드도 남은 공간을 소모하면 undo를 막을 수 있다. head stamp는 stale 삭제 요청을 거부하지만 undo 공간을 예약하지 않는다. [복구 삽입](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/storage/oos_file.cpp#L3683-L3708), [복구 슬롯 전제](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/storage/slotted_page.c#L1962-L1976).

소유자는 `oos_delete` 호출 자체가 아니라 그 삭제를 되돌릴 트랜잭션 또는 sysop이다. 현재 호출 경로는 vacuum forward walk, vacuum heap REMOVE, 비-MVCC 즉시 정리이다. 즉시 정리는 살아 있는 사용자 트랜잭션의 undo를 남긴다. 해당 경로의 실제 동시 실행 가능성은 별도 검증해야 하며, 이름이나 SA 관련 로그 문구만으로 제외할 수 없다. [vacuum sysop](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/query/vacuum_oos.cpp#L155-L210), [REMOVE](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/query/vacuum.c#L2496-L2631), [즉시 정리](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/storage/heap_oos.cpp#L946-L955).

다음 비교는 제안의 비교이며 구현 검증 결과가 아니다. 코드 크기보다 보호 범위, 소유권, 실패 후 회복을 기준으로 판단했다.

| 후보 | 보호 방식 | 장점과 비용 | 결정적인 반증 조건 |
| --- | --- | --- | --- |
| **A 임시 페이지 제외** | undo 가능 기간에 해당 페이지의 모든 일반 삽입과 위험한 reclaim을 금지한다. | 기존 레코드와 WAL 형식을 유지할 가능성이 있다. 페이지 전체의 남은 공간까지 막고, 소유권 메모리와 파일 증가를 관리해야 한다. | 우회 allocator, 이른 해제, map 소실 후 prepared abort 중 하나라도 재사용을 허용한다. |
| **B1 슬롯과 바이트 예약** | 슬롯별 소유권과 정렬된 바이트 예약을 함께 유지한다. | 예약하지 않은 공간을 쓸 수 있다. slotted-page 슬롯 선택, 용량 계산, 선택적 reclaim, sysop 수명까지 바뀐다. | 바이트만 예약해 슬롯이 재사용되거나, 한 소유자 종료가 다른 소유자의 예약까지 푼다. |
| **B2 본문을 보존하는 tombstone** | 삭제 표시를 기록하고 원래 슬롯과 본문을 실제 점유한다. | 슬롯과 용량 보호를 페이지 상태로 표현한다. 영속 상태, 읽기 의미, rollback, 후속 정리와 호환성을 설계해야 한다. | 정리 도중 crash로 tail을 잃거나, 미완료 tombstone 페이지가 해제되거나, 영구 누수가 생긴다. |
| **C 영속적인 지연 삭제** | 삭제 의도와 진행 상태를 기록하고 되돌릴 수 없는 경계 뒤 청크를 해제한다. | 물리 삭제를 원래 undo 의무와 분리할 수 있다. commit 이후 오류 처리와 재시작 가능한 체인 정리까지 바뀐다. | head 삭제 후 crash하고 재실행이 없는 head를 완료로 판단해 tail을 남긴다. |
| **D 모든 청크 latch 유지** | 실제 undo 경계가 끝날 때까지 모든 관련 페이지 latch를 보유한다. | 작은 제한 실험에서 배제 효과를 비교하기 쉽다. 체인 길이와 트랜잭션 수명에 따른 pin 증가와 latch 순서 문제가 있다. | 역순 페이지 체인이 교착하거나 buffer가 고갈된다. `oos_delete` 반환 때 풀면 외부 abort를 보호하지 못한다. |

B1은 기존 플래그 두 개를 켜는 수정이 아니다. `spage_save_space`는 vacuum worker와 crash recovery를 건너뛴다. `ANCHORED_DONT_REUSE_SLOTS`는 슬롯 재사용을 막아도 본문 공간을 반환한다. 기존 `spage_reclaim`은 소유자별로 가려서 해제하지 않는다. 기존 saved-space 합계는 요청자 자신의 예약도 포함하므로, 그 코드가 자기 예약을 자유롭게 쓰게 한다고 설명해서도 안 된다. [예약 제외](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/storage/slotted_page.c#L489-L515), [예약 합계](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/storage/slotted_page.c#L678-L767), [일괄 reclaim](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/storage/slotted_page.c#L2690-L2737).

외부 비교에서 PostgreSQL은 TOAST 청크를 행으로 삭제하고, InnoDB는 delete mark와 후속 purge를 분리한다. 두 사례는 B2와 C를 검토할 이유를 제공한다. CUBRID의 고정 슬롯 undo나 abort 가능한 vacuum sysop 전체를 그대로 정당화하지는 않는다. 특히 InnoDB의 B-tree rollback을 동일 물리 슬롯 복원과 같다고 볼 수 없다. [PostgreSQL 고정 소스](https://github.com/postgres/postgres/blob/7885b94dd81b98bbab9ed878680d156df7bf857f/src/backend/access/common/toast_internals.c#L385-L439), [InnoDB MVCC 설명](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html), [InnoDB 고정 purge 소스](https://github.com/mysql/mysql-server/blob/0896fcd61dec11a0904166911a0126f59daaa1bf/storage/innobase/row/row0purge.cc#L171-L192).

A의 제안 데이터 구조는 파일과 페이지의 현재 incarnation에 연결한 보호 항목과, 그 항목을 소유하는 트랜잭션·sysop 수명별 토큰 집합이다. 페이지 하나에 여러 삭제 소유자가 존재할 수 있다. 단일 transaction ID, descriptor 주소, sysop 깊이만을 키로 삼으면 재사용과 중첩을 구별하지 못한다. 시스템 descriptor는 외부 sysop 종료 때 LSA를 초기화한다. [시스템 descriptor 수명](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/transaction/log_system_tran.cpp#L144-L170).

아직 해결하지 않은 증명 의무는 다음과 같다.

- 중첩 소유권은 commit, abort, attach를 구분해야 한다. 독립 commit은 자기 의무만 끝내고, abort는 마지막 undo까지 보호하며, attach는 부모에게 넘긴다. savepoint rollback은 새 sysop로 이전 트랜잭션 기록을 되돌리므로 현재 stack만 보고 해제할 수 없다. 초기 A에서는 부분 rollback 뒤에도 트랜잭션 종료까지 보호하는 보수적 선택이 가능하다. [sysop 종료](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/transaction/log_manager.c#L4127-L4224), [부분 rollback](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/transaction/log_manager.c#L5692-L5727).
- 같은 소유자의 재사용도 막아야 한다. 바깥 삭제 뒤 안쪽 sysop가 삽입을 독립 commit하면 바깥 abort와 충돌할 수 있다. 예외 허용은 실제 로그 순서와 소유권 증명이 있을 때만 검토한다.
- 메모리 상한에 도달하면 아직 보호하지 않은 삭제 전에 실패해야 한다. 이미 보호한 페이지는 rollback 완료까지 유지한다. 활성 항목 축출, 무제한 chain pin, 자기 종료를 기다리는 대기는 허용할 수 없다. 페이지 latch 아래 짧은 map 접근을 하고, map lock을 잡은 채 페이지를 기다리지 않는 순서를 기존 heap·bestspace·reclaim 순서와 대조해야 한다.
- prepared 2PC의 삭제 undo가 재시작 이후 남을 수 있는지 확인해야 한다. 가능하면 해당 보호를 WAL에서 재구성하거나 동등한 제한을 유지해야 한다. 일반 복구가 client 재개 전에 끝난다는 사실만으로는 충분하지 않다. 현재 redo 종료부는 in-doubt MVCC ID를 재활성화하고 postpone을 실행한다. 그 작업이 보호 대상 공간을 할당할 수 있는지도 열려 있다. [redo 종료 순서](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/transaction/log_recovery.c#L4069-L4082).
- WAL과 재시작 순서를 증명해야 한다. runtime 보호로 충돌하는 committed 재사용 기록이 생기지 않는다는 주장은 가설이다. parallel redo, 복구 중 재장애, page 재할당과 file drop까지 확인해야 한다. 이미 충돌한 이전 로그 이력은 A가 복구해 주지 않는다. B와 C의 새 영속 상태에는 기존 페이지와 로그 호환성 판단도 필요하다.
- C의 postpone은 단순 commit callback으로 취급할 수 없다. sysop postpone은 sysop-end 기록 전에 실행되며, 현재 호출자는 recovery callback의 오류 반환을 버리는 경로가 있다. commit 결정 이후 실패에는 durable retry 또는 fail-stop 정책과 청크별 진행 기록이 필요하다. [실행 순서](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/transaction/log_manager.c#L3981-L3994), [오류 반환 처리](https://github.com/CUBRID/cubrid/blob/beb3facccf38c6374a7e2a29093fd84eceab98aa/src/transaction/log_manager.c#L8636-L8644).

모델 결과는 위 의무의 일부만 다룬다. coordinator가 실행한 현재 코드 모델은 OOS 슬롯 반례를 찾았고, 코드 동기화 검토가 필요해 exit 3을 반환했다. 해당 drift는 위 소스 비교에서 힌트 갱신 리팩터링임을 확인했다. `oos_chunk_release=after_sysop_end`를 가정한 모델은 OOS 슬롯 속성을 통과했다. 이 모델은 latch 보유로 배제 효과를 표현한다. A의 map을 구현하거나 검증한 결과가 아니다. 바이트 용량, 중첩 소유권, 메모리 상한, prepared 2PC는 이 결과로 증명하지 못한다. 별도 forward heap 슬롯 속성은 계속 실패해 가정 모델 전체 exit는 1이다. 이 CBRD-27858 문제는 OOS 청크 보호만으로 해결되지 않는다. `policy-models/results.json`, `policy-models/current.log`, `policy-models/hypothetical_chunk_exclusion_until_sysop_end.log`. 같은 모델의 속성별 독립 실행도 동일한 구분을 보인다. `statechart-results.json`.

과거 실행 증거는 별도이다. 이슈 초안은 `224104a36a37d42847ed0852f312cca9be31e431`의 debug 테스트에서 삭제 페이지 재사용과 재시작 empty-slot assert를 기록한다. release 손상은 소스 추론이며 실행 결과가 아니다. 이번 head에서 빌드나 runtime 재현을 수행하지 않았다. [당시 실행 기록](https://github.com/vimkim/my-cubrid-jira/blob/b89dc2bd34c15c312bddf9ee91e10a3b3738858c/issues/CBRD-27781-oos-slot-reuse-rollback-undo_dcbf09e_claude.md#test-build).

A 초안의 최소 제안 범위는 `oos_file.cpp`의 삭제 전 등록, 모든 최종 삽입 결정과 reclaim 검증, transaction·sysop 종료 및 필요 시 recovery 재구성이다. 삭제 전에 page latch 아래 등록하고, 삽입은 같은 latch 아래 최종 검사해야 한다. 일반 삽입은 소유자 자신도 제외한다. recovery 삽입은 복원 의무에 맞게 허용한다. bestspace cache에서만 제외하거나 vacuum 호출 두 곳에만 적용하는 범위는 충분하지 않다. 2PC 보호를 기존 WAL로 재구성할 수 없다면 A의 무형식변경 가설을 철회하고 B2와 C를 다시 비교해야 한다. 미래 A-prime 등이 호출자를 바꾸더라도 삭제 권한과 삭제 뒤 undo 보호는 각각 검증해야 한다.

선택 후 초안 PR에서 필요한 검증은 다음과 같다.

- 첫 청크 삭제 뒤 동기화 지점을 두고 동일 슬롯 재사용과 다른 슬롯을 통한 바이트 고갈을 각각 시도한다. abort 뒤 원래 체인과 경쟁자가 commit한 체인의 전체 payload와 stamp를 검사한다. head와 continuation, 같은 페이지의 여러 소유자를 포함한다.
- vacuum 두 경로와 도달 가능한 즉시 정리에서 실패를 주입한다. 독립 sysop commit, attach 후 부모 abort, 중첩 abort, statement 오류, savepoint rollback 뒤 추가 쓰기, 시스템 descriptor 재사용을 검사한다.
- delete WAL, page flush, commit 경계, undo 중간에 crash한다. 복구 중 재장애를 반복하고 debug와 release 모두 데이터를 검사한다. prepared 2PC와 redo-time postpone은 도달성 증거 또는 실제 재현을 남긴다.
- map 할당 실패와 상한, 긴 체인, 반대 페이지 순서, bestspace 누락, file drop과 page 재할당을 검사한다. 활성 보호가 사라지지 않고 종료 후 슬롯과 페이지가 다시 회수되는지 확인한다. 기존 no-logging 제한도 별도로 검증한다.
- 기존 stale-reference 회귀와 전체 호출자 보호를 재검증한다. forward heap 슬롯 결함은 별도 결과로 유지한다. B2나 C를 선택하면 영속 상태 전환마다 재장애, 중복 실행, callback 실패와 tail 회수 검증을 추가한다.

사용자의 후보 선택은 해당 방안의 엔진 수정, 테스트, 검증 결과를 포함한 초안 PR 진행을 승인한다. 안전성 확인이나 merge 승인은 아니다. 현재 권한은 조사와 비교까지이며, 코드 수정과 PR 개설은 하지 않았다. A의 핵심 의무가 실패하면 다른 후보를 조용히 대신 구현하지 않고 반증과 수정된 선택지를 제시한다.

`Prove It Works` 원칙에 따라 head, diff, 복구 함수와 모델 로그를 직접 대조했고 소스 사실, 가정 모델, 과거 실행, 제안을 분리했다. 원자료와 세 분야 조사 보고서는 `/home/vimkim/temp/cbrd27781-fix-options-20261103/`에 보존한다. 위 모델 경로도 이 디렉터리를 기준으로 한다. 원자료는 저장소에 커밋하지 않는다. 이번 조사에서 엔진 변경, 빌드, 서비스 변경과 PR 개설은 하지 않았다.


재실행 도구는 [check-release-policies.py](probes/check-release-policies.py)이다. `Build the Lever` 원칙에 따라 비교 명령, 고정 revision, 가정 여부, 속성별 결과와 원래 종료 코드를 남긴다. 저장소에는 비교 보고서, 색인, 이 도구와 [검증기 fingerprint](probes/release-policy-toolchain.json)를 보존한다. 실제 실행 명령은 다음과 같다.

```sh
python3 cbrd-27781/probes/check-release-policies.py \
  --repo /home/vimkim/gh/cb/CBRD-27781-fix-options \
  --rev beb3facccf38c6374a7e2a29093fd84eceab98aa \
  --checker /home/vimkim/.agents/skills/cubrid-verify-vacuum-slot-undo/scripts/check.py \
  --out /home/vimkim/temp/cbrd27781-fix-options-20261103/policy-models-pinned
```

다시 실행할 때는 `--out`에 새 경로를 지정한다. 이 도구는 기존 증거를 덮어쓰지 않는다. 실행 종료 1은 위에서 설명한 forward 속성 실패를 보존한 결과이다. chunk 속성 통과를 전체 모델 통과로 바꾸지 않는다.

OOS 요구사항은 canonical `OOS-CONTEXT.md`의 §4이다. 조사 때 전체 문서의 SHA-256은 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`이었다. 현재 요구사항은 청크 삭제의 원자적 sysop과 동기식 eager 정리를 포함한다. C처럼 삭제 시점이나 원자성 경계를 바꾸는 방안은 사양과 맞는지 별도로 결정해야 한다.

독립 증거 검토의 두 지적을 도구에 반영했다. 검증기 Python 코드, TLA+ 모델, known findings와 coverage 선언의 SHA-256이 기록된 파일과 다르면 실행 전에 거부한다. 검증기 본체는 이 문서 저장소에 포함하지 않는다. 동일한 외부 파일을 별도로 확보해야 하므로 이 네 파일만으로 실행 환경이 완성되지는 않는다. TLC 1.7.4 jar는 검증기가 별도로 checksum을 검사한다.

종료 코드는 각 실행의 1이나 3을 마지막까지 유지한다. `628857607265880ef7bbdda4973b1b6f06e8b797`에서 current checker와 가정 실행이 모두 drift 코드 3을 반환하는 실제 모델 조합을 실행했고 wrapper도 3을 반환했다. 가정 실행에서는 세 속성이 모두 통과했지만 동기화 검토 요구를 숨기지 않았다. 본 조사 head에서 재실행한 결과는 원래 속성 결과와 같고 종료는 1이다. 별도 복사본의 모델을 바꾸자 checker 실행 전 종료 2로 거부했고 출력 디렉터리도 생성하지 않았다. 이는 재현 도구 검증이며 A 엔진 수정 검증이 아니다.
