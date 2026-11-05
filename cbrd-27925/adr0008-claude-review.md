# ADR-0008 이후 CBRD-27925 범위: 독립 재검토

2026-11-05, Asia/Seoul. Work818. Work816 보고서 [adr0008-scope.md](adr0008-scope.md)(`417633e`)를 출발점으로 삼아, 그 전제를 소스와 승인된 target에 대어 다시 확인했다. 독자는 CBRD-27925 범위를 정할 사용자와 Work742 구현 담당자다.

## 결론

**Work816의 큰 방향(게이트 원인 추적 제외, 반환·재시도·성장 전 재사용은 유지)에 동의한다. 다만 범위를 한 단계 더 줄일 수 있고, Work816이 빠뜨린 구현 의무가 하나 있다.**

1. **READ 경합 반례는 gate가 없어도 남는다(확인).** 소스 순서와 전수 interleaving 모델 모두 같은 결과다.
2. **그 반례는 native 재현으로 입증할 대상이 아니라 설계로 닫을 대상이다(추가 축소 제안).** 1차 READ 실패를 `DEFERRED`로 세면 모델의 모든 순서에서 힌트 소실이 사라진다. 고치는 비용이 재현 비용보다 훨씬 작다. 남는 것은 그 변경의 비용(경합 때 sweep이 더 자주 무장됨)에 대한 결정이다.
3. **과거 두 VPID(`1|1312`, `1|1313`)는 READ 경합보다 LSA gate 유예로 더 잘 설명된다(새 해석).** 따라서 두 VPID의 원인 확정은 target 범위에서 뺄 수 있다. 다만 return probe가 없어서 확정은 아니다.
4. **ADR-0008 결정 5의 "vacuum fast path는 유지"는 자동으로 유지되지 않는다(Work816 누락).** REMOVE의 chunk 삭제가 sysop commit의 postpone으로 옮겨가면, 지금 vacuum이 빈 페이지 후보 목록을 모으는 경로가 끊긴다. 이를 다시 연결하는 일은 Work742의 구현 의무다.
5. **"추가 쓰기 없는 eventual return"은 gate나 READ 경합과 무관하게 지금 구조로는 충족되지 않는다.** 성장 sweep만이 재방문하므로, 이 요구를 어떻게 해석할지가 핵심 사용자 결정이다.

엔진 소스 수정, 빌드, 서버 실행, DB 재현, JIRA 게시, merge, push는 하지 않았다. 아래의 모델 결과는 실제 DB 관측이 아니다.

## 기준

| 기준 | 값 |
| --- | --- |
| 엔진 소스 | `CBRD-27925-adr0008-claude`, `d52b1889e907abcf84190ec504dde3bc93de260d`(Work816과 같음). `src/storage/oos_file.cpp` SHA-256 `9c746a2e…`. 읽기만 했다. |
| 정규 명세 | `cubrid-oos-context` `3b07ea3`, `OOS-CONTEXT.md` SHA-256 `b91d103c…`. Work816 기준 `281a940`과의 차이는 §1 STORAGE 정책뿐이며 §4 회수 조항은 같다. 명세는 아직 LSA gate를 포함한다. |
| ADR | `cubrid-oos-context-adr-0008` `d5e81a7`, ADR-0008. 파일의 `proposed`와 A'/B3 미정 문구는 11-05 승인보다 오래된 문안이다(Work747). 승인된 target은 A'와 확정 뒤 redo-only 회수다. |
| 과거 실제 DB 관측 | [reclaim-compact-diagnosis.md](../cbrd-26659/reclaim-compact-diagnosis.md)의 a11·a15. 다시 실행하지 않았다. |

## Work816 전제의 검증

