# CBRD-27193 — page buffer EPIC

Created: 2026-10-16 KST. Last modified: 2026-10-19 KST.

[JIRA EPIC](https://jira.cubrid.org/browse/CBRD-27193)의 정확성·운영성·성능 개선을 위한 회의 자료다. **10/19 17:00 KST 회의용 최신 자료는 [전체 19건 triage HTML](triage-2026-10-19.html)**이다. 모든 하위 이슈의 쉬운 설명·버그 수정/기능 구현 분류·제안 순서·담당 제안·첫 조치를 담았다. 기존 상위 3개 Markdown 브리핑은 10/16 기준의 제안으로 보존한다.

10/16 관련 PR 기록: 당시 상위 3개 이슈 번호로 검색한 직접 관련 PR은 이번 조회에서 발견하지 못했다. 주변 변경은 [#8169](https://github.com/CUBRID/cubrid/pull/8169), [#7592](https://github.com/CUBRID/cubrid/pull/7592), [#7940](https://github.com/CUBRID/cubrid/pull/7940), [#7630](https://github.com/CUBRID/cubrid/pull/7630)을 대조했다. EPIC 전체를 대표하는 단일 PR 번호를 지정하지 않는다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [briefing-2026-10-19.md](briefing-2026-10-19.md) | 상위 3개 제안, 현재 근거, 결정 요청과 전체 subtask 링크 | 2026-10-16 | 2026-10-16 | 10/19 회의에서 우선순위·담당자·첫 조치를 결정하기 위해 |

## 전체 이슈 triage HTML — 10/19 갱신

[triage-2026-10-19.html](triage-2026-10-19.html)은 10/19 17시 회의에서 전체 이슈의 우선순위·담당·첫 조치를 결정하기 위한 독립 HTML이다. 2026-10-19 16:01–16:05 KST에 새로 읽은 JIRA 본문·댓글·PR 및 소스를 기준으로 작성했다. 제안 순서는 JIRA 변경이나 회의 승인이 아니다.

- **전체 집합:** parent JQL `total=19`, 반환 19건과 EPIC의 연결 집합이 일치했다. 19건 모두 Open·Minor이며, CBRD-27370만 Daehyun Kim 담당이다. 댓글도 반환 수와 전체 수가 일치했다.
- **분류·제안:** 버그 수정 12건(결함 후보의 안전성 조사·설명 정리 포함), 기능 구현 7건(조사·설계 포함). 먼저 6건·다음 7건·후속 6건이며, 순번은 검토 순서다. CBRD-27356의 9/29 debug 서버 중단 댓글을 반영해 첫 후보로 올렸고, CBRD-27263·27370이 뒤따른다. 기존 후보 CBRD-27262는 먼저 4번으로 유지했다.
- **현재 소스:** 원격 develop `1dceac8add1801aef564b27624b8fbb5b6f62d59`는 기존 `4adcd409072b189f5d965bde5750c53176d90de0`보다 13커밋 앞이다. `page_buffer.c`, `page_buffer.h`, `double_write_buffer.cpp`는 두 revision에서 동일하며 읽은 로컬 파일도 HEAD와 일치했다. `system_parameter.c`의 차이는 무관한 빈 줄이다. 보고된 vacuum·postpone 실패 지점은 최신 소스로 대조했다.
- **변경 상태 대조:** #7630의 국소 수정 병합과 CBRD-27356의 공통 정책 문제를 구분했다. #7592의 SHOW 카운터 폐기·NULL 반환을 반영해 CBRD-27266의 낡은 전제를 그대로 반복하지 않았다. CBRD-27267에는 실제 big 큐 생산 경로가 있어 “항상 비어 있음”으로 기술하지 않았다. CBRD-27630의 Lean 반례는 실제 엔진 재현과 구분했다.
- **비어 있는 본문:** CBRD-27316·27398은 live JIRA 본문과 댓글이 없다. 27316의 조사 범위는 제안으로 표시했고, 27398은 Open·Draft [PR #7940](https://github.com/CUBRID/cubrid/pull/7940), HEAD `6bf4753eaa136fb87a4632deac44dc403ad0538e`의 설명과 잔여 검증을 사용했다. 19개 번호별 PR 검색에서 27356은 #7630, 27398은 #7940이 반환됐으며 다른 번호는 0건이었다. 번호 검색만으로 관련 수정 부재를 증명하지 않는다.

**문서 검증:** headless Chromium에서 JIRA 집합=표=상세 19건, 분류 12/7건, 단계 6/7/6건을 확인했다. 검색·필터 초기화·이슈 이동·전체 펼치기/접기, 320·390·768·1024·1440px 화면의 페이지 가로 넘침 없음, 밝은/어두운 화면과 console 오류 없음, 외부 의존 요청 없음, JavaScript 없이 전체 목록과 기본 펼치기 동작을 확인했다. 필터·접힘 상태와 무관한 인쇄를 검사했고, JavaScript 사용/미사용 PDF 모두 19건의 문제·영향·변경·근거·불확실성·결정·첫 조치가 원문대로 포함됨을 추출 텍스트로 대조했다. README Markdown 검사, 보존 문서 링크와 기존 Markdown 인덱스 coverage도 통과했다.

HTML은 독자가 직접 읽는 최종 회의 자료이며 CSS·JavaScript·favicon을 포함한다. 별도 지원 파일이나 중복 보고서는 추가하지 않았다. 원시 응답·본문 캐시·생성 스크립트·브라우저 검사·이미지·PDF는 ignored `.scratch/triage-20261019/`에만 보관한다. 기존 `/.scratch/` 규칙을 재사용하며 Git 추적 파일이 아님을 확인한다.

이번 준비에서 엔진 빌드·재현·오류 주입·CI·벤치마크·Lean 검증은 새로 실행하지 않았다. 과거 결과의 기준 빌드·미확정 도달성·배포 범위를 HTML에 구분했다. 작업 373의 실제 회의 결정과 작업 374의 벤치마크 전략 합의는 아직 별도 결과다.

## 검증 기록

확인 시각은 **2026-10-16 13:28–13:30 KST**다. 현재 상태와 과거 실험의 의미를 구분하기 위해 아래 대조를 수행했다.

| 확인 | 명령·결과 |
| --- | --- |
| 전체 이슈 | `cubrid-jira search CBRD-27193 -d <local-cache>`로 EPIC과 19개 자식을 새로 조회. `cubrid-jira jql 'parent = CBRD-27193 ORDER BY key ASC' --fields summary,status,issuetype,assignee,priority,updated,resolution,issuelinks --max 100 --output json`의 `total=19`, 반환 19건과 EPIC 연결 집합이 일치했다. 모두 Open·Minor, CBRD-27370만 Daehyun Kim 담당이다. |
| 소스 신원 | `git log -1 --format='%H %ci %s'`와 `git ls-remote origin refs/heads/develop` 모두 `4adcd409072b189f5d965bde5750c53176d90de0`. `git diff --quiet HEAD -- src/storage/page_buffer.c src/storage/double_write_buffer.cpp` 통과. 읽은 파일은 HEAD와 같았다. |
| 상위 3개 소스 | `rg -n`과 행 번호를 붙인 본문 확인으로 `page_buffer.c`의 빠른 경로(:2266–2282), 보호 등록(:2377–2380)·해제(:2465–2469), 중첩 WRITE의 전역 횟수 대입(:6364–6373)·스레드 횟수 증가(:6446–6452), flush 조기 반환(:10741–10768)·정상 오류 정리(:10846–10860)를 대조했다. 링크는 브리핑에 고정 revision으로 제공한다. |
| 관련 PR | 19개 자식과 연관 CBRD-27576 각각에 `gh pr list --repo CUBRID/cubrid --state all --search <issue-key> --limit 100 --json number,title,state,isDraft,mergedAt,headRefOid,baseRefName,url,updatedAt` 실행. 상위 3개 번호 검색 결과는 각각 0건이다. 검색만으로 모든 수정 부재를 증명하지 않으므로 현재 소스 대조를 함께 사용했다. |

## 후보를 고른 이유와 상태 대조

- **CBRD-27263:** [기존 계측 보고서](../pgbuf-analysis/e6ed61e_claude/10-CBRD-27263-repro-proof-and-solutions.md)는 `e6ed61e87`에서 등록 없는 해제와 양수 보호 카운터 감소를 기록했다. 이번에는 해당 제어 흐름의 잔존을 확인했다. 그 결과만으로 현재 데이터 손상이나 고객 노출을 확정하지 않는다.
- **CBRD-27370:** [현재 이슈](https://jira.cubrid.org/browse/CBRD-27370)의 SA probe는 `11.5.0.2431-198b42a` debug 빌드에서 전역 1/스레드 3을 기록하고, 별도 `f799e05` debug/release 교차 확인과 unfix 결과를 설명한다. 현재도 두 대입이 남아 있다. API의 일반 승격 허용/금지 정책과 실제 SQL 호출 범위는 후속 검토 대상이다. 담당자는 JIRA의 현 담당자를 유지하는 제안이다.
- **CBRD-27262:** [현재 이슈](https://jira.cubrid.org/browse/CBRD-27262)는 `e6ed61e87` 오류 주입 결과를 기록한다. 이번에는 조기 반환이 정상 오류 정리를 거치지 않는 사실을 확인했다. 곁가지 `dwb_read_page()` 실패 분기는 현재 [`double_write_buffer.cpp:3979–4015`](https://github.com/CUBRID/cubrid/blob/4adcd409072b189f5d965bde5750c53176d90de0/src/storage/double_write_buffer.cpp#L3979-L4015)의 모든 정상 반환이 `NO_ERROR`이므로 운영에서 발생하는 오류로 제시하지 않았다. 브리핑의 근거는 TDE/DWB 쓰기 준비 실패 경로다.
- **CBRD-27630:** 현재 `page_buffer.c`의 helper 정리(:8428, :8485, :8508), simple-fix 호출자 재정리(:2643–2647), VPID로 기록을 찾는 제거 함수(:8063 이후)를 대조했다. [이슈와 고정 리비전 모델](https://jira.cubrid.org/browse/CBRD-27630)은 유용한 반례지만 실제 엔진의 동일 임시 VPID 동시 호출과 실패 도달성은 미확인이다. 기존 엔진 실행 근거가 있는 회계 후보를 먼저 제안하고 이 항목은 후속 검증에 둔다.
- **CBRD-27266:** 기존 EPIC의 `SHOW PAGE BUFFER STATUS` 누락 주장을 현재 사실로 복제하지 않았다. [PR #7592](https://github.com/CUBRID/cubrid/pull/7592)는 2026-08-21 병합됐고, merge commit `667f1c8dce9bb4e845edc5e4ad8c9f9092355320`은 9개 폐기 counter 컬럼에 NULL을 반환하도록 바꿨다. 통계 의미 전체가 해결됐다는 결론은 아니다.
- **주변 PR:** [CBRD-27576 / #8169](https://github.com/CUBRID/cubrid/pull/8169)는 Open·Draft, HEAD `21b3a680a2ad37515a1ca92cffdba3d527a02fd1`이며 변경 파일은 `heap_file.c` 하나다. 별도 heap/vacuum 문제의 수정 제안으로, CBRD-27263의 보호 카운터 수정이나 그 결함의 데이터 손상 재현으로 간주하지 않는다. [CBRD-27398 / #7940](https://github.com/CUBRID/cubrid/pull/7940)은 Open·Draft, HEAD `6bf4753eaa136fb87a4632deac44dc403ad0538e`다. [#7630](https://github.com/CUBRID/cubrid/pull/7630)은 CBRD-27198의 국소 수정을 병합했으며, 연결된 CBRD-27356의 공통 latch 정책 이슈는 Open이다.

## 범위와 후속 확인

이번 준비는 소스·이슈·PR 대조다. 엔진 빌드, 재현·오류 주입, CI, 벤치마크 또는 Lean 검증을 새로 실행하지 않았다. 소스 전체 감사와 릴리스 포함 범위 확인도 수행하지 않았다. 기존 분석의 기준 revision과 실행 결과를 현재 재현 결과로 취급하지 않는다.

전체 목록은 [현재 parent JQL](https://jira.cubrid.org/issues/?jql=parent%20%3D%20CBRD-27193%20ORDER%20BY%20key%20ASC)과 [EPIC의 연결 목록](https://jira.cubrid.org/browse/CBRD-27193)에서 연다. JIRA HTTPS 주소는 확인 시 HTTP 주소로 리다이렉트됐다. 10/19 회의 직전 목록·담당자·PR·develop을 다시 확인한다. 원시 조회·캐시는 로컬 작업 자료로만 보관한다.

작업 373은 **자료 준비**와 **현장 결정**을 구분한다. 벤치마크·병목 조사 전략 합의는 별도 작업 374이며, [CBRD-27423](https://jira.cubrid.org/browse/CBRD-27423)과 [10/2 후보 분석](../pgbuf-analysis/report-2026-10-02.md)을 연결한다. Lean은 작은 pgbuf 하위 작업으로 유지하며 별도 대규모 계획이나 필수 설계·PR gate로 확정하지 않는다.
