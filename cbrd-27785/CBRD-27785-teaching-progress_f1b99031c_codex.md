# CBRD-27785 보고서 학습 진행표

팀원에게 읽기 최적화의 변경 이유, 실행 경로와 근거의 한계를 설명하기 위한 진행표다.
설명한 범위와 남은 범위를 기록한다. 체크 표시는 설명을 제공했다는 뜻이며,
학습자의 이해나 발표 준비가 검증됐다는 뜻은 아니다.

작성일과 수정일은 2026-10-30, Asia/Seoul이다.
학습 대상은 `CUBRID/CUBRID`의 `f1b99031c0402d521a785815f107be7a83b27717`이다.
주교재는 [읽기 최적화 코드 해설서](CBRD-27785-code-walkthrough_f1b99031c_codex.md)다.
[질문집](CBRD-27785-learning-questions_f1b99031c_codex.md)은 이전 질문형 진행의 응답과 교정 기록을 보존한다.
전체 학습 작업은 work-tracker 620번으로 추적한다.

## 현재 진행 방식

2026-10-30의 요청에 따라 `pstack-teach`로 질문 없이 설명한다.
한 번에 한 주제를 짧게 설명하고, 사용자가 요청한 깊이와 방향을 따른다.
되묻기, 퀴즈와 재답변 검사를 진행하지 않는다.

설명이 끝난 항목을 체크하고 다음 항목으로 이동한다.
추가 설명이 필요해지면 관련 항목을 다시 열고 이유를 남긴다.
새 주제는 현재 목표에 필요한 경우에만 추가한다.
이후 shared reader와 UPDATE revision은 이 진행표의 범위에 포함하지 않는다.

<a id="teaching-todo"></a>
## 학습 TODO

- [x] T01. 일반 값도 공통 reader를 거치며 OOS 전용 scratch를 별도 helper로 분리한 이유를 설명한다.
- [x] T02. 지역 scratch와 동적 메모리 할당, stack 예약 크기와 실행 instructions 개수를 구분한다.
- [x] T03. 배열 선언의 블록 위치만으로 생성된 stack frame 축소를 보장할 수 없음을 설명한다.
- [x] T04. helper 반환 후 지역 scratch의 수명이 끝나는 문제와 Resolve·변환을 같은 수명에 묶는 이유를 설명한다.
- [x] T05. 일반 inline bytes와 임시 OOS bytes의 수명, COPY 요청과 type handler의 기존 계약을 설명한다.
- [x] T06. record의 `HAS_OOS`, 개별 필드의 `IS_OOS`, 요청한 OOS 속성 수에 따른 scalar·grouped 선택을 설명한다.
- [x] T07. 기존 record layout 재사용, offset 폭과 길이 계산, collection의 물리 순서 처리를 설명한다.
- [x] T08. 일반·without-OID·lazy 읽기와 index-key 소비자의 연결 및 변경 범위를 설명한다.
- [x] T09. NULL·기본값·구 representation·pending owner와 오류 시 정리가 유지되는 경로를 설명한다.
- [x] T10. 코드 diff와 성능 비교의 기준 revision, instructions와 경과 시간, 테스트 및 측정 범위의 한계를 설명한다.
- [ ] T11. 앞의 내용을 팀 발표 순서로 정리하고, 예상 질문에 대한 설명을 준비한다.

## 다음에 이어갈 위치

다음 항목은 T11의 팀 발표 순서와 예상 질문에 대한 설명 정리다.
T10에서는 코드 diff의 base `dcbf09e4f`와 성능 증가율의 분모인 통합 전 고정 기준
`4781495f0`를 구분했다. 학습 소스는 `f1b99031c`다.
기존 기록의 메모리 상주 일반 heap 200,000행 스캔 두 건에서 서버 `instructions:u`는
통합 전 기준보다 약 +1.11%, +1.36% 많았고, 실행 순서를 뒤집어도 비슷했다.
이는 당시 두 heap/heap 스캔에 적용한 +2% 범위였다는 기록이며, 같은 비율의 SQL 경과 시간
단축이나 최신 PR 전체의 합격을 뜻하지 않는다. Warm scan의 I/O read 0과 실제 heap 저장을
확인했다고 보고돼 있으므로 큰 값의 I/O 이득을 측정한 결과로 해석하지 않는다.
기존 측정은 실행당 20회 스캔, 질의별 2라운드의 각 5회 실행 중 첫 실행을 제외한 방식이다.
최종 표본의 instructions 범위가 중앙값의 0.009% 미만이었다는 것도 기존 기록이며 새 실측은 아니다.

