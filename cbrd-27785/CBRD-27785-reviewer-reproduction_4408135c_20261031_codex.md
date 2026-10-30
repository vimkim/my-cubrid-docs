# CBRD-27785: 원댓글 DDL·SQL의 4라운드 재현과 문자셋 비교

작성일: 2026-10-31, Asia/Seoul. 독자: PR #7990의 성능 수치를 검증하거나 팀에 설명할 엔진 개발자.
질문: 리뷰어가 제공한 절차로 실행하면 같은 instructions와 회귀율이 나오는가?

**원문 SQL 실행은 완료했지만, 원댓글 전체 수치의 동일 재현은 확인하지 못했다.**
명시하지 않은 DB 문자셋이 큰 차이를 만들었다. 같은 develop 바이너리에서 큰 값 LENGTH의
중앙값은 UTF-8 294.076M, ISO-8859-1 188.608M이었다. 원댓글은 186.1M이다.
ISO-8859-1은 원댓글에 더 가까웠으나, 이 결과만으로 리뷰어의 locale을 확정할 수 없다.
큰 값 UPDATE와 반복 사이 변동도 원댓글과 같지 않았다. 차이를 공유 호스트의 시간 노이즈로
설명하거나, 원댓글이 틀렸다고 판정하지 않는다.

전체 원시 로그가 아니라 **실제 재실행 결과**다. Work 643에서 수행했고,
각 문자셋의 320회씩 총 640회, warmup 128회를 포함해 보존했다.
계수 구간의 SQL 오류는 0건이며, 남은 512회로 중앙값·범위를 계산했다.

## 원문과 revision

