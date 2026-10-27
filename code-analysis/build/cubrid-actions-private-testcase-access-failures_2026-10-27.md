# CUBRID GitHub Actions: private testcase 저장소 접근 실패 사례

- 작성일: 2026-10-27 (Asia/Seoul)
- 수신: QA 팀
- 대상: [CUBRID/cubrid](https://github.com/CUBRID/cubrid)의 `gha-ci.yml`
- 범위: 제보된 PR #7990과 다른 PR 2건에서 발생한 CI 준비 단계 실패

서로 다른 작성자의 PR #7990, #8023, #8211에서 `CUBRID/cubrid-testcases-private-ex` 저장소에 접근하지 못해 테스트 준비가 중단된 사례를 확인했습니다. 확인한 로그의 직접 실패 원인은 저장소 접근 실패입니다. 이 사례들만으로 타임아웃이나 CPU·메모리 부족을 원인으로 확정할 수는 없습니다.

## 1. PR 제목과 작성자

작성자는 PR을 등록한 GitHub 계정이며, CI 실행 요청자는 해당 Actions 실행의 `actor`와 `triggering_actor`입니다. 아래 세 실행에서는 두 계정이 같습니다. 이름은 GitHub 공개 프로필의 표기를 사용했습니다.

| PR | 정확한 PR 제목 | PR 작성자 | CI 실행 요청자 |
| --- | --- | --- | --- |
| [#8023](https://github.com/CUBRID/cubrid/pull/8023) | [CBRD-27452] Read all_pages_written before num_pages in the DWB file sync helper | Yeunjun Lee — [@YeunjunLee](https://github.com/YeunjunLee) | @YeunjunLee |
| [#8211](https://github.com/CUBRID/cubrid/pull/8211) | [CBRD-27336] Bind a source column in the ON DUPLICATE KEY UPDATE clause of a remote INSERT ... SELECT | Kwang Soo Chae — [@kwangsoochae](https://github.com/kwangsoochae) | @kwangsoochae |
| [#7990](https://github.com/CUBRID/cubrid/pull/7990) | [CBRD-26357] Add out-of-row overflow storage | Daehyun Kim — [@vimkim](https://github.com/vimkim) | @vimkim |

## 2. 다른 PR에서 확인한 실패

### PR #8023 — Yeunjun Lee (@YeunjunLee)

- Actions: [run 40464952350, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/40464952350/attempts/1)
- 실행 생성 시각: 2026-10-27 16:04:56 KST
- 실행 결과: `completed / failure`
- 영향: shell shard 50개가 `Align CTP and testcases to the commits plan saw` 단계에서 실패했습니다.
- 대표 근거: [shard shell 04 로그](https://github.com/CUBRID/cubrid/actions/runs/40464952350/job/122060680413)

대표 shard에서 `repository ... not found` 오류가 5회 반복됐습니다. 이후 checkout 재시도가 소진됐고, CTP 결과 파일 없이 종료됐습니다. 로그 발췌는 다음과 같습니다.

```text
fatal: repository 'https://github.com/CUBRID/cubrid-testcases-private-ex.git/' not found
** ERROR: checkout of cubrid-testcases-private-ex (263b22e7c11cd6eb62d2e31a1144ace425f2b5b6) failed after retries
no CTP result file: the tests did not run
```

이 shard는 테스트를 실행하기 전에 실패했습니다. 로그에 기록된 메모리 최대 사용량은 `0.8 GiB`입니다. 이 수치와 오류 메시지만으로 노드 전체의 자원 상태를 판단할 수는 없지만, 해당 로그에는 OOM 또는 작업 시간 제한 초과를 직접 실패 원인으로 볼 근거가 없습니다.

### PR #8211 — Kwang Soo Chae (@kwangsoochae)

- Actions: [run 40466160215, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/40466160215/attempts/1)
- 실행 생성 시각: 2026-10-27 16:16:44 KST
- 실행 결과: `completed / failure`
- 실패 단계: `plan` → `Refresh testcases, decided once here`
- 근거: [plan 로그](https://github.com/CUBRID/cubrid/actions/runs/40466160215/job/122071415373)

private testcase 저장소의 `tc/pr-8211` 브랜치를 확인하는 `ls-remote`가 종료 코드 128로 5회 실패했습니다. 최종 오류는 다음과 같습니다.

```text
could not reach https://github.com/CUBRID/cubrid-testcases-private-ex.git after 5 attempts
```

테스트 계획을 준비하는 단계에서 중단됐습니다. #8023과 같은 저장소에 접근하지 못한 사례이지만, 이 로그만으로 두 실행의 인증·네트워크 원인이 동일하다고 확정할 수는 없습니다.

## 3. 제보된 실행과 비교

### PR #7990 — Daehyun Kim (@vimkim)

- Actions: [run 40464422209, attempt 1](https://github.com/CUBRID/cubrid/actions/runs/40464422209/attempts/1)
- 실행 생성 시각: 2026-10-27 15:59:53 KST
- 조회 시점 상태: `in_progress` — 전체 실행의 최종 결과는 아직 확인하지 않았습니다.
- 대표 근거: [shard shell 10 로그](https://github.com/CUBRID/cubrid/actions/runs/40464422209/job/122056942616)

`Align CTP and testcases to the commits plan saw` 단계에서 #8023의 대표 shard와 같은 `repository ... not found` 오류가 5회 반복됐습니다. checkout 재시도가 소진됐고, `no CTP result file: the tests did not run`으로 종료됐습니다. 해당 shard의 메모리 최대 사용량도 `0.8 GiB`로 기록됐습니다.

## 4. QA 확인 요청

여러 PR에서 동일 private testcase 저장소에 접근하지 못한 현상이 반복됐으므로, CI의 저장소 접근 경로를 우선 확인해 주시기 바랍니다.

1. CI에서 사용하는 GitHub App/token의 `CUBRID/cubrid-testcases-private-ex` 접근 권한과 유효 상태
2. 실패한 runner에서 private 저장소의 `ls-remote` 및 checkout에 인증 정보가 전달되는지 여부
3. 해당 시간대 저장소 접근·네트워크 오류와 성공한 shard 간 차이

권한·인증·네트워크 문제 중 어느 항목이 원인인지는 아직 확인하지 않았습니다. 타임아웃·자원 부족 여부를 판단하려면 별도로 runner/node 지표와 해당 실패 로그를 확인해야 합니다.

## 5. 확인 범위와 실행 식별 정보

PR 제목·작성자, 공개 프로필 이름, 실행 요청자·시각·상태는 GitHub API에서 확인했습니다. 실패 단계와 shard 수는 각 실행의 attempt 1 전체 job 목록으로 확인했고, 위에 연결한 대표 job 로그를 직접 읽었습니다. 아래 SHA는 해당 대표 로그의 `SHA` 입력값입니다.

| PR | CI 입력 Engine SHA |
| --- | --- |
| #8023 | `a8d071918e069cb0d5816f373e54006eadc8aa18` |
| #8211 | `cfe290bd40c6aa9128235c7804d289da04493487` |
| #7990 | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |

세 실행의 이벤트는 `issue_comment`이며, workflow 메타데이터의 `head_sha`는 모두 `e07b3b09a26b711fa1a9f8ea66ab40e2c802b640`입니다. 이 workflow 참조 SHA와 위의 Engine 입력 SHA는 구분해야 합니다.

이 문서는 준비 단계의 접근 실패를 QA 팀에 공유하기 위한 사례 보고입니다. 전체 testcase 결과, PR 변경과 실패의 인과관계, merge-base 대비 회귀 여부는 분석하지 않았습니다.
