# CBRD-27791: OOS batch read

이 안내 갱신: 2026-10-28, Asia/Seoul.

OOS는 큰 값을 행 본문 밖에 저장하고, 조회에 필요한 값만 따로 읽는 방식이다. 작은 컬럼만 조회할 때는 읽는 양을 줄일 수 있지만, 큰 값의 내용을 조회할 때는 따로 저장된 위치를 따라가며 읽는 비용이 생긴다. 이 문서 묶음은 그 비용을 확인하고, 여러 읽기 요청을 제한된 범위에서 모아 처리하는 batch read를 검토하기 위해 만들었다.

처음 읽는다면 분석 보고서에서 저장·조회 흐름과 측정 결과를 이해한 뒤, 구현·검증 계획에서 다음 작업을 확인한다. 문제의 사용자 영향과 분석을 배정할 이유부터 확인하려면 별도 저장소의 [JIRA 본문 초안](https://github.com/vimkim/my-cubrid-jira/blob/main/issues/CBRD-27791-oos-batch-read_dcbf09e_codex.md)을 읽는다.

현재 결과는 기존 엔진을 그대로 실행한 SQL 측정과, 읽기 요청만 엔진 밖에서 다시 실행한 실험이다. batch read를 엔진에 적용했을 때의 SQL 성능과 비용은 후속 구현에서 확인해야 한다. 이번 문장 개정은 기존 측정의 수치와 조건을 유지하면서 설명을 고쳐 쓴 작업이다.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [상세 분석·재측정](CBRD-27791-oos-batch-read-analysis_dcbf09e_codex.md) | 작은 컬럼 조회의 이득과 큰 값 조회의 비용, 두 실험의 차이와 결과의 한계 | 2026-10-28 | 2026-10-28 | 엔진에서 검토할 batch 범위와 근거를 확인한다. |
| [구현·검증 계획](CBRD-27791-oos-batch-read-plan_dcbf09e_codex.md) | 무엇부터 바꾸고 검증할지, 각 단계의 이유와 중단 기준, 아직 결정할 사항 | 2026-10-28 | 2026-10-28 | 후속 구현을 검토 가능한 단계로 나눈다. |

수치의 근거 자료와 실험 입력·재생 도구는 분석 보고서에서 연결한다. 원시 로그와 읽기 요청 기록은 Git에 넣지 않고 기존 근거 위치에 보존한다.

관련 이슈는 [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791), 상위 이슈는 [CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978)이며, OOS 변경은 [PR #7990](https://github.com/CUBRID/cubrid/pull/7990)과 관련된다. 위의 JIRA 본문 초안과 실제 이슈 본문은 별도로 관리한다.