- [첫 성능 댓글](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6434778190)은 feature `4408135c`와 develop `4781495f`를 명시한다.
- [상세 재현 댓글](https://github.com/CUBRID/cubrid/pull/7990#issuecomment-6461744209)은 conf·DDL·8개 SQL·4라운드·질의별 5회 중 첫 회 제외를 제공한다. 이 댓글에는 feature 전체 SHA와 locale이 없다.

| 역할 | 저장소와 고정 commit |
| --- | --- |
| A, develop 분모 | `CUBRID/cubrid`, `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| B, feature | `CUBRID/cubrid`, `4408135c0833ec959da3590f12c14efa69610c7e` |

사용자는 추가 정보가 없으므로 첫 댓글의 feature를 사용하고 UPDATE를 같은 테이블에서
연속 실행하도록 선택했다. 원문의 이틀에 걸친 측정 대신 4라운드를 오늘 연속 실행하는 것도
선택했으며, 이 날짜 간격 차이를 남긴다. 최신 feature나 읽기 최적화 소스로 바꾸지 않았다.
소스의 tracked 변경은 없고, 각 실제 설치와 실행 PID·DSO를 대조했다.

## 고정한 절차와 남은 가정

[fixture.sql](reviewer-exact-20261031/fixture.sql)과
[queries.sql](reviewer-exact-20261031/queries.sql)은 저장한 원댓글의 SQL block과
CRLF 정규화 후 일치한다. 테이블 이름 `seq`, `w`, `n`도 유지했다.
별도 seed·테이블 복제·ORDER BY·명시적 통계 갱신은 추가하지 않았다.
CSQL 기본 autocommit을 사용했고 측정 SQL 뒤에 COMMIT 문장을 덧붙이지 않았다.

| 항목 | 이번 실행 |
| --- | --- |
| 입력 | `w` 20,000행, SHA2 결과 47개를 연결한 6,016자 값; `n` 200,000행, SHA2 256 결과 64자 |
| 생성 | 각 새 DB에서 원문 DDL·INSERT를 한 번 실행 |
| 반복 | 질의마다 5회, 첫 실행 제외, 4라운드; 버전·질의당 retained 16개 |
| 순서 | 원문 SQL block의 8개 질의 순서. 버전은 A→B, B→A, A→B, B→A |
| 상태 | 표본·라운드 사이 초기화 없음. 세 UPDATE 각각 DB당 20회 누적 |
| 서버 | 두 버전 직렬 실행. 버전·라운드마다 서버를 시작·종료하고 DB는 보존 |
| 계수 | `perf stat -e instructions:u -p <cub_server pid>`로 전체 서버 프로세스 계수 |
| 경계 | 새 CSQL 연결·SQL·autocommit·연결 종료를 포함. 구간 내 background work도 포함 |
| locale | 첫 캠페인 `en_US.utf8`; 누락 조건을 검증하는 별도 새 DB 캠페인 `en_US.iso88591` |

리뷰어는 UPDATE 초기화, 쿼리/라운드의 정확한 중첩 순서, 서버 재시작, CSQL 연결·계수 경계를
완전한 실행 스크립트로 제공하지 않았다. 위 선택을 리뷰어의 실제 절차로 확정하지 않는다.
두 locale의 표본을 합치지 않았고, 첫 캠페인의 불일치 결과도 그대로 남겼다.

## 빌드·설정과 실제 저장 형태

두 버전 모두 GCC 11.5.0, CMake `RelWithDebInfo`다. CUBRID `build.sh`의 release 모드도
이 build type을 선택한다. 서버 `heap_file.c` 실제 compiler command에서
`-O2 -DNDEBUG -finline-functions -fno-omit-frame-pointer`를 확인했다.
설정된 UNIT_TEST 옵션은 전부 OFF이고 `CUBRID_UNIT_TEST_ENABLED`는 없었다.
원댓글의 정확한 컴파일러·전체 flags·libc·호스트는 확인되지 않았다.

```ini
[common]
data_buffer_size=4G
log_buffer_size=256M
sort_buffer_size=16M
max_clients=50
db_volume_size=2G
log_volume_size=1G
log_max_archives=0
```

매 라운드 live `paramdump`로 값을 확인했다. 각 DB의 실제 primary data는
2,147,483,648B, active log는 1,073,741,824B였다. host workenv의 기본 생성 크기
64M/32M을 그대로 쓰지 않았다. 도구의 작업 전용 복사본에서 native createdb의 두 크기
인수만 2G/1G로 바꿨고, 두 번째 캠페인에서는 locale 인수도 바꿨다. 전역 도구는 수정하지 않았다.

호스트 자원 충돌을 피하기 위해 할당 master port 41178/41180을 사용했다. 원문의 1523과
이 부분은 다르다. CPU affinity·PARALLEL 힌트·캐시 drop·threshold·allocator는 바꾸지 않았다.
공유 호스트에서 다른 작업은 유지했다. 각 표본의 loadavg와 프로세스 I/O를 보존했다.

완료 뒤 별도 `SHOW CREATE TABLE`에서 `utf8_bin`·`iso88591_bin`을 확인했다.
일반 테이블은 양쪽 모두 200,000행·1,429 heap pages·평균 92B였다.
큰 값 테이블은 develop의 평균 6,032B·10,001 heap pages에 비해 feature는 평균 55B였다.
이 저장 형태 확인은 누적 UPDATE 20회 뒤의 진단이며 최초 적재 직후의 snapshot이 아니다.

## 실제 결과

단위 M은 1,000,000 instructions다. 각 칸은 **A → B (B/A 변화율)**이며,
모든 증가율의 분모는 동일한 고정 develop A다. 각 새 캠페인은 버전·질의별 유효 16회의
중앙값이다. 원문 열의 값은 리뷰어가 보고한 4라운드 중간값을 옮겼다.

| 작업 | 원댓글, M | UTF-8 재실행, M | ISO-8859-1 재실행, M |
| --- | ---: | ---: | ---: |
| 6KB 행 좁은 컬럼 스캔 | 43.6 → 33.6 (-23.1%) | 43.997 → 35.736 (-18.78%) | 43.958 → 35.764 (-18.64%) |
| 6KB 값 LENGTH | 186.1 → 261.7 (+40.6%) | 294.076 → 377.360 (+28.32%) | 188.608 → 271.931 (+44.18%) |
| 6KB 값 SUBSTR 조건 | 195.1 → 270.7 (+38.7%) | 498.490 → 577.393 (+15.83%) | 198.995 → 277.826 (+39.61%) |
| 6KB 행 작은 컬럼 UPDATE | 3,467.0 → 6,021.9 (+73.7%) | 3,352.992 → 9,264.748 (+176.31%) | 3,349.557 → 9,238.489 (+175.81%) |
| 6KB 큰 컬럼 UPDATE | 1,789.8 → 2,408.7 (+34.6%) | 1,911.151 → 2,485.081 (+30.03%) | 1,701.347 → 2,165.148 (+27.26%) |
| 일반 풀 스캔 | 252.7 → 272.9 (+8.0%) | 251.105 → 268.714 (+7.01%) | 251.123 → 268.730 (+7.01%) |
| 일반 조건 스캔 | 476.8 → 524.1 (+9.9%) | 531.799 → 576.005 (+8.31%) | 491.603 → 535.833 (+9.00%) |
| 일반 UPDATE | 6,323.8 → 6,769.6 (+7.0%) | 6,563.699 → 6,943.490 (+5.79%) | 6,545.014 → 6,874.267 (+5.03%) |

ISO-8859-1의 라운드별 변화율도 남긴다. 각 칸은 해당 라운드의 A/B 각 유효 4회 중앙값 비율이다.

| 작업 | 1라운드 | 2라운드 | 3라운드 | 4라운드 |
| --- | ---: | ---: | ---: | ---: |
| 6KB 값 LENGTH | +40.94% | +44.23% | +44.13% | +44.59% |
| 6KB 값 SUBSTR 조건 | +38.26% | +39.80% | +39.59% | +40.28% |
| 6KB 행 작은 컬럼 UPDATE | +188.47% | +165.55% | +182.05% | +181.32% |
| 6KB 큰 컬럼 UPDATE | +21.99% | +65.72% | +21.64% | +32.67% |

첫 라운드 LENGTH +40.94%만 골라 원문 +40.6%를 재현했다고 쓰지 않는다.
네 라운드를 합친 +44.18%와 이후 라운드의 변화도 함께 판정한다.
원댓글의 스캔 라운드 간 0.3%p 이내라는 관측은 이번 큰 값 스캔에서 같게 나타나지 않았다.
특히 작은 컬럼 UPDATE는 ISO-8859-1에서도 +175.81%로 원문의 +73.7%와 다르다.
UPDATE 상태·유지관리 시점·측정 순서가 이 차이의 원인이라는 인과관계까지 확정하지 않는다.

문자셋은 같은 ASCII 값·SQL에서도 instructions 비교를 크게 바꿨다.
그러므로 SQL과 source commit만 같다는 사실로 같은 실행 경로의 계수를 기대할 수는 없다.
이는 이번 두 캠페인에서 확인한 영향이며, 리뷰어가 ISO-8859-1을 사용했다는 증거는 아니다.

## 검증과 해석의 한계

640개 실제 `.perf`·실행 SQL·exit code를 다시 읽어 표본의 명령 수와 SQL 원문 일치를 확인했다.
모든 counter running 비율은 95% 이상이고 중앙값은 native counter에서 재계산했다.
각 라운드 뒤 전체 행 수·`a=MOD(id,100)+누적 UPDATE 수`·문자열 길이 합계를 검사했다.
큰 값 회전은 경계 ID 1·17·5000·5001·20000의 SHA2로 별도 검증했다.
16개 라운드 종료 상태 검증이 통과했다. 전체 큰 값 내용의 전수 hash 검사는 아니다.

완료 뒤 계수 밖의 별도 warm TRACE에서 20개 읽기 계획의 `ioread=0`을 확인했다.
develop의 읽기와 feature의 일반 테이블 읽기에는 parallel workers 4가 표시됐고,
feature의 큰 값 테이블에는 parallel workers 표시가 없었다. 이는 완료 후 진단이며
측정 구간의 모든 I/O·worker 상태를 동시에 기록했다는 뜻은 아니다.
기본 실행 계획을 포함한 SQL 비용이며 scalar reader 한 함수의 절대 기여율은 아니다.
경과 시간·CPU 시간 비회귀나 최신 PR의 최적화 완료를 인증하지 않는다.

사후 진단 첫 시도는 종료 직후 프로세스 검사에서 assertion이 실패했다.
재조회 때 소유 프로세스는 없었고, 종료 대기를 둔 별도 재실행은 통과했다.
최초 로그를 보존했으며 성능 표본을 제외하거나 다시 고르지 않았다.
모든 작업 소유 서버·master·PL 프로세스의 종료를 확인했다. 기존 DB·다른 작업은 보존했다.

## 증거와 재실행

[선별 계수·범위·빌드 identity](reviewer-exact-20261031/results.json)는 모든 640개 값과
warmup 표시 기준, 4라운드별 배열, retained 중앙값·최소·최대, 실제 compiler command를 보존한다.
[원문 절차 실행기](reviewer-exact-20261031/reproduce.py)와
[locale 비교 실행기](reviewer-exact-20261031/locale_campaign.py)는 절차·DB 소유권·counter와
SQL 결과 검증을 다시 확인하는 데 필요해 남겼다. 두 SQL 파일은 입력 원문 대조와 재실행에 필요하다.
raw 다운로드·전체 로그·DB·설치·보조 진단 스크립트는 Git에 넣지 않았다.

```text
/mnt/nvme/data-5/tmp/CBRD-27785-reviewer-exact-20261031-kpeajbx3
```

개인 host workenv에서 새 root와 빌드·설치된 별도 source worktree를 준비한 뒤 실행한다.
원문 댓글 JSON은 해당 root의 `comment-6461744209.json`에 저장하며 `body`와 `url`이 필요하다.
실행기는 source SHA, 실제 release flags, test-OFF와 DB 생성 크기를 검사한다.
기존 DB 이름·경로를 덮어쓰지 않으므로 재실행에는 새 환경이 필요하다.

```bash
python3 -B reviewer-exact-20261031/reproduce.py prepare \
  --root "$RUN_ROOT" --base-worktree "$BASE_WORKTREE" \
  --feature-worktree "$FEATURE_WORKTREE" --tooling "$WORKENV_SOURCE"
cp reviewer-exact-20261031/reproduce.py "$RUN_ROOT/harness.py"
python3 -B reviewer-exact-20261031/reproduce.py run --root "$RUN_ROOT" --rounds 4
python3 -B reviewer-exact-20261031/locale_campaign.py --primary-root "$RUN_ROOT"
```

원문 전체 수치의 동일 재현을 판정하려면 리뷰어의 정확한 feature SHA·locale·compiler/runtime,
UPDATE 초기화와 질의/라운드/서버 순서·계수 경계를 확인해야 한다. 추가 정보가 없는 현재는
선택한 조건의 재실행 완료와 문자셋의 영향을 확인한 상태이며, 전체 수치 검증 완료로 표시하지 않는다.