| Work816 주장 | 판정 | 근거 |
| --- | --- | --- |
| 1차 READ 실패는 LSA 비교 전에 `SKIPPED`로 끝난다. | **일치** | `oos_try_reclaim_page_internal`(`oos_file.cpp:1583-1591`): fix 실패 시 `result`가 초기값 `SKIPPED`인 채 반환한다. gate 비교는 1594행이다. |
| 정산은 시작 건수를 빼고 유예만 더한다. | **일치** | `oos_reclaim_settle_lap`(1789-1796). 빈 페이지를 하나라도 회수한 lap은 1981행에서 정산 없이 끝난다. |
| INSERT undo는 WRITE latch를 잡은 채 힌트를 올린다. | **일치** | `log_rollback_record`가 WRITE fix(`log_manager.c:7481`) 뒤 CLR을 쓰고 callback을 호출한다(7606-7608). callback `oos_rv_redo_delete`(3650-3673)가 latch 아래에서 `oos_stats_del_bestspace_by_vpid(..., true, ...)`로 힌트를 올린다. 해제는 7695행이다. |
| 일반 삭제 경로는 이 경합을 만들지 않는다. | **일치(보강)** | `oos_delete`는 chain 삭제가 끝난 뒤 latch 밖에서 `oos_reclaim_note_delete`를 부른다(3512-3516). 따라서 latch 아래의 힌트는 rollback·recovery callback 경로뿐이다. |
| 반례는 gate 유무와 무관하다. | **일치** | 아래 모델: gate 유무에서 위반 순서 수가 같다(70개 중 6개). |
| 현재 코드에서 gate만 제거하면 안전하지 않다. | **일치** | `RVOOS_DELETE` undo가 `oos_rv_redo_insert`로 chunk를 다시 넣는다(`recovery.c:887-891`). 생산자는 forward-walk(`vacuum_oos.cpp:184`), REMOVE(`vacuum_oos.cpp:470`), eager(`heap_oos.cpp:1033`) 세 곳이다. |
| `check_gate_scope.py`가 반례를 모델로 보였다. | **약함** | 그 스크립트의 `run_model`은 결과를 직접 지정하고 같은 값을 assert한다. 실행 순서를 탐색하지 않는다. 유효한 근거는 함수 본문 일치와 소스 문자열 검사다. 결론은 맞지만, 근거의 무게는 "소스 판독"이다. |

## 새로 확인한 사항

### F1. Target에서 OOS 페이지로 되돌아 쓰는 undo는 `RVOOS_DELETE` 하나뿐이다

할당 경로도 확인했다. `oos_file_alloc_new`(2984-2998)는 `file_alloc`과 `RVPGBUF_NEW_PAGE`(3155)를 sysop 안에서 기록하고 `log_sysop_commit`으로 끝낸다. `LOG_SYSOP_END_COMMIT`은 영구 변경이라(`log_record.hpp:69,295`) 상위 트랜잭션 rollback이 할당이나 페이지 초기화를 되돌리지 않는다. 따라서 "INSERT 직후 abort한 트랜잭션의 할당 undo가 이미 회수된 페이지를 다시 건드린다"는 반례 후보는 **기각**한다. `RVOOS_INSERT` undo는 CLR(redo-only) 삭제여서 되돌려 쓰는 대상을 만들지 않는다.

그러므로 **세 생산자가 모두 intent + redo-only 삭제로 바뀐 뒤**에는 LSA gate를 없애도 OOS 데이터 페이지의 undo 목적지 문제가 없다. ADR-0008 결정 5의 전제를 소스로 재확인했다. 일부 생산자만 바꾼 중간 상태에서 gate를 제거하면 안 된다.

### F2. INSERT undo로 빈 페이지는 fast path가 없고, bestspace 캐시에서도 빠진다

- Vacuum fast path 후보는 vacuum의 `oos_delete` 호출이 모은다(`vacuum.c:1647,1810,1983`). INSERT rollback은 이 목록에 들어가지 않는다. 이 사실은 target에서도 같다.
- 같은 callback은 `oos_stats_del_bestspace_by_vpid`로 그 페이지의 캐시 항목을 지운다(423-447). 재발견은 bestspace sync에 기대야 하는데, sync는 `num_other_high_best / num_pages`가 임계값 이상일 때만 실행된다(`oos_find_best_page`, 3065-3075).

따라서 Work816이 남긴 "bestspace 재발견이 있으면 sector 증가를 피할 수 있다"는 단서는 맞지만 약하다. INSERT rollback 페이지에 대해서는 재발견이 오히려 보장되지 않는 쪽이다. 또 재발견은 그 페이지를 다시 채우는 것이지 file manager로 반환하는 것이 아니다. 성장은 `file_alloc`이 기존 partial sector의 빈 bit를 쓰면 새 sector 예약 없이 끝난다. "sweep 생략"과 "새 sector 예약"은 여전히 다른 사건이다.

