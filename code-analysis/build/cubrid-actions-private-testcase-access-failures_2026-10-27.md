# CUBRID CI 준비 단계 실패 — QA 공유

작성일: 2026-10-27 · 대상: CUBRID/cubrid GitHub Actions

## 목적

여러 PR에서 반복된 CI 준비 단계 실패를 공유하고, private testcase 저장소 접근 상태 점검을 요청합니다.

## 문제

`CUBRID/cubrid-testcases-private-ex` 저장소의 checkout 또는 브랜치 조회가 실패해 테스트를 시작하지 못하는 사례가 발생했습니다. PR #8023에서는 shell shard 50개가 testcase revision 정렬 단계에서 실패했습니다.

## 문제 원인

- **확인된 직접 원인:** private testcase 저장소 접근 실패. 로그에 `repository ... not found` 또는 `could not reach ... after 5 attempts`가 기록됐습니다.
- **미확인 사항:** 접근 실패의 세부 원인. CI 인증 정보, 저장소 접근 권한, 네트워크 상태 확인이 필요합니다.
- **타임아웃·자원 부족:** 확인한 로그에서 직접 원인으로 확인되지 않았습니다.

## 대표 사례

아래 세 실행은 PR 작성자가 직접 CI 실행을 요청했습니다. 이름과 계정은 GitHub 공개 프로필 기준입니다.

| PR | PR 작성자 / CI 실행 요청자 | PR 제목 | 확인된 실패 |
| --- | --- | --- | --- |
| [#8023](https://github.com/CUBRID/cubrid/pull/8023) | Yeunjun Lee ([@YeunjunLee](https://github.com/YeunjunLee)) | [CBRD-27452] Read all_pages_written before num_pages in the DWB file sync helper | shell shard 50개가 정렬 단계에서 실패. [대표 로그](https://github.com/CUBRID/cubrid/actions/runs/40464952350/job/122060680413)에서 저장소 `not found` 및 checkout 재시도 소진 확인 |
| [#8211](https://github.com/CUBRID/cubrid/pull/8211) | Kwang Soo Chae ([@kwangsoochae](https://github.com/kwangsoochae)) | [CBRD-27336] Bind a source column in the ON DUPLICATE KEY UPDATE clause of a remote INSERT ... SELECT | [plan 로그](https://github.com/CUBRID/cubrid/actions/runs/40466160215/job/122071415373)에서 private 저장소의 브랜치 조회 5회 실패 |
| [#7990](https://github.com/CUBRID/cubrid/pull/7990) | Daehyun Kim ([@vimkim](https://github.com/vimkim)) | [CBRD-26357] Add out-of-row overflow storage | [shell 10 로그](https://github.com/CUBRID/cubrid/actions/runs/40464422209/job/122056942616)에서 동일 저장소 `not found` 및 checkout 재시도 소진 확인 |

## 확인 요청

1. CI의 GitHub App/token이 private testcase 저장소에 접근할 수 있는지 확인
2. runner에 인증 정보가 정상 전달되는지, 해당 시간대 네트워크 오류가 있었는지 확인
3. 접근 문제 조치 후 영향받은 CI 재실행

확인 범위는 각 실행의 attempt 1 준비 단계 로그입니다. 같은 저장소 접근 실패가 반복된 사실을 확인했으며, PR 코드 변경과의 인과관계나 전체 테스트 결과를 판정한 보고서는 아닙니다.

CI 입력 커밋: #8023 [`a8d0719`](https://github.com/CUBRID/cubrid/commit/a8d071918e069cb0d5816f373e54006eadc8aa18) · #8211 [`cfe290b`](https://github.com/CUBRID/cubrid/commit/cfe290bd40c6aa9128235c7804d289da04493487) · #7990 [`dcbf09e`](https://github.com/CUBRID/cubrid/commit/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67)
