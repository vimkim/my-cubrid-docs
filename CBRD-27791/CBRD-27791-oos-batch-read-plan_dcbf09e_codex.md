# CBRD-27791: OOS batch read 구현·검증 계획

작성: 2026-10-28, Asia/Seoul. 독자: OOS 읽기 경로의 구현·검증 담당자.
Work Item 537. 관련 [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791),
[TODO parent CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978),
[PR #7990](https://github.com/CUBRID/cubrid/pull/7990).

## 목표와 현재 결정 범위

큰 OOS 값을 조회할 때 발생하는 읽기 대기를 현실적인 batch read로 줄이고, 작은 컬럼만 읽는 이득과 정확성을 유지하는 것이 목표다.
이 문서는 [재측정·소스 분석](CBRD-27791-oos-batch-read-analysis_dcbf09e_codex.md)을 바탕으로 후속 구현을 나눈다.
엔진 패치, 새 인터페이스의 채택, 성능 예산의 합의, 회사 회귀 통과를 선언하지 않는다.

분석 source는 `CUBRID/cubrid`의 `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`이다.
비교 base는 `4781495f01523a3ecc5891e3377ad62cf876a1cd`이다.
별도 CPU 개선 PR #8299의 `bcb900d`는 측정에 포함하지 않았다.
향후 구현 착수 시 실제 시작 SHA와 PR #8299 포함 여부를 다시 기록한다.

CBRD-27791은 CBRD-26978 아래의 성능 후속 Sub-task다. 이를 PR #7990의 merge 선행 조건으로 지정한 결정은 확인하지 못했다.
따라서 독립 성능 개선 과제로 계획하며, 통합 일정과의 관계는 담당자가 명시적으로 결정한다.

## 보존해야 할 계약

규범 근거는 [OOS 사양](https://github.com/vimkim/cubrid-oos-context/blob/main/OOS-CONTEXT.md)이다.
이번에 읽은 파일의 SHA-256은 `6300aa1fa6ffb54033b9c7f7ea959466e9d88f0530e1ab0d7178b4459d4fcf63`이다.
사양의 문서 수정일은 2026-10-27이다. 구현 관측과 채택된 요구사항을 구분한다.

- 같은 snapshot에서 가시적인 heap record의 OOS inline stub을 사용한다. 과거 버전은 undo의 stub과 해당 chain을 읽는다.
- 해제되거나 다른 용도로 바뀐 head page는 slotted page로 해석하지 않는다. slot·identity stamp·head index·길이 검증은 payload 공개 전에 수행한다.
- OOS page latch와 heap watcher 규칙을 보존한다. 정렬된 주소라는 이유로 여러 page latch를 잡고 기다리는 경로를 새로 만들지 않는다.
- heap `PEEK` record, lazy attribute cache와 scratch buffer를 scan advance 이후에 빌린 채로 보관하지 않는다. 필요한 record/stub을 복사하거나 재검증 가능한 소유권을 정한다.
- 정상 demand read의 결과 복사와 `DB_VALUE` 수명을 보존한다. 성공하지 않은 batch의 부분 payload를 SQL 값으로 공개하지 않는다.
- 사용하지 않는 속성의 Resolve를 강제하지 않는다. predicate short-circuit, 오류 발생 시점, LIMIT와 취소의 동작도 확인한다.
- 모든 영구 page 접근은 page buffer 계약을 따른다. raw `pread` 실험을 엔진의 storage 접근으로 옮기지 않는다.

## 소유 층과 Interface 후보

현재 `heap_oos_read_grouped_payloads`는 한 record의 요청 속성만 모은다.
`oos_read_many`는 같은 head VPID를 공유하는 요청의 fix를 줄이지만, 연속 I/O를 발행하거나 행을 모으지 않는다.
따라서 구현은 다음 책임을 분리해야 한다.

| Module | 책임과 호출자가 알아야 할 계약 |
| --- | --- |
| heap scan의 bounded collector | 가시적인 record에서 필요한 참조만 수집한다. row/attribute 대응, snapshot, row·page·byte 상한, scan advance와 취소 수명을 소유한다. |
| OOS read scheduler | head 참조와 caller-owned destination을 원래 요청과 연결한다. 같은 page를 묶고, 아직 발견하지 못한 continuation 주소를 미리 가정하지 않는다. |
| page buffer | cache hit, 동시 miss, BCB 예약·공개, DWB, TDE, page 검증을 유지한다. 연속 읽기나 선행 읽기의 새 seam이 필요하면 이 층에서 제공한다. |
| scalar fallback | 지원하지 않는 scan·표현식·메모리 조건에서는 기존 경로로 정확히 진행한다. |

가시성·predicate 필요성을 아는 scanner가 collector 후보이며, `file_io`가 행 batch를 소유하는 안은 피한다.
`FILE_OOS`는 logical file이므로 VFID 하나를 OS 파일 하나로 취급하지 않는다. 읽기 묶음은 실제 volume과 page 주소로 나눈다.

### 대조할 두 구현 후보

| 후보 | 기대 효과 | 비용과 실패 조건 | 판별 방법 |
| --- | --- | --- | --- |
| bounded row 요청을 모아 기존 page-fix 경로로 demand read 순서를 변경 | 연속 I/O를 추가하기 전에 순서 효과를 검증할 수 있다. 기존 identity·복사 경로를 재사용한다. | 여러 record와 값의 수명을 보관해야 한다. predicate 평가 순서·메모리·first-result 지연이 커질 수 있다. 현재 `oos_read_many`의 이중 순회를 큰 span에 그대로 확대하면 CPU 비용도 확인해야 한다. | 순서만 바꾼 replay와 native prototype을 비교한다. 제한된 read-only serial scan부터 적용한다. |
| scanner가 모은 bounded VPID 힌트를 page buffer에 선행 전달하고 demand Resolve는 유지 | lazy 평가와 값 공개 순서를 유지하기 쉽고 payload buffer를 전부 보관하지 않아도 된다. | prefetch가 cache를 오염시키거나 불필요한 I/O를 만들 수 있다. 힌트를 모으는 scan 수명 문제는 여전히 남는다. raw 정렬 결과만으로 효과를 증명할 수 없다. | demand 순서를 유지한 native prototype에서 읽기 대기·불필요 page·Q1·LIMIT를 측정한다. |

첫 후보는 읽는 순서의 효과를 직접 확인하기 좋고, 두 번째는 기존 lazy Resolve와의 결합을 검토하기 좋다.
최종 선택은 native prototype의 정확성·성능·메모리 측정으로 정한다. 두 구현을 모두 제품에 남기기로 결정한 것은 아니다.
`fileio_read_pages`를 heap/OOS에서 직접 호출하는 안은 page buffer 계약을 제공하지 못하므로 후보에서 제외한다.

## 구현을 나눌 순서와 중단 기준

이번 수치로는 **bounded 순서 변경을 먼저 native에서 검증**하는 편이 타당하다.
같은 64 heap-page 모델의 정렬 3.449초가 인접 병합 3.974초보다 빨랐으므로 syscall 병합을 기본 전제로 넣지 않는다.
짧은 OOS run만 묶은 경우는 4.409초로 원래 4.413초와 비슷했다. 따라서 한 행 또는 짧은 구간의 grouped Resolve 확대만으로 충분하다고 보지 않는다.
gap 병합의 1.965초와 요청량 72.4% 증가는 추가 I/O 예산을 따로 결정해야 할 근거다.
첫 prototype의 window 탐색에는 request 32/128/512와 heap-page 16/64 모델을 참고하되 제품 기본값으로 채택하지 않는다.

| 단계 | 산출물 | 선행 조건 | 검증·중단 기준 |
| --- | --- | --- | --- |
| A. 적용 범위와 계약 확정 | 대상 scan, 요청 필요성 판단, fallback, row/page/byte 상한, 오류·취소·소유권 문서 | 이번 분석과 실제 구현 시작 revision 확인 | `PEEK`/lazy 수명과 short-circuit을 보존할 수 없으면 적용 범위를 줄인다. |
| B. bounded collector와 순서 prototype | 요청을 원래 row/attribute에 대응시키는 최소 변경, 기본 비활성 또는 제한된 적용 | A | 메모리 상한 초과·unsupported scan은 scalar fallback. 같은 입력의 결과·오류가 달라지면 성능 평가를 중단한다. |
| C. page buffer 연계 후보 비교 | 기존 demand-fix 순서 변경 또는 bounded prefetch의 native 대조 | B | cold Q4의 차이가 반복 변동 범위 안에 있거나 작은 컬럼 이득을 훼손하면 후보를 재검토한다. raw replay 개선만으로 통과시키지 않는다. |
| D. 필요할 때만 연속 page read | page buffer 내부의 안전한 batch I/O와 실패 처리 | C에서 syscall 병합의 추가 가치 확인 | BCB 동시 miss·DWB·TDE·부분 read·공개 순서를 증명하지 못하면 이 단계를 보류한다. |
| E. 집중 정확성 및 성능 회귀 | 아래 matrix의 결과와 최종 적용 정책 | 선택한 후보 | 합의한 정확성·성능·메모리·latency 기준을 모두 충족해야 한다. |
| F. 리뷰·CI | engine PR과 연결된 testcase, exact-head CI 근거 | E | 수정한 층에 맞는 CTest/SQL/shell/medium을 선택한다. PR 정책의 전체 CI는 별도 수행한다. |

첫 탐색은 replay에서 사용한 제한 범위를 참고하되, request 수를 row 수로 바꾸어 해석하지 않는다.
제품 상한은 **rows, distinct pages, encoded/staged bytes, 한 번의 I/O 크기, 대기 시간**을 각각 제한하도록 설계한다.
큰 값 하나가 byte 상한을 넘으면 scalar 경로로 보내고, batch를 무한히 키워 수용하지 않는다.

## 정확성 검증

| 영역 | 집중 확인 항목 |
| --- | --- |
| 값과 순서 대응 | 0/1/다중 OOS 속성, 같은 page의 다른 slot, 서로 다른 page·volume, NULL/inline 혼합, 중복 참조, unordered 요청의 원래 destination 대응 |
| multi-chunk | head를 읽어야 다음 주소를 알 수 있는 frontier, 서로 다른 chain 길이, 잘못된 index/length, 부족·초과 payload, 실패 후 부분 결과 미공개 |
| identity와 동시성 | deallocated/retyped page, 빈/재사용 slot, stamp 불일치, concurrent UPDATE/DELETE/vacuum, 오래된 snapshot·undo record, batch 중 scan 재시도 |
| 수명과 자원 | heap page unfix·scan advance·attribute cache 재사용 후에도 값 유지, allocator 실패, interrupt/cancel, 조기 종료·LIMIT, latch/pin 누수 없음 |
| lazy 평가 | 작은 컬럼만 읽는 Q1에서 OOS Resolve 없음, short-circuit으로 건너뛴 값의 오류를 미리 발생시키지 않음, 선택도가 낮은 조건의 불필요 읽기 |
| page buffer 확장 시 | cache hit와 dirty page를 disk image로 덮어쓰지 않음, concurrent miss, DWB, TDE, volume 경계·EOF·부분 read·I/O 오류 |

현재 revision의 기존 결함을 batch가 새로 만든 결함과 혼동하지 않도록 unmodified engine에서도 같은 집중 대조를 실행한다.
알려진 OOS ownership/vacuum 미완료 사항은 별도 이슈와 구분하며, batch가 그 결함을 해결했다고 주장하지 않는다.

## 성능 검증과 판정

Native SQL과 offline replay는 별도 표로 유지한다. native prototype은 동일 source 계열의 독립 설치·DB로 비교한다.
저장 형식이 달라지면 DB를 새로 만들고 기존 artifact를 보존한다.

1. 우선순위는 재현된 overflow Q4의 파일 캐시 해제 요청 조건이다. heap Q4, Q5와 Q1을 함께 유지한다.
2. restart-only와 warm을 구분한다. 전역 cache 해제를 사용하지 않고, 작업 전용 정지 volume에만 해제 요청한 뒤 residency를 기록한다.
3. 작은 값/큰 값, 단일/다중 속성, 단일/multi-chunk, buffer 안/밖, 선택도와 LIMIT는 설계 위험에 맞춰 추가한다. 모든 축을 전수 조합하지 않는다.
4. 엔진 순서를 교대하고 warmup·반복·간섭을 기록한다. 최종 합격 판단은 tracer 없는 native SQL로 한다.
5. wall/CPU/instructions, fetch/ioread, OS read_bytes, 요청량·추가 읽기, peak memory와 **실제 첫 행 또는 첫 batch 반환 시간**을 수집한다.

최종 시간 개선율, Q1 허용 회귀, peak memory와 first-result latency 예산은 **TBD — ANALYSIS에서 합의**한다.
기존 CBRD-27785의 일반 heap CPU 2% 예산이나 진단용 1.5배 marker를 이 이슈의 합격 기준으로 전용하지 않는다.
우선 prototype의 진행 조건은 정확성 통과와 반복 변동을 넘어서는 native 개선이다.
gap 읽기는 속도뿐 아니라 요청·OS I/O 증가와 동시 workload 영향을 따로 승인할 수 있어야 한다.

## 이번 작업의 완료점

이번 산출물은 재측정 보고서·기계 요약·재생 도구와 이 구현 계획, CBRD-27791의 로컬 본문 초안이다.
실제 엔진 구현·PR 생성·CI 실행은 후속 작업이다. JIRA 본문 게시 및 문서 저장소 통합은 승인된 범위에서 진행한다.
