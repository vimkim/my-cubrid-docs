# PR #7990 최종 통합 성능 보고: 측정 준비와 인계

작성일 2026-11-11, Asia/Seoul. Work912(상위 Work508, 착수 Work909).
관련 이슈 [CBRD-27788](https://jira.cubrid.org/browse/CBRD-27788), [CBRD-27785](https://jira.cubrid.org/browse/CBRD-27785), [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816), [CBRD-27781](https://jira.cubrid.org/browse/CBRD-27781).
독자는 PR #7990 최종 성능 측정을 실행하거나 그 결과를 검토할 사람이다.

**이 문서는 측정 준비다. 새 측정 결과가 아니다.** 이 문서의 수치는 모두 기존 보고서에서 가져온 것이며 출처를 적었다.
최종 측정은 아래 [준비 조건](#ready)이 모두 참이 된 뒤 시작한다. 측정 정책과 판정 기준은
[PR7990 성능 수락 기준](../cbrd-27785/CBRD-27785-pr7990-performance-acceptance_dcbf09e_codex.md)을 그대로 따른다.
이 문서는 새 benchmark 정책을 만들지 않고, 성능 측정을 회귀 CI에 넣지 않는다.

## 질문과 결론

질문은 세 가지다. 최종 통합 head에서 무엇을 어떤 명령으로 재야 하는가. 언제 재야 하는가. 지금 무엇이 빠져 있는가.

- **지금은 잴 수 없다.** 2026-11-11 18:00 KST 조회에서 PR #8299가 아직 병합되지 않았다. AC-P1의 전제가 "PR8299를 먼저 반영"이다. 측정 도구 `bench.py`·`ordinary.py`도 아직 PR #8299 branch에만 있다.
- **측정 시점은 하나의 사건으로 정한다.** 성능에 영향을 주는 PR의 포함·제외를 사용자가 확정하고, 그 상태의 `feature/oos-merge` tip을 최종 head로 고정한 때다. 아래 [필요한 사건](#trigger)에 적었다.
- **기준 revision을 다시 정해야 한다.** 수락 기준서의 기준은 develop `4781495f`다. 현재 PR #7990의 develop merge-base는 이미 `2dd94e32`로 바뀌었다. 최종 비교의 1차 기준은 고정 시점의 merge-base로 두고, `4781495f`는 과거 수치와 잇기 위한 연속 기준으로 둘 것을 권한다. 사용자가 정할 일이다.
- **도구는 대부분 있다.** 측정할 시나리오 7개(P2 제외)는 모두 기존 도구가 있다. P1-a, P1-c, P3-c, P3-d는 그대로 돌릴 수 있다. P1-b, P3-a, P3-b는 작은 준비가 필요하다. 빠진 것은 `io_bench.py`의 공개 위치, `ordinary.py` 결과의 비교기, idle 마감 수정, 리뷰어 큰 값 질의의 최종 head용 실행기다. [빠진 근거](#missing)에 정리했다.

## 1. 2026-11-11 조회 상태

`gh pr view`와 GitHub compare API로 조회했다. 측정을 시작하기 전에 같은 명령으로 다시 조회한다.

| 대상 | SHA·상태 | 성능 보고와의 관계 |
| --- | --- | --- |
| PR #7990 `feature/oos-merge` → develop | head `dfbf3d82c49f0ed998f8f35558ceb50de0fe16a6`, OPEN, CHANGES_REQUESTED, MERGEABLE | 최종 측정 대상. develop보다 47 commit 앞서고 10 commit 뒤처졌다. |
| develop | tip `45ca36562ffde26251b69e37704a8c27822795a1` | PR #7990과의 merge-base는 `2dd94e32ab86a756b0f1ea2123ad7d2ac913321b`다. 수락 기준서의 `4781495f`가 아니다. |
| PR #8299 일반 heap 읽기·UPDATE CPU | head `cd24a212aa81e2a11d72d1ac57bb10113727a4d8`, APPROVED, 미병합 | AC-P1의 전제. 측정 도구 `contrib/benchmarks/oos-performance/`를 함께 가져온다. Work880은 run 42968315485의 shell `cbrd_25894.sh` NOK 때문에 병합 조건 미충족으로 대기 중이다. |
| PR #8434 OOS 회수를 delete 확정 뒤로 | head `443073283d89e4511b2fa9a5b6a16898770f7e65`, APPROVED, 미병합 | UPDATE·DELETE·commit 경로를 바꾼다. Work841 측정에서 행 하나 UPDATE+COMMIT 3000회가 18.83 s → 31.09 s로 느려졌고, 원인은 commit마다 추가되는 동기 로그 flush였다(fdatasync 3011 → 6006). 수정 시제품은 있으나 미결이다. |
| PR #8416 STORAGE FORCE_INLINE | head `89496263eb8abfc7e80098004371c03c5aab8376`, 리뷰 없음, 미병합 | 저장 정책 선택지를 더한다. 기본값 경로가 바뀌는지 병합 전에 확인해야 한다. |
| PR #8348 vacuum undo forward slot | head `225375922881fb0f61cc311458078264961eef79`, 미병합 | 정확성 수정이다. 성능 영향은 작을 것으로 추정한다(추정, 미측정). |
| CBRD-27925 2단계 OOS 빈 페이지 재사용 | PR 없음, Work878 구현 중 | churn 뒤 OOS 파일 크기와 UPDATE 비용을 바꾼다. |

측정 도구의 현재 위치는 다음과 같다.

| 도구 | 위치 | 확인한 것 |
| --- | --- | --- |
| `bench.py`, `ordinary.py`, `test_bench.py`, `README.md` | PR #8299 head `cd24a212a`의 `contrib/benchmarks/oos-performance/`. `dfbf3d82c`에는 없다(API 404). | `--help` 정상. `python3 -m unittest test_bench` 16개 통과(Python 3.14.6). `bench.py fixture` 출력 SHA-256 `ff9fa8ce…5fe1`. `ordinary.py fixture --prefix chk_`는 6줄 SQL을 낸다. |
| `io_bench.py`, `IO_README.md` | 로컬 branch `CBRD-27788-oos-benchmark` commit `1a8cbefa434564275ce9b1dc10261261672f5251`만. `vimkim/cubrid`에 같은 branch가 없다(404). | 같은 commit의 `bench.py`와 함께 두면 `--help`, `sample --help` 정상. |
| 리뷰어 원문 실행기 | 이 저장소 [reviewer-exact-20261031/reproduce.py](../cbrd-27785/reviewer-exact-20261031/reproduce.py), [locale_campaign.py](../cbrd-27785/reviewer-exact-20261031/locale_campaign.py) | `--help` 정상. `prepare`가 base·feature worktree 두 개를 받는 구조다. |
| UPDATE churn·지연 | 이 저장소 [cbrd-27781/bench/run_all.sh](../cbrd-27781/bench/run_all.sh), [oos_update_churn.sh](../cbrd-27781/bench/oos_update_churn.sh) | Work841 소유. 이 작업에서 실행하지 않았다. |
| 같은 표 연속 UPDATE | `/mnt/nvme/data-5/tmp/CBRD-27816-20261103/harness/consecutive.py` (로컬, Git 밖) | 존재만 확인했다. |

이 조회 때 공유 서버의 load average는 42.9 / 58.4 / 67.2였다(80 cores, 17:55 KST). 실행 시간 측정에는 쓸 수 없는 상태다.

<a id="ready"></a>
## 2. 준비 조건

아래가 모두 참이면 측정을 시작한다. 하나라도 거짓이면 시작하지 않는다.

| ID | 조건 | 확인 방법 | 2026-11-11 상태 |
| --- | --- | --- | --- |
| R1 | PR #8299가 `feature/oos-merge`에 병합됐다. | `gh pr view 8299 -R CUBRID/cubrid --json state,mergedAt` | 거짓 |
| R2 | 성능에 영향을 주는 PR(#8434, #8416, CBRD-27925 2단계)마다 최종 head에 포함할지 제외할지 사용자가 정했다. 포함한 PR은 병합됐다. | 사용자 결정 기록, `gh pr view` | 미정 |
| R3 | 최종 head `F`를 full SHA로 고정했다. `F`는 PR #7990의 head이며, 측정 동안 바뀌지 않는다. | `gh pr view 7990 --json headRefOid`를 측정 전후에 두 번 | 미정 |
| R4 | 기준 `B`를 정했다. 권장안은 `git merge-base F develop`(고정 시점)이며, `4781495f`는 연속 기준으로 함께 잰다. | 사용자 결정 기록 | 미정 |
| R5 | 측정 도구가 `F`에 들어 있거나, 고정한 도구 commit을 따로 기록했다. `io_bench.py`는 측정 장비에서 받을 수 있는 위치에 있다. | `git ls-tree F contrib/benchmarks/oos-performance` | `bench.py`·`ordinary.py`는 R1과 함께 해결. `io_bench.py`는 거짓 |
| R6 | 측정 장비가 조용하다. 시작 전과 끝난 뒤 `uptime` load average가 1 미만이고, 다른 CUBRID 서버·빌드·테스트가 돌지 않는다. | `uptime`, `pgrep -a cub_` | 이 서버는 거짓(load 42~67) |
| R7 | 다른 세션의 측정과 겹치지 않는다. Work880(PR #8299 새 base 재측정)과 Work841(#8434 지연)이 끝났거나 장비가 다르다. | `work-tracker show 880`, `show 841` | 둘 다 진행 중 |

R6은 [Work841 인계](../cbrd-27781/perf-latency-handoff.md)의 장비 조건과 같다. 명령어 수(`instructions:u`)는 부하에 덜 흔들리지만, 수락 기준서는 실행 시간·CPU 시간·I/O도 함께 보고하라고 요구한다. 따라서 R6을 생략하지 않는다.

<a id="trigger"></a>
## 3. 측정 전에 필요한 사건

측정은 다음 사건 뒤에 시작한다.

> 사용자가 R2의 포함·제외를 확정하고, 포함한 PR이 모두 `feature/oos-merge`에 병합되고, develop을 반영해야 한다면 그 merge도 끝난 뒤의 `feature/oos-merge` tip.
> 이 tip을 PR #7990의 최종 통합 head `F`로 고정한다.

가장 이른 경우는 "PR #8299만 포함하고 나머지는 후속으로 보낸다"는 결정이다. 그러면 `F`는 #8299가 병합된 직후의 tip이다.
#8434를 포함하면 commit postpone flush의 처리(수정 포함 여부)가 먼저 정해져야 한다. 그 flush는 UPDATE+COMMIT 지연에 직접 들어가기 때문이다.

`F`가 고정된 뒤 head가 다시 움직이면 측정을 무효로 하고 새 `F`로 다시 잰다. 일부만 다시 재서 섞지 않는다.

## 4. 시나리오와 기존 명령

각 행은 기존 도구를 그대로 쓴다. 명령의 자리표시자는 `B`·`F`의 full SHA, 각 설치의 DB 이름과 서버 PID다.
설치마다 registry·master port·설정·DB·TMP를 따로 두고, 서버는 한 번에 하나만 띄운다. 도구는 DB 생성·삭제와 서버 시작·정지를 하지 않는다.

| ID | 수락 항목 | 무엇을 재는가 | 도구와 명령 | 판정에 쓰는 값 |
| --- | --- | --- | --- | --- |
| P1-a | AC-P1 | 200,000행 80B 일반 행의 narrow·wide scan | `python3 bench.py fixture > n-fixture.sql`, `csql -C -u dba --no-pager -i n-fixture.sql DB`, `python3 bench.py measure --database DB --server-pid PID --label B --source <SHA> --output <새 경로>`, 끝으로 `python3 bench.py compare --baseline <B>/summary.json --candidate <F>/summary.json --max-overhead-percent 2` | compare exit 0(예산 안)·1(회귀)·2(판정 불가). 유지 표본 spread가 2%를 넘으면 판정 불가다. |
| P1-b | AC-P1 | 리뷰어 일반 테이블 `COUNT(*), SUM(a)`, `SUBSTR(s,30,1)='a'` 조건 scan, 새 복제본 `UPDATE ... SET a=a+1` | `python3 ordinary.py fixture --prefix rN_ > f.sql`, `csql -C -u dba --no-pager -i f.sql DB`, `python3 ordinary.py measure --prefix rN_ --database DB --server-pid PID --label B --source <SHA> --output <새 경로> --show-oos`(`B`가 `SHOW HEAP OOS`를 모르면 `--show-oos` 빼기) | 질의별 유지 표본 명령어 수 중앙값의 `(B − F) / B`. 비교기가 없어 손으로 계산한다([빠진 근거](#missing) M2). |
| P1-c | AC-P1 진단 | 같은 표 연속 UPDATE, vacuum 비용 | CBRD-27816의 `harness/consecutive.py`(s1 쉬어 가며, idle 마감 120초) | 판정 줄이 아니라 별도 줄로 보고한다(2026-11-03 사용자 결정 2-가). |
| P3-a | AC-P3 | OOS SELECT Q1~Q5, heap·overflow 입력, `restart-only`·`warm`, 보조 `file-evict` | `python3 -B io_bench.py fixture --rows 100000 > fixture.sql`, `io_bench.py sample ... --layout {heap,overflow} --case {q1..q5} --cache {restart-only,warm} --repeat N --client-cpu 12`, `io_bench.py summarize --root <결과> --repeats 5` | 명령어 수와 실행 시간 중앙값, fetch·ioread, `/proc/PID/io`. 자동 합격선 없음. 같은 저장 정책인 overflow→OOS에 잠정 2%를 적용하고, heap→OOS(AC-P2 영역)는 관측값으로만 적는다. |
| P3-b | AC-P3 | 리뷰어 큰 값 `w` 표(약 6KB SHA2 값 2만 행) `sum(length(big))`, `substr(big,5000,1)`, `count(*), sum(a)`, `update w set a=a+1` | `reviewer-exact-20261031/reproduce.py prepare --root R --base-worktree <B> --feature-worktree <F> --tooling <workenv>`, `reproduce.py run --root R --rounds 4`, `locale_campaign.py --primary-root R` | 명령어 수 중앙값. 저장 경로가 바뀐 행(heap→OOS)은 관측값, overflow→OOS는 2% 평가 대상. 실행기 SHA 고정을 먼저 풀어야 한다(M4). |
| P3-c | AC-P3 | 최초 복사(INSERT)와 반복 UPDATE churn의 로그 바이트·OOS 페이지·지연 | `BASE=<B 설치> NEW=<F 설치> OUT=<새 경로> REPEATS=10 bash cbrd-27781/bench/run_all.sh` | `insert_sec`와 `update1~3_sec`를 따로 본다. 로그·페이지는 `SHOW LOG HEADER`, `SHOW HEAP OOS`. Work841 결과가 `F`와 같은 코드라면 재사용하고 다시 돌리지 않는다. |
| P3-d | AC-P3 | 작은 트랜잭션 UPDATE+COMMIT 지연 | Work841 보조 B(행 하나 UPDATE+COMMIT 3000회, 한 csql 세션) | #8434를 포함할 때만. flush 수(`strace -f -c`의 fdatasync)와 함께 보고한다. |
| P2 | AC-P2 | 기본 threshold 4~16KB 전체 읽기 | 측정하지 않는다 | 후속 이연. 통과로 표시하지 않는다. |

P1-a의 fixture는 `bench.py` README의 schema 3이다. `ordinary.py` 결과는 schema가 달라 `bench.py compare`가 받지 않는다(README의 Compare 절).

## 5. 반복·순서·산출물 요구

**반복.**

- P1-a는 `bench.py` 기본값(round 2개 × run 5개, run 0 버림)을 그대로 쓰고, 설치 순서를 바꿔 한 번 더 돈다(B→F, F→B). 지난 PR #8299 최종 측정은 한쪽당 64개 표본이었다.
- P1-b는 호출 한 번이 질의마다 5회, 첫 회 warmup이다. 리뷰어 절차와 같은 4 라운드 ABBA로 질의별 유지 표본 16개를 얻는다. UPDATE는 매번 새 복제본에서 시작한다.
- P3-a는 cache·layout·case·엔진마다 5개 표본, `file-evict`는 Q1·Q4를 3개씩이다(CBRD-27788 기본 200개 + 보조 24개).
- P3-c는 10회 이상 교대(Work841 인계의 조건)다.

**순서.** 서버와 질의 순서를 기록한다. 같은 반복 번호에서 B와 F를 교대한다(ABBA). 문자셋이 다른 표본은 섞지 않고 따로 집계한다.

**판정 전에 정한 기준.** 결정을 바꾸는 결과는 AC-P1·같은 저장 정책 AC-P3에서 명령어 수 중앙값이 −2%보다 나쁜 것이다. 라운드 사이 spread가 효과보다 크면 판정 보류다. 실행 시간에는 2%를 적용하지 않는다.

**측정마다 남길 것.** 다음이 빠진 표본은 판정에 쓰지 않는다.

| 항목 | 남길 근거 |
| --- | --- |
| revision | `B`·`F` full SHA, 도구 commit, `git status --porcelain`이 빈 결과 |
| 빌드 | compiler 버전, CMake build type, 실제 compile flag, `CUBRID_UNIT_TEST_ENABLED` 부재, `cub_server`·`csql`·로드된 DSO SHA-256 |
| 설정 | `cubrid.conf`, `cubrid paramdump` 출력. P1은 `data_buffer_size=4G`, query cache 0. P3-a는 16KiB page, `data_buffer_size=512M`. 시나리오별로 다르니 표에 적는다. |
| 문자셋 | 각 DB의 `createdb` 명령과 locale 인수, `SHOW CREATE TABLE`로 본 테이블·컬럼 charset·collation, 서버·client `LANG`·`LC_*` |
| 저장 상태 | `SHOW HEAP CAPACITY`, `SHOW HEAP OOS`, `spacedb`. 같은 입력이 B·F에서 heap·overflow·OOS 중 어디에 있는지 |
| 계수 경계 | client·연결 방식, autocommit 여부, 계수 구간에 들어간 작업, vacuum이 구간에 들어왔는지 |
| cache | `restart-only`·`warm`·`file-evict` 중 무엇이고 실제로 무엇을 했는지, `fincore` 전후 |
| 장비 | CPU 모델, core 수, 메모리, 디스크, kernel, governor, 서버·client CPU affinity, 시작·끝 load average, boot ID |
| 원시값 | 표본별 SQL·stdout·stderr·perf 출력, 버린 표본과 버린 이유 |

원시 산출물은 Git 밖의 새 디렉터리에 두고 경로를 보고서에 적는다. Git에는 선별 요약 JSON과 보고서만 넣는다(이 저장소 `AGENTS.md`의 What belongs in Git).

<a id="missing"></a>
## 6. 빠진 근거

| ID | 빠진 것 | 영향 | 처리 제안 |
| --- | --- | --- | --- |
| M1 | `io_bench.py`가 로컬 commit `1a8cbefa`에만 있다. 원격 branch가 없다. | 다른 장비에서 P3-a를 돌릴 수 없다. | `vimkim/cubrid`에 branch를 push하거나 파일을 측정 장비로 복사한다. push는 별도 승인 필요. 측정 결과에 도구 commit을 적는다. |
| M2 | `ordinary.py` 결과를 비교하는 명령이 없다. | P1-b 판정을 손으로 계산하게 된다. 계산 실수와 spread 누락 위험이 있다. | 측정 전에 retained median·spread·`(B−F)/B`를 내는 작은 요약 스크립트를 만들고, 측정과 같은 commit에 고정한다. 엔진 변경이 아니다. |
| M3 | `ordinary.py`의 idle 대기 마감이 10초다. checkpoint 뒤 대기는 21~22초였다(CBRD-27816). | 오래 떠 있는 서버에서 UPDATE 측정이 멈출 수 있다. | 사용자 결정 2-2(늘린다)가 아직 반영되지 않았다. 측정 전에 PR #8299 쪽 소유 세션이 반영하거나, 서버를 매 블록 재시작한다. |
| M4 | 리뷰어 큰 값 실행기 `reproduce.py`는 `REVISIONS`에 `4781495f`·`4408135c`를 고정했다(22~23행). UPDATE도 같은 표에 연속으로 돈다. | 그대로는 `B`·`F`를 받지 않는다. | 측정 전에 `REVISIONS`만 `B`·`F`로 바꾼 사본을 만들고 그 diff를 결과와 함께 남긴다. 새 root에서 `prepare`를 한 번 시험한다. |
| M5 | 리뷰어 원문 locale·feature SHA가 알려지지 않았다. | 원문 수치와의 동일 재현을 판정할 수 없다. | UTF-8과 ISO-8859-1을 따로 잰다. 원문 재현 완료로 표시하지 않는다. |
| M6 | 기준 revision이 `4781495f`에서 `2dd94e32`(현재)로 움직였다. | 과거 수치와 최종 수치의 기준이 다르다. | R4 결정. 두 기준을 다 재면 표를 나눈다. |
| M7 | UPDATE 허용치가 두 곳에서 다르다. 수락 기준서는 잠정 2%, `bench.py` README는 "작성자가 일반 UPDATE 약 5%를 따로 수용"이라고 적었다. PR #8299 본문은 UPDATE 중앙값 −1.34%, vacuum이 든 최악 표본 약 −7.9%를 보고했다. | 같은 결과를 두 기준으로 다르게 읽을 수 있다. | 보고서에는 2% 기준의 판정을 적고, 5% 수용은 작성자 수용으로 따로 적는다. 둘 다 리뷰어 승인이 아니다. |
| M8 | #8434 commit postpone flush의 처리가 미정이다. | #8434를 포함하면 P3-d 결과가 수정 여부로 크게 달라진다. | R2에서 함께 정한다. Work841·latency 세션 소유. |
| M9 | 측정 장비가 정해지지 않았다. 이 서버는 R6을 만족하지 못한다. | 실행 시간·CPU 시간을 판정할 수 없다. | 조용한 장비를 확보한다. 못 하면 명령어 수만 판정하고 실행 시간은 "판단 불가"로 적는다. |
| M10 | 리뷰어 2026-11-04 요청(SQL trace에서 OOS 읽기 분리)이 미구현이다. | P3-a의 fetch·ioread를 heap과 OOS로 나눠 보고할 수 없다. | 별도 slice가 진행 중이다. 측정 전에 들어오면 trace 분리값을 함께 남긴다. |

## 7. 재사용할 기존 결과

다음 결과는 그 revision의 기록으로 인용한다. 최종 head의 결과로 바꿔 적지 않는다.

| 결과 | revision | 출처 |
| --- | --- | --- |
| 일반 테이블 scan +0.79%, 조건 scan −0.83%, UPDATE −1.34%(명령어 수 중앙값, develop 대비) | `4c3c8d791` 대 `4781495f`, 2026-11-03, locale `en_US.utf8`, 테이블 문자셋 미기록 | [PR #8299 본문](../cbrd-27785/pr8299-sign-rule-pr-body.md) |
| 같은 표 연속 UPDATE −1.33%(유지 표본 36개), 최악 −2.94% | 2026-11-04 | [CBRD-27816 1단계](../cbrd-27785/CBRD-27816-ordinary-update-phase1.md) |
| OOS SELECT Q1 heap 입력 +48.6%, Q4 −25.9% 등(실행 시간, restart-only) | `dcbf09e` 대 `4781495`, 2026-10-27 | [OOS SELECT 실측](CBRD-27788-oos-select-performance_dcbf09e_codex.md) |
| UPDATE churn 로그 −42%, 회수 로그 6.1 → 0.71 KB, 행 하나 UPDATE+COMMIT 지연 +65% | `3e8072f56` 대 `d52b1889e`, 그리고 Work841 2026-11-11 | [CBRD-27781 성능](../cbrd-27781/perf.md), Work841 기록 |

Work880은 `50619ce53` 대 `855f220d5`의 PR #8299 재측정을 남겨 두었다. 그 측정은 Work880 소유이며 이 작업에서 반복하지 않는다.

## 8. 최종 보고서 틀

측정 뒤 이 틀을 `CBRD-27788/` 아래 새 보고서로 채운다.

```markdown
# PR #7990 최종 통합 성능 보고

작성일 YYYY-MM-DD, Asia/Seoul. 대상 head `F` <full SHA>, 기준 `B` <full SHA>, 연속 기준 `4781495f…`(쟀다면).

## 결론
- AC-P1: 목표 충족 | 개선 필요 | 판정 보류. 근거 한 줄(명령어 수 중앙값, 표본 수, spread).
- AC-P3: 이득과 손해 요약. 같은 저장 정책(overflow→OOS)의 2% 평가 결과. heap→OOS는 관측값.
- AC-P2: 후속 이연. 측정하지 않음.
- 잠정 2%는 사용자 기준이며 리뷰어 승인 여부: <근거 있으면 링크, 없으면 "미확인">.

## 조건
revision, 도구 commit, 빌드, conf, 문자셋, 저장 상태, cache, 장비, load average.

## AC-P1 일반 테이블
| 질의 | B 중앙값 | F 중앙값 | 변화 (B−F)/B | 유지 표본 | spread | 판정 |

## AC-P3 이득과 손해
| 시나리오 | 입력 저장 경로 B→F | cache | 명령어 수 변화 | 실행 시간 변화 | I/O | 비고 |
최초 복사(INSERT)와 반복 UPDATE churn을 다른 행으로 둔다.

## 제외한 표본과 이유
## 한계와 남은 일
## 원시 산출물 경로
```

## 9. 이 문서의 검증과 한계

- 실행한 것은 도구의 `--help`, fixture 생성, `test_bench.py` 단위 시험(16개 통과)뿐이다. 서버를 띄우거나 DB를 만들지 않았다.
- PR 상태와 SHA는 2026-11-11 약 18:00 KST의 조회값이다. 측정 직전에 다시 조회해야 한다.
- #8348, #8416의 성능 영향은 추정이며 재지 않았다.
- 엔진 source, CI, PR 본문, JIRA를 바꾸지 않았다.