기존 기능 측 빌드에는 `CUBRID_UNIT_TEST_ENABLED`가 포함됐고 baseline에는 이 OOS 테스트
코드가 없었다는 차이를 함께 설명했다. 동일한 모든 production 조건의 성능 보장으로 확대하지 않는다.
기존 집중 CTest 15/15, snapshot·vacuum 3/3과 characterization 4/4는 과거 실행 결과다.
UPDATE, heap/OOS·overflow/OOS 비교, 큰 데이터 I/O 이득과 전체 HA·복구 검증은 이 읽기
측정의 결론 밖에 있다. 근거와 전체 source SHA는 [기존 분석·검증 기록](CBRD-27785-oos-read-performance_bcb900d_codex.md)에 있다.

이번 학습에서는 실측 엔진 `e77ffbf0e3c4a2dcf1f3a918bafcabf91ac136cd`와 학습 revision 사이의
`src`·`unit_tests` diff가 비어 있음을 확인했다. 학습 revision과 공유용
`bcb900d1696756a120ec0a2b7885c212f71ebc07` 사이에는 `src`·`unit_tests`·`contrib` diff도 없다.
이는 소스 대응을 확인한 것이며, 학습 revision의 바이너리를 새로 빌드하거나 raw 성능 로그를
재감사한 것은 아니다. 이번 학습에서 엔진 테스트·성능 측정·CI를 새로 실행하지 않았다.

## 보충 설명 기록

### T08. Lazy 읽기와 회귀 원인의 구분

T08 보충으로 lazy 읽기의 의미를 설명했다. Heap record를 이미 가져온 뒤에도,
속성을 `DB_VALUE`로 읽는 작업은 그 값이 실제로 필요할 때까지 미룰 수 있다.
실행기가 `a` 조건을 먼저 평가하고 그 결과만으로 AND가 거짓이면, 뒤 조건의 `b`는
읽지 않아도 된다. 이는 SQL에 적은 순서가 평가 순서를 보장한다는 뜻은 아니다.
이 구현은 먼저 평가할 속성을 즉시 읽고 나머지를 lazy 상태로 두며,
`heap_attrvalue_peek_lazy`가 처음 접근할 때 읽는다. 같은 행에서 다시 접근하면 읽은 값을 재사용한다.
근거는 고정 학습 revision의 `src/storage/heap_file.c:12008`과 `:12389`다.

T08의 추가 보충에서는 회귀 원인과 수정의 영향을 받는 소비자를 구분했다.
lazy는 불필요한 속성 읽기를 건너뛰는 방식이고, 실제로 읽을 때는 공통 scalar reader를 호출한다.
따라서 공통 reader의 OOS 대응 비용을 줄이는 수정이 lazy 소비자에도 연결되는 것이며,
lazy 선택 로직 자체가 회귀 원인으로 입증됐다는 뜻은 아니다.
OOS 통합 전 기준 `4781495f01523a3ecc5891e3377ad62cf876a1cd`의
`src/storage/heap_file.c:11462`에도 lazy 읽기 함수가 있다.
수정 전 feature `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`와 학습 revision 사이에는
이 lazy 읽기 함수의 본문이 같다는 점도 확인했다.
[기존 진단 기록](CBRD-27785-oos-read-performance_bcb900d_codex.md)은 일반 행의 reader와 loop를
기준 구조로 바꾸면 추가 instructions가 줄고, 원상 복구하면 다시 늘었다고 기록한다.
이는 공통 읽기 경로의 OOS 대응 준비·dispatch 비용을 뒷받침하며,
scratch·inlining·코드 배치 각각의 기여율을 분리한 증거는 아니다. 새 측정을 수행한 것은 아니다.

### T10. 원본 리뷰 댓글과 학습 범위

