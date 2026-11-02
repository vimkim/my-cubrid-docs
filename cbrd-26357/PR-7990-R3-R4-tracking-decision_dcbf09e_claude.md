# PR7990 R3·R4의 CBRD 추적 단위 종합

2026-11-02 Asia/Seoul 작성. coordinator 종합이다.

사용자의 목표는 hornetmj의 PR7990 리뷰 R3와 R4를 각각 별도 CBRD Sub-task로 추적할지 정하는 것이다. 두 항목은 독립 agent가 따로 분석했다. 이 문서는 두 보고서의 권고를 검토하고, 같은 변경이 두 티켓에 중복 제안되는지 확인한 결과다. 두 agent의 결론은 바꾸지 않았다.

- R3 보고서는 [R3 sweep 비용 분석](PR-7990-R3-growth-sweep-cost_dcbf09e_claude.md)이다.
- R4 보고서는 [R4 재시작 후 bestspace 분석](PR-7990-R4-restart-bestspace_dcbf09e_claude.md)이다.

**후속 결정.** 2026-11-02 사용자가 R3를 [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)(Sub-task, 부모 CBRD-26583, 제목 `[OOS] [M2] sweep cost`)로 발급했다. R3 agent가 후속 처리 기준으로 제안한 CBRD-26978 대신 M2 운영 품질 묶음인 CBRD-26583을 골랐다. R1·R2·R5·R6 대응 이슈와 같은 부모다. 리뷰어가 R3를 병합 조건으로 보는지는 아직 확인하지 않았다. 같은 날 두 이슈의 설명과 제목을 JIRA에 반영했다. Relates 링크는 CBRD-27872와 CBRD-26786·CBRD-27213, CBRD-27213과 CBRD-27761·CBRD-26824로 만들었다. 두 이슈 본문은 이 종합을 반영해 my-cubrid-jira의 `issues/CBRD-27872-oos-growth-sweep-cost_dcbf09e_claude.md`와 `issues/CBRD-27213-oos-bestspace-shared-module_dcbf09e_claude.md`로 다시 썼다.

## 결론은 R3 신규 Sub-task, R4 기존 이슈 확장이다