### F3. Fast path 후보 목록은 target에서 다시 연결해야 한다(Work742 의무)

지금 REMOVE 경로는 vacuum sysop 안에서 직접 chunk를 지우며 비게 된 VPID를 `oos_emptied_pages`에 모으고, home page를 놓은 뒤 `vacuum_oos_reclaim_empty_pages`를 부른다(`vacuum.c:1980-1987`). ADR-0008에서는 같은 삭제가 `log_sysop_commit`이 실행하는 postpone의 reclaimer로 옮겨간다. 그 postpone은 recovery 함수 문맥에서 돌기 때문에, vacuum의 지역 벡터에 후보를 넣을 수단이 지금은 없다. UPDATE 알림을 소비하는 vacuum 경로와 eager의 commit 시점 회수도 새 후보 공급원이다. 재시작 중 postpone을 다시 실행하면 후보 목록은 아예 없다(boot rule만 남는다).

ADR 결정 5는 "fast path stays"라고만 적는다. 구현이 후보를 reclaimer에서 회수 호출까지 전달하지 않으면, fast path는 이름만 남고 모든 빈 페이지가 성장 sweep에만 의존한다. Work742의 구현·검증 항목에 이를 명시해야 한다. 반대로 target에서는 reclaimer의 삭제가 이미 확정이므로, eager 경로에도 처음으로 fast path를 붙일 수 있다(지금은 `heap_oos.cpp:946`의 주석대로 금지되어 있다).

### F4. 과거 두 VPID는 gate 유예 쪽 증거가 더 강하다

진단 보고서의 a15 관측은 다음과 같다. 성장 sweep이 두 VPID에 각각 **세 번** 진입했다. rollback CLR 힌트는 `183|8288`이고, 두 페이지의 raw LSA(`182|14640`, `182|14576`)는 horizon `182|14448`보다 크다.

- 힌트가 `183|8288`이라는 것은 두 페이지의 INSERT undo가 그 전에 끝나 latch가 풀렸다는 뜻이다. 따라서 그 sweep 진입 시점에 undo가 READ를 막았을 수 없다.
- 빈 페이지에는 이후 쓰는 주체가 없으므로 진입 시 page LSA는 raw LSA와 같았을 가능성이 높다. 그러면 gate는 `DEFERRED`를 낸다.
- `DEFERRED`는 `pending_deletes`를 유지하므로 다음 성장마다 다시 진입한다. 세 번의 진입과 맞는다. READ 경합이었다면 lap 정산이 힌트를 0으로 만들어 재진입이 줄었을 것이다(다른 삭제가 다시 무장했을 가능성은 남는다).

결론: 두 VPID는 "gate 유예 + 추가 성장 없이 20초 대기"로 설명된다. 다른 9개 페이지와 같은 원인이다. **return probe가 없으므로 확정은 아니다.** 이 해석이 맞다면 target에서는 gate가 사라져 같은 증상은 재방문 한 번에 해소된다. 해석이 틀려도 target 검증 범위는 바뀌지 않는다. 그러므로 원인 확정을 선행 조건으로 둘 이유가 없다는 Work816 판단에 동의하고, 근거를 하나 더한다.

### F5. 추가 쓰기가 없으면 아무것도 재방문하지 않는다

빈 페이지를 찾는 경로는 vacuum fast path(일회성)와 해당 파일의 성장 sweep뿐이다. Fast path를 놓친 페이지에는 READ·WRITE 경합, 오류, OOM, interrupt, INSERT rollback, 재시작 rerun이 있다. 이런 페이지는 **같은 OOS 파일에 다음 page 할당이 올 때까지** 남는다. Gate 제거도 READ 경합 수리도 이 사실을 바꾸지 않는다. 기존 5개 FAIL의 "20초 안에 반환" 판정은 바로 이 구조에 걸려 있다.

명세 §4의 첫 문장("eventually returned")을 성장 없이도 지켜야 하는 요구로 읽으면, 성장과 무관한 재방문 장치(예: vacuum 주기 작업이 무장된 파일의 sweep을 진행)가 필요하다. 둘째 문장("새 sector는 지금 회수할 페이지가 없을 때만")만을 운영 요구로 읽으면, 성장 시점 sweep으로 충분하고 TC의 무성장 20초 판정을 고쳐야 한다. 이는 소스로 정할 수 없는 해석 문제다.