원본 내용을 다시 묻는 요청에 따라 GitHub API로 shparkcubrid의 두 댓글 본문을 확인했다.
[2026-10-27 첫 보고](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6434778190)는
PR `4408135c`와 통합 전 develop `4781495f`의 release 빌드 비교이며,
일반 행 스캔 +8~10%, 큰 OOS 컬럼 스캔 +40%, 일반 UPDATE +7%를 보고했다.
6KB 값 테이블에서는 작은 컬럼 UPDATE +72%, 큰 컬럼 UPDATE +34%, 좁은 컬럼 스캔 -23%였다.
큰 컬럼 스캔의 wall time 2.5배는 instructions +40%와 구분된 관측값이고,
원문도 공유 호스트에서 wall-clock 변동이 컸다고 밝혔다.

[2026-10-28 상세 보고](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209)는
같은 고정 develop 기준의 서버 user-space instructions를 4라운드 중간값으로 제시했다.

| 작업 | 리뷰어가 보고한 instructions 변화 |
| --- | ---: |
| 일반 테이블 풀 스캔 | +8.0% |
| 일반 테이블 조건 스캔 | +9.9% |
| 일반 테이블 UPDATE, 20만 행 | +7.0% |
| 6KB 값 테이블의 큰 컬럼 스캔, length | +40.6% |
| 6KB 값 테이블의 큰 컬럼 스캔, substr | +38.7% |
| 6KB 값 테이블의 작은 컬럼 UPDATE, 2만 행 | +73.7% |
| 6KB 값 UPDATE, 5000행 | +34.6% |
| 6KB 값 테이블의 좁은 컬럼 스캔 | -23.1% |

두 댓글 모두 데이터가 메모리에 올라간 조건이다. 상세 댓글에는 비교한 feature의 전체 SHA가
명시돼 있지 않으므로, 그 수치를 현재 PR head의 재측정 결과로 쓰지 않는다.
리뷰어는 일반 테이블 비회귀, 기본 설정의 4~16KB 행 전체 읽기 비회귀,
현재 PR 버전의 OOS 이득과 손해 공유를 병합 전 조건으로 제시했다.
위 증가율은 허용치가 아니라 관측된 회귀다.
이 댓글에서 리뷰어가 +2% 허용치를 승인한 것은 아니다.

학습 중인 읽기 최적화는 일반 행 읽기의 회귀를 주로 다룬다. 약 +1.11%, +1.36%는
재구성한 두 일반 heap 스캔의 기존 결과이며 원댓글 전체 workload의 해결 증거가 아니다.
실제 큰 OOS 값 읽기의 40%대 비용과 UPDATE 비용은 별도 범위로 구분한다.

### T10. 원문 재현 방법을 사용한 후속 기록

원문이 재현 방법까지 제공했다는 지적에 따라 초기 재구성 하네스 이후의 기록도 조사했다.
10월 27일 보고서의 "원본 SQL이 제공되지 않았다"는 설명을 10월 28일 이후의 전체 작업에
적용하지 않는다. 이후에는 원문 DDL과 SQL을 사용한 실행 기록이 있다.

[공통 reader·UPDATE 후속 보고서](CBRD-27785-shared-read-update_408d135_codex.md)는
고정 develop `4781495`, 미수정 feature `dcbf09e`, 개선본 `408d135`의 3-way 비교를 기록한다.
대상은 원문 일반 테이블의 풀 스캔·조건 스캔·UPDATE다.

| 작업 | feature / 고정 develop | 개선본 / 고정 develop |
| --- | ---: | ---: |
| 일반 풀 스캔 | +7.02% | +0.64% |
| 일반 조건 스캔 | +8.32% | +1.36% |
| 일반 UPDATE | +5.35% | +1.66% |

이 표는 후속 소스의 회귀 방향과 개선을 보여 주며 원댓글의 비율과 정확히 일치하는 결과는 아니다.
일반 UPDATE의 별도 +5.0158% 관측도 후속 보고서에 남아 있으므로 전체 +2% 완료로 해석하지 않는다.
[선별 결과 JSON](pr-threeway-20261028/results.json)의 retained counters에서 중앙값을 재계산해
표와 일치함을 확인했다. 기록된 UNIT_TEST 옵션은 세 variant 모두 OFF다.

