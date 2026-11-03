https://jira.cubrid.org/browse/CBRD-27785

## Purpose

- OOS 통합 후 일반 테이블의 읽기와 UPDATE에 남은 CPU 비용을 줄입니다.
- AS-IS: header를 반복 해석하고 일반 UPDATE에도 OOS 계획과 추가 owner를 미리 만듭니다. grouped 읽기는 별도 변환 루프를 사용합니다.
- TO-BE: 일반 값과 미리 읽은 OOS 값을 공통 속성 reader에서 변환합니다. layout과 writer 정보를 재사용하고 OOS 상태는 필요한 경우에만 만듭니다.

## Implementation

- grouped 읽기는 여러 OOS 값을 미리 가져오고, 공통 eager 루프와 속성 reader가 값 변환·COPY를 처리합니다. 임시 버퍼는 소유한 경로에서 해제합니다.
- 단일 OOS 값의 Resolve(행 밖에 저장한 값을 읽어 오는 단계)는 noinline 함수 `heap_attrvalue_read_oos`가 맡습니다. 16KB 임시 버퍼는 이 함수에만 있어서, 속성 reader를 inline하는 레코드 읽기 함수의 stack에는 들어가지 않습니다.
- 가변 필드의 offset은 검사된 공통 decoder로 읽습니다. offset 폭 switch의 실패 분기는 strict release 컴파일을 위해 유지합니다.
- UPDATE 크기·강제 OOS 선택 계산과 writer의 header·offset 폭을 재사용합니다. 추가 pending owner는 copy-area/workspace 입력일 때만 만듭니다.
- `heap_attrinfo_determine_disk_layout`은 계획용 메모리 할당 실패를 한곳에서 `ER_OUT_OF_VIRTUAL_MEMORY`로 바꿉니다. stack 배열을 쓰는 기준값은 배열 길이에서 계산합니다.
- OOS로 옮길지 정하는 기준을 OOS 명세의 4-record 목표(16KB page에서 4,060B)로 맞춥니다. 병합되지 않은 [CBRD-27057](https://jira.cubrid.org/browse/CBRD-27057) 수정에서 `heap_oos_inline_target_size()`를 가져와 layout 판정·중단 조건과 workspace 입력의 준비 생략 조건(`heap_oos_needs_record_preparation`)에 씁니다. 이전 기준 `DB_PAGESIZE / 4`(4,086B)에서는 판정값이 4,061~4,086B인 행이 inline에 남아 한 page에 세 개만 들어갔습니다.
- OOS SQL 테스트는 grouped 읽기의 버퍼 해제, 많은 OOS 컬럼, 빈 가변 필드, offset 표의 끝, 재사용 슬롯의 NULL, 임시 버퍼 COPY, 4-record 목표의 경계(4,011B는 inline, 4,012B는 OOS)와 workspace flush 경계를 고정합니다.
- 벤치마크 `bench.py`는 서버·DB·설치본과 fixture 내용을 검증합니다. 잘못된 증거는 regression(exit 1)이 아니라 invalid(exit 2)로 거부합니다.

## Remarks

- 현재 head는 `4c3c8d791`입니다. [전체 CI run 41485345491](https://github.com/CUBRID/cubrid/actions/runs/41485345491)에서 release·debug 빌드, SQL, shell, medium이 모두 성공했습니다.
- 로컬에서 `4c3c8d791`의 debug OOS CTest 44/44가 통과했습니다. 기준 변경 전 코드에서는 새 경계 테스트의 4,012B가 inline에 남아 실패합니다. strict GCC 8.5 컴파일(SA·SERVER)은 `5837393ff`에서 확인했습니다.
- `-fstack-usage`로 잰 레코드 읽기 함수의 stack frame은 이전 head `f8114e432`의 16.6~16.8KB에서 128~336 bytes로 줄었습니다.
- release 비교에서 서버 명령어 수는 `f8114e432`보다 측정한 5개 경우(narrow·wide·일반·조건 scan, UPDATE) 모두 0.47~1.82% 적었습니다. 11-03 재측정에서도 0.46~1.81% 적었습니다. 판정은 회귀 없음이며 속도 개선으로 주장하지 않습니다.
- cycles는 11-03 조용한 시간대에 서버 시작 단위로 다시 쟀습니다(ABBA 12라운드). 측정 전에 정한 회귀 기준(2% 넘게 나빠짐, p<0.01, 라운드 사이 일관)에는 해당하지 않았습니다. 다만 narrow scan은 서버 시작마다 두 상태로 갈려, `5837393ff`는 22번 중 11번 약 14% 느렸고 `f8114e432`는 0번이었습니다.
- 느린 시작도 명령어 수는 같고, 분기 예측 실패의 97%가 이 PR이 바꾸지 않은 [`px_scan_result_handler.cpp:2028`](https://github.com/CUBRID/cubrid/blob/5837393ffb9d69bccb93271d63b0e38b884e0ed4/src/query/parallel/px_scan/px_scan_result_handler.cpp#L2028)의 분기 하나에서 났습니다. 코드 배치에 따라 생기는 현상으로 보며, 다른 변경으로도 그 비율이 바뀔 수 있습니다.
- 위 stack과 `f8114e432` 대비 명령어 수·cycles는 `5837393ff`에서 잰 값이며, `4c3c8d791`에서 다시 재지 않았습니다. 벤치마크 fixture의 값은 80B라 이번 기준 변경으로 저장 형태가 바뀌지 않습니다.
- develop `4781495` 대비 성능은 11-03에 `4c3c8d791`에서 다시 쟀습니다. 서버 명령어 수 기준이며, 좋아지면 +, 나빠지면 −로 적습니다. 일반 테이블의 풀 스캔은 +0.79%, 조건 스캔은 −0.83%, UPDATE는 −1.34%(중앙값)입니다. DB locale은 `en_US.utf8`이며 테이블 문자셋은 따로 기록하지 않았습니다.
- UPDATE는 COMMIT 뒤 비동기로 도는 vacuum이 측정 구간에 들어온 표본에서 더 나쁘게 나오며, 계산상 최악은 약 −7.9%입니다. 그래서 성능 저하 2% 이내 기준을 모든 표본에서 충족하지는 않습니다. 작성자는 남은 저하를 수용해 먼저 통합을 제안하며, 이 수용을 리뷰어 승인으로 해석하지 않습니다. 원인 분석과 남은 측정은 [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816)에서 추적합니다.
- TC 변경은 없습니다. [공개 TC PR #3898](https://github.com/CUBRID/cubrid-testcases/pull/3898)과 [비공개 TC PR #4589](https://github.com/CUBRID/cubrid-testcases-private-ex/pull/4589)는 사람이 닫아야 합니다.
- OOS reclaim·allocator 구현, AC-P2의 threshold 설정, 기존 기준 2는 별도 범위입니다. 이 PR은 고정 기준값만 명세에 맞춥니다. MVCC·recovery·ownership·identity 검사와 COPY 의미를 유지합니다.
- [`5837393ff`의 검증·측정 근거](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-review-fixes_5837393_claude.md)
- [narrow scan cycles 재측정과 원인](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27785/CBRD-27785-pr8299-cycles-layout_5837393_claude.md)