## 독립 모델

[explore_sweep_lap.py](explore_sweep_lap.py)는 INSERT undo(latch → 삭제·힌트 → latch 해제 → 트랜잭션 종료)와 sweep lap(claim → P 검사 → Q 검사 → 정산)의 모든 interleaving 70개를 실행한다. 페이지 Q의 상태(가득 참·회수 가능한 빈 페이지·inserter가 WRITE 보유), 시작 힌트, boot rule을 바꾸며 18조합씩, 두 규칙(현재 `skip`, 후보 `defer`)과 gate 유무를 곱해 36조합을 검사한다. 인자로 CUBRID checkout을 주면 `oos_file.cpp` SHA-256과 네 함수의 구조(READ 실패가 gate보다 앞섬, 정산 순서, callback 안의 힌트, 무장 조건)를 먼저 확인한다.

```sh
python3 -I -B cbrd-27925/explore_sweep_lap.py <d52b188의-CUBRID-checkout>
```

검사 성질: 두 주체가 끝난 뒤 P가 비어 있고 할당된 채라면 다음 성장이 sweep을 무장해야 한다.

| 조건(시작 힌트 0, boot 완료) | 위반 순서 / 70 | P 회수 순서 |
| --- | --- | --- |
| gate 있음, `skip`(현재), Q 가득 참 | 6 (예: `UUSSUUSS`) | 3 |
| gate 없음, `skip`, Q 가득 참 | 6 | 9 |
| gate 있음·없음, `skip`, Q 회수 가능 | 0 (lap이 Q에서 멈춰 정산하지 않음) | 3 / 9 |
| gate 있음·없음, `defer`, 모든 Q | 0 | 3 / 9 |

`UUSSUUSS`는 undo가 latch를 잡고 힌트를 올림 → sweep claim → P READ 실패 → undo 해제·종료 → Q 검사 → 정산(힌트 0)의 순서다. 해석:

- Gate 제거는 latch 해제 뒤·트랜잭션 종료 전 구간의 회수를 늘린다(3→9). 힌트 소실 순서는 줄이지 않는다(6→6).
- 1차 READ 실패를 `DEFERRED`로 세면 36조합 모두에서 위반이 0이다.
- 비용: inserter가 쥔 비어 있지 않은 페이지도 유예로 세므로, 부하 중에는 성장마다 sweep이 다시 무장된다. 이는 CBRD-27872의 할당 시 회수 비용과 충돌한다. 대안은 rollback·recovery callback이 올린 VPID만 별도 재시도 집합에 넣는 방식이다. 이 모델은 대안을 검사하지 않았다.

한계: 페이지 2개, undo 1건, lap 1회의 유한 모델이다. bestspace·file manager·실제 sector 예약·다중 sweep 호출자·재시작은 모델에 없다. 실행은 exit 0이다.

## 남길 범위

| 항목 | Work816 | 이번 판정 |
| --- | --- | --- |
| LSA horizon 공급자·append clamp 추적 | 필수 조사에서 제외 | **동의.** 과거 근거로 보존. |
| 과거 두 VPID 원인 확정 | 선행 조건 아님 | **동의, 근거 추가(F4).** gate 유예로 더 잘 설명된다. 확정은 아니다. |
| READ 경합 힌트 소실 | 유지, 구현 후 검증 | **설계로 닫기를 제안.** 실제 DB 재현은 필요 없다. 선택한 수정은 단위·모델 수준에서 확인한다. |
| WRITE 실패 `DEFERRED` 대조군 | 유지 | 동의. |
| `pending_deletes`·boot rule·cursor | 유지 | 동의. 수정 방식이 정산 규칙을 바꾸므로 함께 검증한다. |
| Fast path 후보 공급 | 언급 없음 | **추가(F3).** REMOVE postpone·UPDATE 알림 소비·eager commit에서 후보를 회수 호출까지 전달한다. 재시작 rerun은 boot rule에 맡긴다는 점을 명시한다. |
| 세 `RVOOS_DELETE` 생산자의 전환 완료 | undo 목적지 표에 포함 | **gate 제거의 전제 조건으로 격상(F1).** 셋이 모두 바뀌기 전에는 gate를 지우지 않는다. |
| Intent·chunk 재시도 수렴 | Work742 | 동의. 페이지 반환과 대체 관계가 아니다(intent는 남은 chunk, sweep은 이미 빈 페이지를 다룬다). |
| 추가 쓰기 없는 eventual return | 유지 | **사용자 해석 결정 대기(F5).** |
| 성장 전 재사용·sector 예약 | 구현 후 검증 | 동의. 부분 재사용, 반환, 새 sector를 따로 관측한다. CBRD-27945는 별도다. |