원문을 직접 읽는 하네스와 원시 자료도 다음 경로에 있다.

```text
/mnt/nvme/data-5/tmp/CBRD-27785-reviewer-20261028
/mnt/nvme/data-5/tmp/CBRD-27785-threeway-20261028
```

`reviewer.py`는 저장한 원댓글 JSON에서 DDL을 추출한다. 보존된 seed SQL은 테이블 prefix와
COMMIT·통계 갱신 추가를 제외하면 원문 DDL과 같았다. 3-way에서는 큰 값 테이블을 제외하고
일반 테이블만 사용했다. 6개 완료 summary의 SQL sample 90개가 원문 일반 질의와 같은 형태이고,
각 summary의 하네스 hash도 보존된 `harness.py`와 일치함을 확인했다.

큰 값까지 포함한 원시 실행은 `base/final-a/summary.json`과
`original_repeat/final-b/summary.json`에 있다. 각 8개 작업의 sample 40개, 작업당 첫 회를
제외한 4개 표본이 남아 있다. 두 summary의 SQL sample 80개는 원문 질의 형태와 일치한다.
이 디렉터리에는 매 UPDATE를 새 복제본에서 시작한 실행과 같은 테이블에 연속 수행한 실행이
따로 있으며, 큰 값 UPDATE의 관측 방향과 크기가 달랐다. 원문은 각 UPDATE 표본의 시작
상태를 상세히 정하지 않았으므로 이를 같은 물리 이력의 재현으로 단정하지 않는다.

위 단일 방향 pair의 기존 retained instructions 중간값을 다시 계산하면 큰 값 `length`는
+26.21%, `substr`는 +15.27%다. 원문의 +40.6%, +38.7%와 같은 수치는 아니다.
작은 컬럼 UPDATE는 새 복제본에서 -5.90%, 연속 UPDATE에서 +135.49%였고,
큰 컬럼 UPDATE는 각각 -1.76%, +251.01%였다. 각 비교는 작업·엔진당 첫 회를 제외한
4개 표본이다. 원문의 4라운드 검증과 같지 않다.
두 UPDATE 방식 사이의 기록된 source hash·binary identity·설정은 같았지만,
DB 이력과 실행 시점의 모든 차이를 통제한 인과 실험은 아니다. 이는 저장된 진단 기록의
재계산이며, 새 벤치마크나 원문 수치에 대한 확정 판정이 아니다.

원시 metadata의 HEAD 표시는 실제 실험 소스를 충분히 식별하지 못한다.
`original_repeat/final-b`의 세 storage source hash는 `4408135c`와 `dcbf09e`의 해당 파일과
일치하지만, 두 commit의 전체 `src`는 7개 파일에서 다르다. 원댓글의 후속 표에는 feature의
전체 SHA도 없다. 따라서 이 기록만으로 원문의 +40%·+74%를 동일 조건에서 수치까지
검증 완료했다고 판정하지 않는다. 이번 조사는 기존 파일·SQL·hash·요약값 확인이며,
새 벤치마크 실행이나 모든 native counter·DB 상태의 재감사는 아니다.

### T10. Instructions와 재현성 판정

