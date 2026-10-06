# 목적지 선택 뒤 OOS를 기록하는 inline RECDES POC

목적: PR #7927의 대안이 **코드를 단순화할 수 있는지** 확인한다. 성능 개선은 필수 조건으로 두지 않았다.

기준: `feature/oos-merge` 의 `fb567a629cdb390fff920542173fa36f454c74a0`.
POC: 로컬 브랜치 `CBRD-27089-oos-insert-poc`, 커밋 `b81d943d2f1c07996d38619ebfd2ad67e71116f4`.
worktree: `/home/vimkim/gh/cb/CBRD-27089-oos-insert-poc`.
검증일: 2026-10-06. 기존 PR의 본문·소스 브랜치는 변경하지 않았다.

## 판단

**일반 SQL INSERT/UPDATE의 동기 호출 범위에서는, 새 행 소유 객체 없이 목적지 선택 뒤 OOS를 기록하는 구현이 가능했다.** 기존 파티션 평가기를 유지하면서 일반 테이블, 부모 경유 INSERT, 자식 직접 INSERT, 자식 간 이동 UPDATE를 실행했다. 실패한 문장의 부분 OOS 기록도 롤백되는 것을 확인했다.

다만 기존 PR 전체의 대체안으로 채택한 것은 아니다. loader·복제·REPLACE/ODKU·별도 재평가 경로는 새 경로에 연결하지 않았다. 작은 지원 범위 때문에 코드가 짧아진 부분을 전체 설계의 우월성으로 계산해서는 안 된다.

부모와 자식의 호출 순서는 별도의 [팀장 보고용 코드 근거 보고서](CBRD-27089-partition-insert-call-flow_fb567a629_codex.md)에 설명했다.

## 구현 흐름

```text
기존 DB_VALUE → 행 변환
  │  OOS demotion을 생략하고 모든 값을 inline RECDES에 보존
  ▼
기존 파티션 평가기로 목적지 선택
  ▼
heap_attrinfo_insert_inline_oos(destination, recdes)
  ├─ VOT에서 이미 직렬화된 컬럼 길이·위치 수집
  ├─ 기존 선택 함수로 OOS 대상 결정
  ├─ 확정된 목적지의 OOS 파일에 값 기록
  └─ 같은 RECDES 버퍼에서 값 → stub 교체, VOT 재작성
  ▼
heap 저장 및 index/FK 처리
```

같은 heap의 UPDATE는 기존 코드에서 index/FK 처리가 heap UPDATE보다 먼저이므로, 목적지 선택 뒤 index 갱신 전에 같은 OOS 함수를 호출한다. 다른 자식으로 이동하는 UPDATE는 목적지 INSERT에 위임한 뒤 반환하므로 중복 외부화하지 않는다.

| 변경 지점 | 역할 |
|---|---|
| `src/query/query_executor.c` | 일반 INSERT 두 호출과 일반 UPDATE 호출만 명시적으로 opt-in |
| `src/transaction/locator_sr.c:5083` | INSERT 목적지 확정 뒤 공통 OOS 함수 호출 |
| `src/transaction/locator_sr.c:6057` | 같은 heap UPDATE의 index 갱신 전 공통 함수 호출 |
| `src/storage/heap_file.c:12915` | 직렬화된 값의 기록과 같은 버퍼 안에서의 축소 |
| `heap_attrinfo_determine_disk_layout()` | 기존 선택 정책 공유; 길이 입력만 DB_VALUE 또는 RECDES에서 공급 |

줄 번호는 POC 커밋 기준이다. 소스 커밋은 로컬에만 있으며 공개 GitHub 링크가 아니다.

## 무엇이 단순해졌는가

| 항목 | PR #7927의 prepared-row 방식 | 이번 제한된 POC |
|---|---|---|
| 값의 소유 | 컬럼별 바이트와 compact 레코드를 새 객체가 소유 | 기존 copyarea의 RECDES가 전체 inline 값을 소유 |
| 파티션 키 읽기 | prepared-row의 값 읽기 경로가 필요 | 기존 RECDES 읽기 경로 사용 |
| 수명·상태 | 별도 객체와 building/prepared/consumed/completed 상태 | 동기 locator 호출의 수명, 한 번 실행하는 제어 흐름 |
| OOS payload | 보관한 컬럼 바이트 참조 | RECDES 내부 바이트 참조 |
| 완료 결과 | 객체에서 완성된 RECDES를 얻음 | 기존 RECDES 버퍼와 length를 갱신 |
| 남는 구현 비용 | 여러 입력 경로에서 사용할 소유·변환 인터페이스 | inline 레코드 축소 함수와 opt-in/attrinfo 인자 전달 |

POC의 엔진 소스 변경은 5개 파일에서 280행 추가·35행 삭제다. 여기에 테스트 132행과 로그 제외 규칙 4행을 추가했다. 줄 수는 검토 범위를 나타낼 뿐, 지원 범위가 다른 PR과의 단순화 점수는 아니다.

기존 `HEAP_CACHE_ATTRINFO` 는 동기 호출 동안 빌린다. 새 컬럼 소유 컨테이너는 없다. 다만 길이, 원래 offset, variable→attribute 인덱스, OOS plan/request를 담는 지역 vector는 필요하다. **상태를 전부 없앴다는 뜻은 아니다.**

`consumed` 같은 공개 재시도 방지 상태는 추가하지 않았다. 현재 호출 경로에서 한 번만 실행하고 오류를 반환한다. 실패한 버퍼를 임의로 다시 시도할 수 있는 범용 인터페이스로 확장하려면 이 계약을 다시 검토해야 한다.

## 바이트와 오류 처리

