# PR 7990 필수 TC 리뷰 처리: cubrid-testcases#3551, cubrid-testcases-private-ex#4210

작성: 2026-11-11 (Asia/Seoul). Work911. 독자: 작성자와 TC·엔진 리뷰어.

## 질문과 결론

- 질문: #3551의 CHANGES_REQUESTED(넓은 행 -1388을 답지에 기록)를 어떻게 처리하고, 두 TC PR을 어떤 순서로 머지하는가.
- 결론: 기대값을 되돌리지 않는다. 같은 리뷰어(shparkcubrid)가 엔진 PR에서 블로킹을 철회했다([r4386842256](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4386842256)). 철회 조건인 릴리스 노트 요청에는 아직 답이 없다. 그래서 회신에서 릴리스 노트 문안을 함께 제시한다.
- 다중 LOB 지적(Greptile P2)은 타당하다. 행을 거부하는 기준은 측정으로 확인했다. LOB 400개를 채운 행은 한도 안에 들어간다. 그래서 b001·c001 두 개만 채운 희소 행을 LOB 400개 행으로 바꾸는 후보 커밋을 만들었다(answer 변경 없음). 반영 여부는 작성자가 정한다.

## 기준 리비전 (2026-11-11 재조회)

| 대상 | 리비전 | 상태 |
| --- | --- | --- |
| 엔진 PR #7990 head | `dfbf3d82c49f` | OPEN, CHANGES_REQUESTED(shpark 10-27 리뷰가 아직 유효), `Check TC PRs` 실패 |
| #3551 `tc/pr-7990` | `b53a7984c` | OPEN, CHANGES_REQUESTED, TC develop보다 11커밋 뒤, merge-tree 충돌 없음 |
| #4210 `tc/pr-7990` | `8ef4f6278` | OPEN, APPROVED(swi0110, kwonhoil), develop보다 8커밋 뒤, 충돌 없음 |