같은 바이너리·데이터 상태·실행 경로·계수 구간을 통제했다면 instructions에는 안정적인
재현성을 기대해야 한다. 큰 차이를 단순한 공유 호스트의 시간 변동으로 설명하지 않는다.
`instructions:u`는 정적 assembly의 명령 개수가 아니라, 계수 구간에 user mode에서
실제로 retire한 명령 수다. 정의는 [Linux perf event 문서](https://man7.org/linux/man-pages/man2/perf_event_open.2.html)에 있다.
보존 하네스는 `perf stat -p <cub_server pid>`로 서버 프로세스를 대상으로 센다.
따라서 질의 처리 외의 서버 작업이 구간에 포함되거나 실제 읽기·갱신 경로가 달라지면
계수가 달라질 수 있다. 이것은 원인 후보이며 이번 차이의 확정 원인으로 쓰지 않는다.

실제로 큰 값 `LENGTH`의 절대 계수부터 다음처럼 달랐다.

| 기록 | develop instructions | feature instructions |
| --- | ---: | ---: |
| 원댓글의 4라운드 중간값 | 186.1M | 261.7M |
| 보존된 단일 방향 pair의 유효 4표본 중간값 | 294.1M | 371.2M |

두 기록의 develop 소스 표시는 같은 `4781495f`지만, 이것만으로 원댓글과 보존 실행의
바이너리·실행 계획·물리 데이터 상태·계수 경계가 같다고 입증하지는 못한다.
현재는 원문과 동일한 조건의 수치 재현이 확인되지 않았고, 그 불일치 원인도 미확정이다.
유사한 회귀 방향을 관측한 기록과 원문 수치의 검증 완료를 구분한다.
이 차이만으로 원댓글이 틀렸다고 단정하지도 않는다.

### T10. Release 빌드와 재현 절차 대조

보존된 8개 질의 pair의 baseline·feature와 후속 일반 테이블 3-way 모두 CMake cache는
`RelWithDebInfo`다. CUBRID의 `build.sh`는 `release`를 이 build type으로 설정한다.
각 variant의 저장된 `compile-commands.json`에서 서버 `heap_file.c`의 실제 옵션은
`-O2 -DNDEBUG -finline-functions -ggdb -fno-omit-frame-pointer`였고,
`CUBRID_UNIT_TEST_ENABLED`는 없었다. 보존 cache의 모든 `UNIT_TEST*` 옵션도 OFF다.
따라서 CUBRID 기준 release 빌드는 맞으며, `RelWithDebInfo`라는 이름만으로
비최적화 debug 빌드라고 판정하지 않는다. 원댓글의 전체 compiler command는 없으므로
리뷰어와 컴파일러·전체 옵션이 동일하다는 검증까지 마친 것은 아니다.

원댓글의 SQL을 사용했다는 사실과 전체 측정 절차를 그대로 반복했다는 주장을 구분한다.
앞서 인용한 큰 값 포함 pair는 다음 차이가 있다.

| 항목 | 원댓글 | 보존된 8개 질의 pair |
| --- | --- | --- |
| 데이터·질의 | 제공한 DDL·8개 SQL | 원문 DDL로 seed 생성, 같은 형태의 8개 SQL 사용 |
| 측정 테이블 생성 | 제공한 INSERT로 생성 | seed에서 `ORDER BY id`로 복제하고 통계 갱신 |
| 반복 | 4라운드, 각각 5회 중 첫 회 제외 | 1라운드, 5회 중 첫 회 제외 |
| UPDATE 시작 상태 | 표본마다 초기화하는지 명시하지 않음 | 매 표본 새 복제본, UPDATE와 COMMIT을 계수 구간에 포함 |
| 빌드 | release로 기재 | 실제 O2·NDEBUG와 테스트 옵션 OFF 확인, 원문 전체 옵션과의 일치는 미확인 |

두 완료 summary의 round 값은 0 하나뿐이고, 각각 8개 작업·40표본·warmup 8개다.
따라서 정확한 표현은 원문 SQL을 사용한 별도 재현 실험이며, 원문의 전체 절차를
동일하게 반복한 검증 완료 기록은 아니다. 복제·통계·UPDATE 이력·반복 수의 차이가
관측된 절대 instructions 불일치의 원인이라는 인과관계도 아직 입증하지 않았다.
원문과 동일한 develop 절대 계수를 얻는지부터 확인한 뒤 회귀율을 대조해야 한다.

## 지금까지 답변에서 확인한 내용

질문형으로 진행하던 시기의 기록이며, 앞으로 퀴즈를 계속한다는 뜻은 아니다.

- 일반 읽기마다 동적 메모리 할당을 한 것은 아니라는 구분을 학습자가 직접 설명했다.
- 조건문 안으로 배열 선언을 옮겨도 stack frame 축소가 보장되지는 않는다는 결론을 답했다.
  `implementation-defined`라는 표준 용어와 컴파일러의 코드 생성 선택은 구분해 설명했다.
- helper 반환 후 지역 scratch의 주소를 계속 사용하는 수명 문제를 답했다.

기존 보고서의 성능 결과는 이 학습 진행표의 새 실측이 아니다.
설명한 항목 수를 이해도 점수나 성능 검증 결과로 해석하지 않는다.