- SQL 식, INCR/DECR, 외부 LOB 복사를 다시 수행하지 않는다. 이미 직렬화된 바이트를 사용한다.
- OOS 함수가 입력 바이트를 모두 소비하기 전에는 원본 버퍼를 수정하지 않는다.
- 선택된 값은 24바이트 stub보다 크고 VOT 폭도 커지지 않는다. 따라서 fixed/bitmap과 남는 inline 값을 `memmove()` 로 앞으로 이동할 수 있다. 늦은 OOS 함수 자체는 행 전체 복사 버퍼를 추가하지 않는다.
- CHN·MVCC header·목적지 representation ID는 보존한다. OOS summary bit와 offset 폭만 바꾸고, VOT의 OOS/LAST flag와 padding을 다시 쓴다.
- 이 helper의 버퍼 준비와 OOS+BIGONE 검사는 OOS 기록 위임 전에 끝낸다. 기록 실패는 기존 statement rollback으로 전파한다.
- 현재 내부에서 생성한 full-inline 행과 전체 attrinfo가 입력이라는 계약이다. raw/복제 입력을 검증 없이 받는 범용 API로 소개해서는 안 된다.

선택 정책은 기준 브랜치의 현재 구현을 유지했다. 기준 코드의 raw `DB_PAGESIZE/4` 와 OOS 규격의 물리 용량 목표 사이에 있는 기존 차이는 이 POC에서 수정하지 않았다.

## 실행 검증

| 검증 | 결과 | 확인한 범위 |
|---|---|---|
| Debug 빌드·설치 | 성공 | 서버·SA·클라이언트 대상 컴파일 |
| 구성된 CTest | 35/35 통과, 187.12초 | 기존 OOS storage/CRUD/rollback/BIGONE/vacuum/recovery 등의 구성된 테스트와 새 SQL 테스트 |
| 보강한 집중 SQL 테스트 | 3/3 통과, 16.57초 | 추가한 statement rollback 검증까지 최종 소스로 재실행 |
| 실제 SERVER_MODE SQL | 검증 통과 | 부모/자식 소유 파일, 이동 UPDATE, 이동 롤백, 같은 heap UPDATE, 값 유지 |
| 스타일 검사·diff 검사 | 통과 | 포맷터 반복 적용이 동일하고 커밋 hook 통과 |

CTest 이후 엔진 변경은 주석과 선언 줄바꿈뿐이다. 최종 빌드와 보강한 집중 테스트를 다시 수행했다. 시간은 검증 실행 시간이며 성능 벤치마크가 아니다.

새 SA 테스트는 다음을 확인한다.

1. 부모 OOS 레코드는 0, 각 자식이 자기 OOS 파일을 소유한다. 이동 UPDATE의 롤백 후 값과 체인 수가 복원된다. 성공한 이동 후 SA eager cleanup으로 원래 자식 체인이 정리된다.
2. 파티션 키 자체가 FORCE_OUTLINE 대상이어도 라우팅된다. fixed/variable NULL, 40KB 값, VOT 축소와 파티션 이동 뒤 값이 유지된다.
3. 첫 OOS 값 기록 후 강제 실패와 index 중복 오류에서, 명시적인 전체 트랜잭션 롤백 **이전부터** 실패 문장의 새 OOS 레코드가 남지 않는다. 일반 테이블 INSERT/UPDATE도 같은 경로에서 동작한다.

실제 서버 실행의 주요 결과:

```text
initial_values       2
moved_uncommitted    1
rollback_values      1
moved_committed      1
same_heap_update     1

부모: Has_oos_file=0, Oos_num_recs=0
p0:   OOS VFID=(volid=1, fileid=960), OOS 레코드 4개
p1:   OOS VFID=(volid=1, fileid=1024), OOS 레코드 1개
```

파일 식별자는 해당 실행에서 관찰한 값이다. OOS 레코드 수는 value chain 수와 다르다. 40KB 값은 여러 chunk record를 사용한다. 서버 모드의 이전 버전 체인은 vacuum까지 남을 수 있으므로 SA의 즉시 삭제 개수와 비교하지 않았다.

재실행 가능한 서버 SQL은 소스의 `unit_tests/oos/sql/cases/destination_oos_poc_server.sql` 에 있다. 별도로 준비한 일회용 서버 DB에서 아래처럼 실행한다.

```sh
csql -C -u dba --no-auto-commit -t -N \
  -i unit_tests/oos/sql/cases/destination_oos_poc_server.sql <database>
```

검증 출력 발췌는 [evidence](../.scratch/pr7927-oos-insert-poc/evidence/validation.json)에 보관했다.

## 비용과 남은 판단

중간 행은 OOS 적용 전의 **전체 inline 크기**를 유지한다. 큰 행에서는 기존 copyarea의 확장·복사 경로가 더 큰 버퍼를 다루게 된다. 늦은 함수에서 행 전체 복사를 없앴다고, 전체 파이프라인의 복사가 없어진 것은 아니다. 추가 비용은 컬럼 길이·offset 순회와 남는 inline 바이트 이동이다. 최대 메모리나 처리량을 prepared-row와 동일 조건으로 비교한 벤치마크는 수행하지 않았다.

loader는 DB_VALUE를 정리한 뒤 행을 큐에 보관한다. 이번처럼 기존 attrinfo를 잠깐 빌리는 연결을 그대로 적용할 수 없다. 복제 입력은 이미 완성된 OOS stub을 포함할 수 있으며, REPLACE/ODKU는 실제 기록 전 probe 변환이 있다. 이 경로들을 추가할 때도 코드가 단순하게 유지되는지가 다음 채택 판단의 핵심이다.

이번 결과는 **동기 SQL 경로에서의 단순화 후보로는 성립한다**는 증거다. 기존 PR을 교체하거나 통합 브랜치에 병합하는 결정과 분리해, 비교 가능한 로컬 POC로 남긴다.