TC 저장소의 `feature/oos-merge`는 각 `tc/pr-7990`보다 develop revert 커밋 1개(#4129, #4827)만 앞선다. 두 revert는 TC develop에 이미 들어 있으므로 PR 내용에서 빠진 것은 없다.

## 리뷰 코멘트 전수 (inline, review 본문, 대화 탭)

| PR | 코멘트 | 내용 | 처리 |
| --- | --- | --- | --- |
| 3551 | shpark review (CHANGES_REQUESTED) | -1388 답지 기록만 지적 | 아래 회신 A 후 재리뷰 요청 |
| 3551 | inline [4385249339](https://github.com/CUBRID/cubrid-testcases/pull/3551#discussion_r4385249339) `bug_bts_10516.answer` | 엔진이 고쳐지면 답지와 희소 행을 되돌려야 함 | 전제(엔진 수정)가 철회됨. 회신 A |
| 3551 | inline [4385249346](https://github.com/CUBRID/cubrid-testcases/pull/3551#discussion_r4385249346) `fbo_ddl02.answer` | 같은 내용 | 회신 A' |
| 3551 | Greptile inline [4139602561](https://github.com/CUBRID/cubrid-testcases/pull/3551#discussion_r4139602561) | 희소 행 때문에 다중 LOB 검증 축소 | 타당. 회신 B |
| 3551 | Greptile summary | Low impact, 차단 문제 없음 | 조치 없음 |
| 3551·4210 | tc-sync-bot 10-26 "closed" 코멘트 | 엔진 PR이 잠시 닫혔을 때의 자동 코멘트. 두 PR은 다시 OPEN | 조치 없음 |
| 4210 | inline 없음 | 승인 2건 | 본문 갱신만 필요 |

## 넓은 행 -1396의 경위와 동작

1. 10-27 05:02 shpark가 엔진([r4385247873](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4385247873))과 TC #3551에서 블로킹으로 지적했다.
2. 06:49 작성자가 CBRD-26937 설계 결정이라고 답했다.
3. 09:08 shpark가 블로킹을 철회하고 릴리스 노트 기재를 요청했다. 요청 내용은 "넓은 행 거부"와 "이전 버전 unloaddb 데이터의 loaddb 실패 가능성"이다. 이 요청에는 아직 답이 없다(2026-11-11 재조회).
4. 오류 번호는 develop 동기화로 -1388에서 -1396으로 바뀌었다. TC head의 answer(`Error:-1396`)는 엔진 `dfbf3d8`의 `src/base/error_code.h:1803`과 일치한다.

엔진 규칙(`dfbf3d8`, `src/storage/heap_file.c:14864-14870`, `heap_attrinfo_determine_disk_layout`): 행이 `DB_PAGESIZE/4`를 넘으면 24바이트(`OR_OOS_INLINE_SIZE`, `object_representation.h:528`)보다 큰 가변 컬럼 값을 큰 것부터 OOS로 옮긴다. 하나라도 옮겼는데 남은 행이 `heap_Maxslotted_reclength`(16KB 페이지에서 16,236B)를 넘으면 -1396으로 거부한다. 옮길 값이 없는 큰 행(고정 길이 컬럼만 큰 행 등)은 이전처럼 REC_BIGONE으로 저장된다. LOB 컬럼은 locator 문자열이 24바이트를 넘으므로 OOS로 옮겨진다.

측정(debug 빌드 `dfbf3d8`, 16KB 페이지, csql -S, 1000 LOB 컬럼 테이블): 채운 LOB 개수 k에 대해 남은 행 크기 = 2,036 + 24k.

| 채운 LOB | 남은 크기 | 결과 |
| --- | --- | --- |
| 400 | 11,636 | 성공 |
| 600 | 16,436 | -1396 |
| 800 | 21,236 | -1396 |
| 1000 | 26,036 | -1396 |

한도는 k = 591이다. 1000개를 채운 원래 행은 어떤 OOS 배치로도 들어갈 수 없다.

## 다중 LOB 보강 후보

- 커밋: `cubrid-testcases` 로컬 브랜치 `CBRD-26357-tc3551-dense-lob`의 `7bc7d7237`(base `b53a7984c`, push 안 함). 두 case의 희소 행을 b001..b200, c001..c200을 채운 행으로 바꾼다. 이후 SELECT는 count와 b001·c001만 출력하므로 answer는 그대로다.
- 효과: `insert ... select` 세 번, UPDATE, DELETE가 행마다 LOB 400개(8행 기준 3,200개)를 처리한다. 지금 head는 행마다 2개뿐이다. 1000개 행의 거부 경로는 그대로 검증된다.

## 검증 (native cubrid-testkit, 엔진 `dfbf3d8` debug, 시도별 디렉터리 보존)

| 시도 | TC | case | 결과 |
| --- | --- | --- | --- |
| `~/tk/t911a` | `b53a7984c` | `bug_bts_10516` | PASS (total 1, success 1, fail 0) |
| `~/tk/t911b` | `b53a7984c` | `fbo_ddl02` | PASS (1/1, fail 0) |
| `~/tk/t911c` | `7bc7d7237` | `bug_bts_10516` | PASS (1/1, fail 0) |
| `~/tk/t911d` | `7bc7d7237` | `fbo_ddl02` | PASS (1/1, fail 0) |

각 시도는 `testkit-focused.py verify`로 판정했다(기대 case 일치, summary·XML·`.result` 존재, 실패 0). 현재 head와 보강 후보 모두 OOS 엔진 head에서 통과한다.

## PR 본문에서 고칠 부분

- #3551: `-1388` → `-1396`. `medium/_02_xtests/7105` 행 삭제. TC develop #4110(CBRD-27836, 11-10)이 같은 `order by`를 넣어 diff에서 빠졌다. 그래서 "3개(파일 5개)"를 "2개(파일 4개)"로 고친다. 머지 순서 문단의 7105 언급도 지운다.
- #4210: `-1387,-1389,-1390` → `-1395,-1397,-1398`. `file_enc_05` 행 삭제. TC develop #4089(CBRD-27151, 11-09)가 이 case의 answer 파일을 없애고 스크립트 검사로 바꿨다. "17개(파일 26개)" → "16개(파일 25개)". 검증 문단을 최신 run으로 갱신한다(run 42819814597에서 `8ef4f6278`로 오류 번호 case 3건 통과, [cbrd-27785/ci-analysis-855f220.md](../cbrd-27785/ci-analysis-855f220.md)).

## 머지 순서

1. #3551 CHANGES_REQUESTED 해소: 회신 A·B 게시 후 shpark 재리뷰(승인 또는 review dismiss). 엔진 쪽에는 회신 C로 릴리스 노트에 답한다.
2. 두 TC PR 본문 갱신. 보강 후보를 채택하면 `tc/pr-7990`에 반영하고 CI를 다시 돌린다.
3. 엔진 머지 직전에 `error_code.h` 번호를 다시 확인한다. develop에 오류 코드가 추가되면 answer 7개 파일을 다시 맞춘다.
4. #3551, #4210을 TC develop에 머지한다. 이 사이에는 develop 엔진에 OOS가 없으므로 해당 case가 실패한다(추론).
5. 엔진 #7990의 `Check TC PRs`를 다시 실행한 뒤 엔진을 머지한다.

보강 TC #3688/#4365의 리뷰는 develop 머지 뒤로 미룬 결정을 유지한다.

## 회신 초안 (게시 전 승인 필요)

**A. #3551 inline 4385249339에 대한 답**

> 엔진 PR 쪽 같은 지적에서 블로킹을 철회해 주셨습니다([r4386842256](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4386842256)). OOS로 옮길 수 있는 값을 모두 옮긴 뒤에도 행이 최대 레코드 크기를 넘으면 오류로 처리하는 것이 엔진 동작으로 확정되었습니다(CBRD-26937). 그래서 이 answer는 되돌리지 않고 유지합니다. 오류 번호는 develop 동기화로 -1396이 되었고, 엔진 head `dfbf3d8`의 값과 같습니다.
>
> 이 행은 OOS 배치를 어떻게 해도 들어갈 수 없습니다. LOB 1000개를 모두 옮기면 행에 24바이트 stub 1000개가 남아 26,036바이트가 됩니다. 한도는 16,236바이트입니다. 요청하신 릴리스 노트는 엔진 PR 스레드에 문안을 남겼습니다.

**A'. inline 4385249346:** "bug_bts_10516과 같은 이유로 유지합니다. 위 답글을 참고해 주세요."

**B. Greptile 4139602561에 대한 답 (보강 후보를 채택한 경우)**

> 맞는 지적이라 보강했습니다. LOB 400개를 채운 행은 11,636바이트로 한도 안에 들어갑니다(측정한 한도는 591개). 희소 행을 이 행으로 바꿔서, `insert ... select`, UPDATE, DELETE가 행마다 LOB 400개를 처리하도록 했습니다. answer는 바뀌지 않습니다.

**C. 엔진 #7990 스레드 r4386842256에 대한 답과 릴리스 노트 문안**

> 확인 감사합니다. 릴리스 노트에 아래 내용을 넣겠습니다.
>
> - 큰 가변 길이 값을 OOS로 옮긴 뒤에도 행의 남은 크기가 최대 레코드 크기(16KB 페이지에서 16,236바이트)를 넘으면, 이 행의 INSERT와 UPDATE는 `ER_HEAP_OOS_OVERPASS_MAXOBJ_SIZE`로 실패합니다. 이전 버전은 이런 행을 overflow 레코드로 저장했습니다. 주로 수백 개의 가변 길이 컬럼이나 LOB 컬럼을 동시에 채운 행이 해당합니다.
> - 이전 버전에서 unloaddb한 데이터에 이런 행이 있으면 loaddb에서 해당 행이 실패할 수 있습니다.
> - OOS로 옮길 값이 없는 큰 행은 영향이 없습니다. 예를 들면 고정 길이 컬럼만 큰 행이나, 모든 가변 값이 24바이트 이하인 행입니다. 이런 행은 이전처럼 저장됩니다.

## 한계와 미결

- 측정과 실행은 debug 빌드에서 했다. CI에서는 release 빌드도 돈다.
- 페이지 크기별 한도는 16KB 페이지만 측정했다.
- 보강 후보를 채택할지, 릴리스 노트를 어디에 기록할지(JIRA, 릴리스 문서)는 작성자가 정한다.
- 회신 게시, 스레드 resolve, TC push와 머지는 별도 승인 대상이다.
