# CBRD-26357: engine PR #7990 body context

Prepared: 2026-10-27, Asia/Seoul. Agent: `claude`.
Status: prepared for review; not published.
This context does not establish publication permission.

## Source and target

| Field | Value |
| --- | --- |
| Ticket | https://jira.cubrid.org/browse/CBRD-26357 |
| Operation | `update` existing body |
| Target repository | `CUBRID/cubrid` |
| PR | https://github.com/CUBRID/cubrid/pull/7990 |
| Existing title | `[CBRD-26357] Add out-of-row overflow storage` |
| Title operation | Preserve |
| PR state | `OPEN`, draft=`false` |
| Draft/ready operation | Preserve |
| Source repository | `CUBRID/cubrid` |
| Source branch | `feature/oos-merge` |
| SOURCE_COMMIT | `5a70787feea9e0488222af7e3a0249cc431562ca` |
| Observed remote head | `5a70787feea9e0488222af7e3a0249cc431562ca` |
| Base branch | `develop` (merge base `4781495f0`) |
| Recorded CI | gha-ci run 40349442612 |
| Original decoded GitHub body SHA-256 | `16c3e16cc918b9089ab2c28028a5f60b24fd517c1d2be64630851b85bb424273` |

## Saved material

- Body: [CBRD-26357-oos-engine-pr-body_5a70787_claude.md](CBRD-26357-oos-engine-pr-body_5a70787_claude.md).
- Detailed explanation: [CBRD-26357-oos-engine_5a70787_claude.md](CBRD-26357-oos-engine_5a70787_claude.md), public URL `https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-oos-engine_5a70787_claude.md`.
- Docs task branch: `docs/pr7990-engine-pr-body-20261027`. Integration branch: `main` of `vimkim/my-cubrid-docs`.

## Reconciliation with the original body

The original body said the changes were still being prepared. Its only substantive section, "인덱스 용량 TC 기대값 조정", described the `cbrd_24916_check_index_ovfps` answer change in testcase commit `046d0e2f8`. That change no longer reaches the testcase PR: the develop merge `fea33d9fe` took the newer develop answers (`c79be6f9c`, CBRD-27247), and the case passed on the OOS engine. The new body therefore drops that section. Its historical explanation remains in [CBRD-26357-oos-index-capacity_3252fcf_codex.md](CBRD-26357-oos-index-capacity_3252fcf_codex.md) and the testcase report.

Original body, for reference:

> https://jira.cubrid.org/browse/CBRD-26357
>
> ## Purpose
>
> OOS (큰 컬럼 값을 별도로 저장하는 기능)의 develop 병합을 준비합니다.
>
> ## Implementation
>
> 변경 사항은 준비 중이며 후속 커밋으로 추가할 예정입니다.
>
> ## Remarks
>
> 준비 중인 Draft PR입니다.
>
> ### 인덱스 용량 TC 기대값 조정
>
> - `tc/pr-7990`의 `cbrd_24916_check_index_ovfps` answer 파일 5개에서 숫자 6줄만 조정합니다. 원본 스크립트와 13개 검사를 유지합니다.
> - OOS의 `oos_vfid` 필드로 힙 헤더(테이블 저장 파일의 관리 정보)가 8바이트 커집니다. OID(행의 물리 주소) 배치가 달라져 인덱스 오버플로 페이지가 다르게 분할됩니다.
> - `xx1/xx2`의 총 오버플로 페이지 수를 `278/280`에서 `274/282`로, `xx1`의 키당 정수 평균을 `55`에서 `54`로 갱신합니다.
> - `1a8c705`에서 원시 볼륨 검사와 `checkdb`로 페이지 수 및 데이터 무결성을 확인했습니다. 기준 엔진의 헤더만 8바이트 늘린 실험도 OOS와 같은 배치를 재현했습니다.
>
> ### Test Plan
>
> - develop `60ad770f0`에서 원본 TC의 13개 검사가 모두 통과했습니다.
> - OOS `3252fcf`에서 수정 전 5개 검사의 불일치를 재현했습니다. 기대값 수정 후 새 DB에서 13개 검사와 실행 산출물 검증이 모두 통과했습니다.
> - 이 결과는 해당 TC 한 건의 로컬 OptDebug 검증입니다. 전체 CI 통과를 뜻하지 않습니다.
> - [수정 근거와 검증 범위](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-oos-index-capacity_3252fcf_codex.md)
>

## Evidence used

- Code read at `5a70787fe` (`git diff origin/develop...5a70787fe`), the OOS specification at cubrid-oos-context `c6fc51b`, and Greptile review threads as of 2026-10-27.
- Collected evidence of gha-ci run 40349442612; local OOS CTest 33/33 at `5a70787fe`.

## Proposed operations

1. Commit the body, context, explanation, and README rows on the docs task branch; rebase onto `main`, fast-forward `main`, and push `origin main`.
2. Verify the explanation URL serves the reviewed file.
3. Update the body of PR #7990 with `gh pr edit 7990 --repo CUBRID/cubrid --body-file <body>`. Keep the title and draft/ready state.
4. Verify the published body SHA-256 equals the body file SHA-256 and record the result here.

No source push is needed.
