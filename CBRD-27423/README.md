# CBRD-27423 — page buffer 성능 분석·벤치마크 전략

Created: 2026-10-16 KST. Last modified: 2026-10-16 KST.

[JIRA CBRD-27423](https://jira.cubrid.org/browse/CBRD-27423)의 성능 분석 제안과 협업 결정을 위한 문서다. 관련 EPIC은 [CBRD-27193](https://jira.cubrid.org/browse/CBRD-27193)이다. 관련 PR: 2026-10-16 이슈 번호 검색에서 직접 관련 PR을 찾지 못했다. 구현 PR 번호는 아직 지정하지 않는다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [benchmark-strategy-2026-10-19.md](benchmark-strategy-2026-10-19.md) | 부하·환경·지표·역할 결정안, 첫 실험과 관측별 후속 조사, 연락 문안 | 2026-10-16 | 2026-10-16 | 형규님과 첫 벤치마크 실행 및 병목 조사 전략을 합의하기 위해 |

## 검증 기록

확인: **2026-10-16 18:33–18:39 KST**. 아래는 자료 준비 과정의 관측이다. 벤치마크 결과나 협업 합의로 해석하지 않는다.

| 확인 대상 | 명령·결과 | 의미·한계 |
| --- | --- | --- |
| 작업·회의 범위 | `work-tracker show 374 --json`, `work-tracker history 374 --json` 및 주간 control sheet 확인. 374의 planned/due는 2026-10-19이며 형규님과의 전략 합의가 목표다. 준비 착수 때 기존 374를 active로 갱신했다. | 담당·실행 일정·반복 횟수의 합의 기록은 없었다. 373·269의 상태나 기한은 바꾸지 않았다. |
| 현행 이슈 | `cubrid-jira search CBRD-27423` 성공. Open·Minor·Sub-task·Unassigned·Unresolved, 표시된 Updated는 2026-10-02다. | 이슈 본문은 비교 목적과 제안·미결정을 구분한다. 본문에 남은 “현재 develop c63a3b9”는 과거 설계의 기준이다. |
| 관련 PR | `gh pr list --repo CUBRID/cubrid --state all --search CBRD-27423 --limit 100 --json number,title,state,url,headRefOid` → `[]`. | 번호 검색으로 발견하지 못했다는 뜻이며 관련 구현 부재의 증명은 아니다. |
| 로컬 소스 신원 | `git -C /home/vimkim/gh/cb/develop rev-parse HEAD` → `4adcd409072b189f5d965bde5750c53176d90de0`. build의 CMakeCache는 `CMAKE_BUILD_TYPE=Debug`. | 새 소스 동작 분석은 하지 않았다. submodule 변경과 기존 미추적 파일을 보존했다. 이 SHA를 첫 실험의 합의 revision으로 확정하지 않았다. |
| 선택된 호스트 환경 | `cub-workenv doctor --worktree /home/vimkim/gh/cb/develop` → 선택 설치본 `develop/debug_gcc`, 상태 ready지만 exit 1. `sp_testdb.sock`의 stale 또는 미확인 항목과 접근 불가 PID 1705개를 보고했다. | 준비 완료 판정이 아니다. 소켓·프로세스·DB를 정리하거나 환경을 전환하지 않았다. 설치 경로 존재만으로 현재 소스와 대응한다고 보지 않는다. |
| 기존 최적화 설치본 | `develop/release_gcc/bin/cubrid`와 `csql` 파일 존재를 확인했다. 현재 셸의 `command -v cubrid csql`에서는 찾지 못했다. | release 설치본의 소스 SHA·추가 패치·설정·사용 가능성은 미검증이다. 새 빌드나 DB 생성·실행은 하지 않았다. |
| 머신·도구 | `hostname` → dev2. `uname -sr`, `lscpu`, `free -h`에서 Linux 5.14, Xeon Gold 5218R, 2 socket/40 physical core/80 logical CPU, 2 NUMA node, 총 메모리 약 251 GiB 확인. `command -v`로 perf·pidstat·iostat·mpstat·taskset·numactl 확인. | 장비 존재와 사양 확인이다. 벤치마크용 예약·유휴 상태·저장 장치·CPU 배치·전력 조건은 미확인이다. |
| perf 기본 권한 | `perf stat -e task-clock,cycles,instructions -- true` → exit 0. | 짧은 자기 자식 프로세스에서 카운터 수집이 가능했다. 이 수치는 성능 결과가 아니다. 서버 attach·call graph·심볼·관련 데몬 관측은 검증하지 않았다. |
| 기존 직접 실험 자산 | 세미나 저장소의 patch·analyze.py·summary/provenance·압축 trace 파일 존재 확인. 실제 소스 worktree `pgbuf-seminar-replacement`는 clean, HEAD `282f81cebad9c875fb4f03348ccbcdb8d15a1c04`이며 실험 README가 있다. | 통상 build 및 build_preset_debug 위치의 실행 파일·CMakeCache는 없었다. 다른 위치의 설치·실행 가능 여부와 현재 revision 호환성은 미확인이다. 이번에 재빌드·재실행하지 않았다. |

### 기존 자료를 사용할 때의 경계

- [프레임워크 초안](https://github.com/vimkim/my-cubrid-jira/blob/c6a7ca4a9d2f0a6daab90b6ea09b8c6e876d4055/issues/CBRD-27423-page-buffer-performance-framework_c63a3b9_codex.md)은 CUBRID `c63a3b993be552ef6ad3ce244c386d5081147958`을 참고한 설계 제안이다. 조회한 현행 JIRA 본문과 목적·범위·주요 미결정 사항을 대조했다. 이 문서는 그 상세 설계를 다시 작성하지 않는다.
- [세미나의 실제 교체 실험](https://github.com/vimkim/my-cubrid-page-buffer-seminar/blob/8dbdff4639734a2eeef327ba9a6343182548b09d/experiments/replacement/README.md)은 CUBRID `f799e05d77d5300c6ea5753b4a6cc7caee6d8912`에 관측 패치를 적용한 debug SERVER_MODE 동작 검증이다. 유지보수 일부를 정지시키며 flush 데몬은 실행한다. 64 MiB 버퍼의 fits/cycle 조건은 과거 실험 설정이지 첫 벤치마크의 합의 조건이 아니다. 실행·데이터 준비·완전성 검증 방식을 참고할 수 있지만 시간을 일반 성능 기준으로 재사용하지 않는다.
- 세미나 로컬 HEAD는 `83462868664feee0d2a79d71ea644a7a09331f91`이다. 위 README의 현재 파일과 링크에 고정한 `8dbdff4` 버전의 SHA-256이 모두 `19dd0159dafd1bcae83457d3a279dc3fa672a6fc2af8092aa4fc0b9dabe2146b`로 일치했다.
- [10/2 후보 분석](../pgbuf-analysis/report-2026-10-02.md)의 holder·대기열·LRU·flush 후보는 측정으로 입증된 병목이 아니다. 이번 첫 실험은 그중 하나를 미리 결론 내리지 않는다. [작업 373의 triage 자료](../CBRD-27193/briefing-2026-10-19.md)는 별도로 유지한다.

## 회의 전·후 갱신

10/19 회의 직전 JIRA·관련 PR과 실제 사용할 소스·설치본·부하·머신 조건을 다시 확인한다. 그때도 실행 환경이 없으면 누락 자산과 담당자·확인 시점을 합의하는 것이 첫 조치다.

회의가 끝나면 준비안의 합의 기록에 선택한 부하·환경·지표·역할·다음 조치와 남은 결정을 적고 작업 374에 반영한다. 자료 준비·로컬 통합과 실제 전략 합의는 구분한다. 원시 조회·로그는 저장소에 추가하지 않으며, 새 supporting/configuration 파일은 없다.