| 항목 | R3. 할당 시 성장 게이트 sweep 비용 | R4. 재시작 후 bestspace 미복원 |
| --- | --- | --- |
| 원댓글 | [r4399899312](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4399899312), `oos_file.cpp:1868` | [r4409283403](https://github.com/CUBRID/cubrid/pull/7990#discussion_r4409283403), `oos_file.cpp:3081` |
| agent 결론 | `신규 Sub-task` | `기존 이슈 확장·연결` |
| 기존 이슈와의 관계 | 범위를 가진 live 이슈가 없다. 원 설계인 [CBRD-26786](https://jira.cubrid.org/browse/CBRD-26786)은 Resolved이고 병합됐으므로 다시 열지 않는다. CBRD-26786과 [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213)에 relates로 연결한다 | [CBRD-27213](https://jira.cubrid.org/browse/CBRD-27213)이 재시작 뒤 재사용을 결과 수준의 완료 조건으로 담는다. 하지만 현재 결함, 재현 시나리오, 원댓글 링크가 없어 본문 보강이 필요하다 |
| 제안 부모 | 사용자가 [CBRD-26583](https://jira.cubrid.org/browse/CBRD-26583)(Development Subject, M2) 밑에 [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)로 발급했다. 분석 당시 제안은 [CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978)(Task, 후속 처리)이었다 | CBRD-27213의 기존 부모 CBRD-26978을 유지한다. CBRD-27213이 Sub-task이므로 그 밑에 만들지 않는다. 신규로 전환하면 CBRD-26583 또는 CBRD-26978 |
| 제안 제목 | `[OOS] [TODO] 재시작이나 삭제 뒤 새 OOS 페이지를 할당하는 INSERT가 파일 크기에 비례해 느려진다` | `[OOS] [TODO] 재시작 뒤에도 OOS 빈 공간을 재사용하도록 bestspace를 heap 재설계 기반으로 전환` (CBRD-27213 제목 변경안) |
| 최소 완료 조건 | 새 페이지 할당 한 번의 회수 검사량이 파일 크기와 무관한 상한 이하다. fast path가 모두 회수한 삭제는 검사를 시작하지 않는다. 빈 페이지 반환 보장을 유지한다. OOS 명세 §4 불변식을 갱신하거나 유지 근거를 기록한다 | 부분 여유 페이지가 있는 파일을 정상 재시작한 뒤에도, 재시작하지 않은 대조군과 같은 수준으로 기존 페이지를 재사용한다. 힌트 용량 초과와 비정상 종료 뒤의 경우도 포함한다. 재사용 테스트는 운영 경로의 발동 조건을 거친다 |
| 처리 시점 | 후속. 단 R3 thread가 미해결이므로 리뷰어 동의가 필요하다 | 후속. 리뷰어가 "bestspace redesign 안정화 후 oos에 적용"을 밝혔다. 병합 PR에 알려진 제약으로 선언해야 한다 |
| 상대 항목과의 의존 | R4 없이 구현·검증할 수 있다 | CBRD-27213으로 처리하면 R3와 필수 의존이 없다. legacy 경로를 sweep hook으로 고치는 안을 고르면 R3의 sweep 계약이 먼저 정해져야 한다 |

## coordinator가 직접 확인한 근거

두 보고서의 결론이 기대는 주장을 source HEAD `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`와 OOS 명세 저장소 HEAD `3462a7f`에서 다시 읽었다. 확인 시각은 2026-11-02 19:43 KST다. 실행이나 측정은 하지 않았다.

R4 근거는 다음과 같다.

- `estimates.num_pages`를 쓰는 코드는 `oos_stats_sync_bestspace` 안의 `oos_file.cpp:985`, `1001` 두 곳뿐이다 [관찰].
- 운영 경로의 유일한 호출 `oos_file.cpp:3105`는 지역 변수 `tmp_hdr`를 넘긴다. 다른 호출자는 unit test용 `bridge_oos_stats_sync_bestspace`(`oos_file.cpp:3970`)뿐이다 [관찰].
- 그래서 실제 헤더의 `num_pages`는 0에 머물고, `oos_file.cpp:3081-3086`의 ratio 조건은 늘 거짓이다 [소스 추론]. 리뷰어도 gdb로 두 값이 0임을 보고했다 [리뷰어 보고].
- `03133632`(CBRD-26824 hotfix, 2026-06-29)의 diff에서 `|| try_find == 0`이 빠졌다 [관찰]. 이 hotfix 이후 운영 경로에서 sync가 실행되지 않는다.
- OOS 명세 `OOS-CONTEXT.md:170`의 "Recovery rediscovers free space through sync"는 현재 코드에서 성립하지 않는다 [소스 추론].

R3 근거는 다음과 같다.

- 발동 조건 `pending_deletes > 0 || !swept_this_boot`가 `oos_file.cpp:1868`에 있다 [관찰].
- `oos_delete`는 체인을 회수하면 호출자와 무관하게 `oos_reclaim_note_delete`를 부른다(`oos_file.cpp:3534-3537`) [관찰].
- lap은 첫 회수에서 cursor를 저장하고 반환한다. 회수 없이 한 바퀴를 돌면 `oos_reclaim_settle_lap`으로 정산한다(`oos_file.cpp:1975-1998`) [관찰].
- 명세 `OOS-CONTEXT.md:253`은 "reserves a new sector only when no safely reclaimable empty page exists **right now**"를 불변식으로 둔다 [관찰]. R3의 할당당 상한은 이 불변식을 완화하는 변경이다. 그래서 결함 수정이 아니라 승인된 설계를 바꾸는 성능 개선으로 분류한다.

## 중복 제안을 조정한다

두 보고서는 같은 변경을 서로 다른 티켓으로 요구하는 곳이 한 군데 있다.

R4 보고서의 CBRD-27213 보강 완료 조건 4번은 "재시작 뒤 재발견 순회와 CBRD-26786의 성장 게이트 sweep이 같은 섹터 비트맵을 중복 순회하지 않거나 근거를 기록한다. INSERT 한 건이 떠안는 순회량의 상한을 정한다"이다. R3 신규 Sub-task의 첫 완료 조건도 새 페이지 할당 한 번의 검사량 상한이다. 성장 게이트 sweep의 상한이 두 티켓에 함께 들어가면 어느 쪽이 끝났을 때 요구가 충족되는지 불분명해진다.

소유를 다음처럼 나눈다.

- **성장 게이트 sweep의 발동 조건과 할당당 상한은 R3 Sub-task가 소유한다.** CBRD-27213 보강문에서는 이 요구를 R3 Sub-task 링크로 대신한다.
- **CBRD-27213은 자신이 새로 도입하는 재발견 순회의 할당당 비용만 소유한다.** 완료 조건 4번은 "CBRD-27213의 재발견 순회가 INSERT 한 건에 더하는 순회량의 상한을 정한다. 성장 게이트 sweep과의 중복 순회 처리는 R3 Sub-task의 sweep 계약에 맞춘다"로 줄인다.
- 그 밖의 겹침은 중복이 아니다. R3 Sub-task는 "R4 자체는 이 이슈 범위가 아니다"라고 명시했다. R4 보고서는 R3 요구를 CBRD-27213에 넣지 않았다.

## 판단을 달리한 근거 하나

R4 agent는 legacy 경로의 별도 수정을 기각하면서 "사용자가 2026-11-02 R3·R4를 차주 계획에서 보류했다"는 사실을 근거로 들었다. 일정 보류는 언제 일할지에 관한 결정이고, 어느 티켓으로 추적할지에 관한 근거는 아니다. 그래서 이 근거를 빼고 다시 따져 보았다.

남는 근거만으로도 결론은 같다. 리뷰어가 redesign 뒤 적용을 밝혔고, CBRD-27213이 hash, `best[]`, sync를 삭제하면 legacy 수정도 함께 사라지며, 영향은 정합성이 아니라 공간이다. 다만 이 결론은 "OOS legacy bestspace가 이 결함을 가진 채 릴리스되어도 된다"는 전제에 기대고 있다. 그 전제는 아직 아무도 확인하지 않았다. 아래 열린 결정 1번이 그 전제다.

R3 agent가 같은 일정 보류를 처리 시점의 근거로 든 것은 타당하다. 처리 시점은 일정 결정이기 때문이다.

## 열린 결정은 팀과 리뷰어의 몫이다

두 결론은 다음 두 결정에 따라 바뀐다. 코드나 측정으로는 정할 수 없다.

1. **OOS가 legacy bestspace로 develop 병합이나 11.5 릴리스에 들어가는가.** 들어가고 CBRD-27213 착수가 늦어지면, 재시작마다 부분 여유 공간이 버려지는 상태로 출시된다. 팀이 이를 허용하지 않으면 R4는 신규 Sub-task로 바뀐다. 부모는 CBRD-26583이다. R4 보고서에 조건부 초안이 있다.
2. **hornetmj가 R3를 병합 조건으로 보는가.** R3 본문에는 병합 전 요구 표현이 없다. 같은 리뷰어의 R6은 "머지 전에 모두 제거해 주시면 좋겠습니다"라고 명시했다. 사용자는 CBRD-27872를 M2 묶음인 CBRD-26583 밑에 발급했다. 병합 전에 처리할지는 리뷰어 답과 M2 일정으로 정한다.

## 이번 작업에서 한 일과 하지 않은 일

분석과 로컬 제안 작성까지 마쳤다. 실제 이슈는 만들지 않았다.

- JIRA 이슈를 생성하거나 수정하지 않았다. CBRD-27213 보강문과 R3 Sub-task 문안은 각 보고서 안의 로컬 제안이다.
- PR7990 리뷰 thread에 답글을 달지 않았다. R3와 R4 thread는 미해결이고 답글이 없다(R3 19:28:15 KST, R4 19:28:45 KST 조회).
- source checkout은 바꾸지 않았다. HEAD는 여전히 `dcbf09e4f`이고 untracked `review.log`도 그대로다.
- 재현과 성능 측정은 하지 않았다. 보고서 안의 수치는 모두 리뷰어 보고다.
- `cubrid-jira search`가 자체 캐시 `~/.local/share/cubrid-jira/issues/`를 갱신했다. R3 agent가 보고한 부수 효과다.

이슈를 실제로 게시하려면 다음 순서가 필요하다. 각 단계는 사용자 승인 뒤에 한다.

1. R3 Sub-task를 발급한다. 2026-11-02 사용자가 [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)로 발급해 끝났다.
2. CBRD-27872 본문을 [R3 분석의 로컬 제안](PR-7990-R3-growth-sweep-cost_dcbf09e_claude.md#신규-sub-task-로컬-제안)을 바탕으로 게시한다. 다시 쓴 본문은 `issues/CBRD-27872-oos-growth-sweep-cost_dcbf09e_claude.md`다.
3. CBRD-27213에 [R4 분석의 보강 제안](PR-7990-R4-restart-bestspace_dcbf09e_claude.md#cbrd-27213-보강-제안)을 반영한다. 다시 쓴 본문은 `issues/CBRD-27213-oos-bestspace-shared-module_dcbf09e_claude.md`다. 완료 조건 4번은 위 [중복 제안 조정](#중복-제안을-조정한다)대로 줄이고 R3 Sub-task를 링크한다.
4. 두 thread에 각 이슈 링크로 답한다. 해결 처리는 하지 않는다.
5. PR7990 설명 또는 QA 노트에 R4의 알려진 제약을 적는다. OOS 명세 §2의 "Recovery rediscovers free space through sync" 격차를 implementation observations에 기록할지는 명세 소유자가 정한다.

## 남은 불확실성

각 보고서의 마지막 표에 해소 방법이 있다. 결론에 영향이 큰 항목만 옮긴다.

| 불확실성 | 영향 | 해소할 증거 |
| --- | --- | --- |
| 오래 열린 쓰기 트랜잭션이 있을 때 할당마다 lap 전체를 반복하는 비용 | 크면 R3가 병합 전 처리로 바뀐다 | 격리 환경에서 한 세션이 쓰기 트랜잭션을 연 채, 다른 세션이 삭제·vacuum 뒤 새 페이지가 필요한 INSERT를 반복한다. 두 파일 크기에서 지연과 lap 횟수를 잰다 |
| 리뷰어가 말한 "bestspace redesign"이 CBRD-27761인지 | 다르면 CBRD-27213의 설계 기준 링크가 바뀐다 | 리뷰어 확인 |
| 리뷰어 측정의 build revision | R4 수치가 다른 코드에서 나왔을 수 있다 | `dcbf09e4f` release 빌드로 리뷰어 시나리오를 재현하고 sync 분기 진입 횟수를 센다 |
| CBRD-27816의 "OOS reclaim tail"이 무엇인지 | 같은 문제를 다른 이름으로 기록했을 수 있다 | CBRD-27785 작업 기록 또는 작성자 확인 |

## 조회 기준

| 항목 | 값 |
| --- | --- |
| source | `/home/vimkim/gh/cb/feature-oos-merge`, `feature/oos-merge`, `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67`. PR7990 head와 같다 |
| OOS 명세 | `/home/vimkim/gh/cubrid-oos-context`, `3462a7f` |
| 일정 저장소 | `ed28fb38aa55130ee920ed4654abf0fef1114582` |
| 로컬 이슈 초안 | `~/gh/my-cubrid-jira`, `52577be` |
| GitHub 조회 | R3 agent 19:28:15 KST, R4 agent 19:28:45 KST |
| live JIRA 조회 | R3 agent 19:30:21~19:31:37 KST, R4 agent 19:29:04~19:41:11 KST |
| coordinator 근거 확인 | 19:43 KST |