## 남는 최소 검증

Work790의 별도 팀장 승인 전에는 아래 중 서버·DB를 쓰는 항목을 시작하지 않는다.

1. **승인 전에 가능(순수 모델·소형 추출):** 선택한 READ 경합 수정의 interleaving 검사(이 모델 확장), fast path 후보 전달의 단위 시험, 세 생산자 전환 여부의 소스 검사.
2. **Work742 구현 후, 승인 뒤 native:**
   - 원래 5개 FAIL을 새 기준에서 다시 실행하고, 결과를 과거 결과와 나란히 기록한다. 과거 enum을 소급해 채우지 않는다.
   - REMOVE·UPDATE·eager 각각에서 빈 페이지가 fast path로 반환되는지 확인한다(F3 회귀).
   - INSERT abort 직후 같은 파일에 성장을 한 번 일으켜 반환되는지 확인한다(F2·F5의 성장 경로).
   - F5 해석에 따라, 추가 쓰기 없는 대기에서 반환되는지 확인하거나 TC 판정을 고친다.
   - 성장 압력 시험에서 sector 예약 수를 관측한다.

READ 경합 순서를 실제 SQL로 맞추는 재현은 이 목록에서 뺐다. latch 구간이 callback 한 번이라 재현이 어렵고, 수정 여부가 그 재현 결과에 달려 있지 않기 때문이다.

## 사용자 결정

1. **"Eventually returned"를 성장 없이도 요구하는가?** 예라면 성장과 무관한 재방문 장치를 Work742 또는 CBRD-27925의 구현 범위에 넣는다. 아니라면 명세 §4 문구와 5개 TC의 무성장 대기 판정을 고치는 작업(Work747·TC)이 생긴다.
2. **READ 경합을 재현으로 입증할 것인가, 설계로 닫을 것인가?** 이 보고서는 설계로 닫기를 권한다. 닫는다면 방식도 정한다: (a) 1차 READ 실패를 `DEFERRED`로 센다(단순, 부하 시 sweep 증가) 또는 (b) callback이 올린 VPID만 재시도 집합에 둔다(정확, 상태 추가).
3. **과거 두 VPID 원인 확정을 범위에서 공식 제외할 것인가?** F4의 해석을 받아들이면 제외한다. 기존 관측 기록과 "미확정" 표시는 그대로 둔다.
4. **Fast path 재연결(F3)을 Work742 범위에 넣을 것인가, CBRD-27925 후속으로 둘 것인가?** Work742에 넣기를 권한다. 회수 경로를 바꾸는 바로 그 변경이 후보 공급을 끊기 때문이다.

## Work816과 비교

- **일치:** gate 원인 추적 제외, READ 경합이 gate와 무관하다는 판단, 현재 코드에서 gate만 지우면 안 된다는 판단, intent 재시도와 페이지 반환이 서로 대체하지 않는다는 판단, 과거 두 VPID를 선행 조건에서 제외하는 판단.
- **반박·보강:** `check_gate_scope.py`는 탐색 모델이 아니다. bestspace 재발견은 INSERT rollback 페이지에서 오히려 약하다(F2). fast path 유지가 구현 의무라는 점이 빠졌다(F3). 과거 두 VPID는 READ 경합보다 gate 유예 쪽 근거가 강하다(F4). READ 경합은 재현이 아니라 설계로 닫을 수 있다.
- **아직 확인할 수 없음:** 과거 두 VPID의 최종 enum, READ 경합의 실제 SQL 도달 빈도, 새 sector 예약까지의 연결, target 구현의 실제 후보 공급 방식.
