# OOS 파일 성장 상한: 대안 설계와 TLA+ 검증

2026-11-05, Asia/Seoul. Work821. [CBRD-27925](https://jira.cubrid.org/browse/CBRD-27925) 후속이며 [CBRD-27872](https://jira.cubrid.org/browse/CBRD-27872)(할당 시 회수 검사 비용)와 [CBRD-26659](https://jira.cubrid.org/browse/CBRD-26659)(회수 TC)에 걸친다.

독자는 OOS 회수 규칙을 정할 사용자와, ADR-0008을 구현하는 Work742 담당자다.

## 질문과 결론

빈 OOS 페이지 회수 규칙의 목적은 OOS 파일이 한없이 커지지 않게 하는 것이다. 현재 명세는 더 강하다. 회수 가능한 빈 페이지가 하나라도 있으면 새 sector를 예약하지 못한다(OOS-CONTEXT §4, ADR-0009 결정 2). 사용자는 이 강한 규칙이 INSERT·UPDATE 성능을 잡아먹을까 염려했다.

**결론: 비용의 원인은 규칙의 강도가 아니라 무장 신호다.** 현재 엔진은 chain 삭제가 성공할 때마다 sweep을 무장한다. 그 삭제가 페이지를 비웠는지는 보지 않는다. 무장되면 다음 할당이 파일 전체를 READ fix하는 lap을 돈다. 빈 페이지가 된 VPID만 모으는 **후보 집합**으로 바꾸면 강한 규칙을 그대로 지키면서 할당당 비용이 상각 O(1)이 된다. TLA+ 모델은 이 설계만이 성장 중 동시 쓰기가 있어도 파일 크기를 유계로 지킨다는 것을 보였다. 비교한 다른 설계는 모두 그런 조건에서 상한에 닿았다.

1. **권고: 강한 규칙은 유지하고 무장 방식을 바꾼다(`cand`).** ADR-0009 결정 1~3은 그대로 둔다. 무장 방식 변경은 새 ADR-0010으로 제안한다.
2. **약화안(N 페이지 예산 sweep)은 기각한다.** 모델에서 예산 sweep은 N=1과 N=2 모두 성장이 상한에 닿았다. undo latch 하나와 살아 있는 chunk가 sweep 창을 매번 막는 배치가 있다.
3. **READ 경합 수정은 (b)를 일반화한다.** rollback callback이 비운 VPID만이 아니라, 빈 페이지가 된 모든 VPID를 1의 후보 집합에 넣는다. 후보 집합을 채택하지 않는다면 (b)가 (a)보다 낫다. 두 방식의 모델 판정은 같고, (b)는 부하 중에 lap을 더 무장하지 않는다.
4. **TC 판정은 첫 cycle 정확 상한에서 여유분 있는 유계 판정으로 바꾼다.** a01 재실행은 명세가 허용하는 범위에서도 1 page 차이가 생길 수 있음을 보였다(아래 TC 절).

엔진 소스 수정, 빌드, DB·서버 실행, JIRA 게시, push는 하지 않았다. 모델 결과는 작은 유한 모델에 대한 것이다. 실제 엔진의 성능 수치는 측정하지 않았다.

## 기준

| 기준 | 값 |
| --- | --- |
| 엔진 소스 | `/home/vimkim/gh/cb/CBRD-27925-adr0008-claude`, `feature/oos-merge` `d52b1889e907abcf84190ec504dde3bc93de260d`, clean. `src/storage/oos_file.cpp` SHA-256 `9c746a2e313cc3e4…`(Work818과 같음). 읽기만 했다. |
| 정규 명세 | `cubrid-oos-context` main `07f1911`, `OOS-CONTEXT.md` SHA-256 `679b77c7…`. ADR-0009가 병합된 상태다. |
| ADR | ADR-0008(승인, A'와 확정 뒤 redo-only 회수, LSA gate 제거). ADR-0009(승인, 쓰기 없는 동안의 반환 불요). |
| 이전 조사 | [adr0008-claude-review.md](adr0008-claude-review.md)(Work818), [explore_sweep_lap.py](explore_sweep_lap.py) |
| TC 실행 결과 | Work820 a01, `/home/vimkim/temp/w820b-Ruydhzdl/a01`. 엔진 `e3589ae42`, TC `tc/pr-8128` `3ec4e014d`. 이 세션은 그 결과를 읽기만 했다. |
| 모델 | [growth-model/OosGrowthBound.tla](growth-model/OosGrowthBound.tla), [growth-model/run.py](growth-model/run.py). TLC 2.19(`tla2tools-1.7.4.jar`), OpenJDK 1.8.0_462. |

## 현재 엔진의 비용 구조

출처는 모두 `d52b1889e` 의 `src/storage/oos_file.cpp` 다.

- **무장 신호.** `oos_delete`(3505-3520)는 chain 삭제가 `OOS_DELETE_RECLAIMED` 로 끝나면 `oos_reclaim_note_delete` 를 부른다. 이 함수가 파일의 `pending_deletes` 를 올린다(1337-1357). 페이지가 비었는지는 보지 않는다. 같은 함수 안의 `oos_delete_chain` 은 페이지가 비었는지를 이미 안다(3375). 그러나 그 정보는 vacuum fast path 목록에만 쓰인다.
- **Fast path가 무장을 풀지 않는다.** Vacuum fast path는 비워진 페이지를 바로 반환한다. 하지만 `pending_deletes` 는 줄이지 않는다. 그래서 fast path가 일을 다 끝낸 뒤에도 다음 성장은 아무것도 찾지 못할 lap을 돈다.
- **무장된 성장 한 번의 일.** `oos_reclaim_sweep_step`(1816-2000)은 다음을 순서대로 한다.
  1. 파일당 single-flight를 잡는다. 동시에 성장하려는 다른 INSERT는 `pthread_cond_wait` 로 기다린다(1850-1866).
  2. `file_get_all_data_sectors` 로 sector 표 전체를 모아 정렬한다(1915-1935).
  3. `oos_reclaim_sample_horizon` 으로 활성 트랜잭션과 system tdes를 모두 훑는다(1938). ADR-0008 이후에는 이 단계가 사라진다.
  4. cursor부터 할당된 페이지마다 조건부 READ fix와 빈 페이지 검사를 한다(1941-1990). 버퍼에 없는 페이지는 디스크에서 읽는다.
  5. 빈 페이지 하나를 회수하면 멈춘다. 회수 없이 한 바퀴를 돌면 정산한다(1789-1796).
- **결과.** UPDATE·DELETE가 섞인 workload에서는 vacuum이 chain을 지울 때마다 무장이 다시 켜진다. 그러면 그다음 성장은 파일 전체를 읽고, 그동안 같은 테이블의 다른 INSERT는 기다린다. 비용은 파일 크기에 비례하고, 삭제가 잦을수록 자주 낸다. 이 판단은 소스 판독에 근거한 것이며 측정하지 않았다.

INSERT rollback은 `oos_rv_redo_delete`(3650-3673)에서 페이지 WRITE latch를 쥔 채 힌트를 올린다. sweep이 그 페이지를 READ로 잡지 못하면 `SKIPPED` 가 되고, lap 정산이 힌트를 0으로 만든다. 이것이 Work818의 READ 경합 힌트 소실이다.

## 설계 후보

| 이름 | 설명 | 출처 |
| --- | --- | --- |
| `none` | 성장 쪽 회수가 없다. 끝내 스케줄되지 않는 백그라운드 sweep과 같다. | 기준선 |
| `full_skip` | 현재 엔진이다. 모든 chunk 삭제가 무장하고, lap이 파일 전체를 돌며, 첫 회수에서 멈춘다. latch 경합 페이지는 `SKIPPED` 다. | `d52b1889e` |
| `full_defer` | (a) 1차 READ 실패를 `DEFERRED` 로 센다. | Work818 결정 2(a) |
| `full_retry` | (b) rollback callback이 비운 VPID를 재시도 집합에 넣는다. 모든 성장이 그 집합을 먼저 확인한다. 나머지는 현재 엔진과 같다. | Work818 결정 2(b) |
| `budget_N1`, `budget_N2` | `full_defer` 에 할당당 검사 페이지 수 N 제한을 더한다. lap은 다음 성장에서 이어진다. 약화안이다. | 인계 문서 방향 2 |
| `cand_fullboot` | **권고안.** 빈 페이지가 된 VPID만 파일별 집합에 넣는다. 성장은 그 집합만 확인한다. 재시작이나 OOM으로 집합을 잃으면 파일 전체 lap을 한 번 돈다(현재 boot rule과 같다). | 인계 문서 방향 4 |
| `cand_budgetboot_N2` | `cand` 에서 손실 뒤 lap을 할당당 N 페이지로 나눈다. | 방향 2와 4의 결합 |

인계 문서 방향 1(비율·여유량 상한)은 따로 모델링하지 않았다. 빈 페이지 수를 알아야 상한을 넘었는지 판정할 수 있다. 그 수를 정확히 세는 장치가 곧 후보 집합이므로 `cand` 에 포함된다. 방향 3(할당 경로 밖의 sweep)은 `none` 과 같다. 백그라운드 작업은 스케줄을 보장하지 않으며, 스케줄되지 않으면 아무것도 막지 못한다.

## TLA+ 모델

[OosGrowthBound.tla](growth-model/OosGrowthBound.tla)는 OOS 파일 하나를 모델링한다.

- **페이지.** 각 페이지는 FREE(예약된 sector 안의 미할당 페이지)이거나 0..Cap개의 chunk를 가진다. 한 페이지를 한 sector로 둔다. 따라서 예약 페이지 수 `R` 이 디스크상 파일 크기다. 영구 파일의 sector는 `file_destroy` 에서만 반환되므로 `R` 은 줄지 않는다.
- **행위자.**
  - 기존 페이지에 넣는 INSERT. bestspace가 맞은 경우다.
  - 성장하는 INSERT. 언제든 힌트를 잃었다고 보고 성장할 수 있다.
  - Vacuum chunk 삭제와 fast path.
  - INSERT rollback undo. latch를 쥔 채 chunk를 지우고 기록한다.
  - 재시작. 메모리 힌트를 모두 잃는다.
- **성장하는 INSERT.** 파일당 single-flight가 성장을 직렬화하므로 grower는 하나다. 회수 단계는 페이지 하나씩 원자 단계로 나눠 다른 행위자와 interleave한다.
- **모델의 제한 두 가지.**
  - undo는 성장 한 번 동안 새 latch를 최대 한 번 잡는다. 이 제한이 없으면 zero-wait 검사를 쓰는 어떤 설계도 상한을 지키지 못한다. scheduler가 grower가 닿기 직전마다 latch를 그 페이지로 옮길 수 있기 때문이다. 첫 실행에서 모든 설계가 상한에 닿아 이 제한을 넣었다.
  - `WritesDuringGrow` 가 FALSE면 INSERT와 삭제는 성장이 끝날 때까지 기다린다. undo의 latch 해제는 여전히 성장 도중에 일어날 수 있다. TRUE면 모든 쓰기가 성장 단계 사이에 끼어든다.

성질은 다음과 같다.

| 성질 | 의미 |
| --- | --- |
| `TypeOK`, `FreeHoldsNothing` | 안전성. 예약 범위 밖 페이지는 FREE이고, latch가 걸린 페이지는 할당된 상태다. 회수 동작은 모두 "비어 있고 latch가 없음"을 조건으로 한다. |
| `NoGrowthPastStaleEmpty` | 현재 명세. 성장 시작 때 비어 있었고 그 뒤 아무도 쓰거나 latch를 잡지 않은 페이지가 남아 있으면 새 페이지를 예약하지 않는다. |
| `NoOverflow`, `SizeWithinBound` | 유계 성장. 가장 작은 통과 `Bound` 가 최악의 파일 크기다. 파일이 MaxPages에 닿으면 `cap` 으로 표시한다. |
| `CostWithinBound` | 성장 한 번이 검사하는 페이지 수의 최댓값이다. |
| `NoFutileWork` | 성장 동안 빈 페이지가 한 번도 없었다면 검사한 페이지도 없다. 무장 신호가 정확한지를 본다. |

모델은 엔진 코드와 대응하는지 자동으로 확인하지 않는다. 대응은 위 비용 구조 절의 소스 판독에 기댄다.

### 실행

```sh
python3 -I -B cbrd-27925/growth-model/run.py --out <새 디렉터리> --jobs 18
```

설정은 Cap=2, L=2(파일 안 chunk 최대 2개), MaxPages 5와 6이다. 크래시 유무와 성장 중 쓰기 유무를 곱했다. safety, 비용, `NoFutileWork` 는 MaxPages 5에서만 본다. 비용과 `NoFutileWork` 는 성장 중 쓰기가 없을 때만 본다. MaxPages 6은 유계인 설계의 최악 크기가 같은지 확인하는 데 쓴다. runner는 결과를 `EXPECTED` 표와 비교하고, 하나라도 다르면 exit 1로 끝난다. 80코어 서버에서 약 15분 걸렸다.

### 결과

전체 표는 아래 "재현 기록"에 있다. 요약은 다음과 같다. "조용"은 성장 중 쓰기가 없는 설정이고, "쓰기"는 있는 설정이다.

| 설계 | 현재 명세 | 최악 크기 (조용) | 최악 크기 (쓰기) | 크래시 포함 시 | 성장당 최대 검사 (조용) | 헛된 검사 없음 |
| --- | --- | --- | --- | --- | --- | --- |
| `none` | FAIL | cap | cap | cap | 0 | PASS |
| `full_skip`(현재 엔진) | **FAIL** | 3 | cap | 같음 | 3(파일 전체) | FAIL |
| `full_defer`(a) | PASS | 3 | cap | 같음 | 3(파일 전체) | FAIL |
| `full_retry`(b) | PASS | 3 | cap | 같음 | 5 | FAIL |
| `budget_N1` | FAIL | cap | cap | cap | 1 | FAIL |
| `budget_N2` | FAIL | cap | cap | cap | 2 | FAIL |
| `cand_fullboot` | **PASS** | **3** | **4** | 조용 3, 쓰기 cap | 3, 크래시 시 5 | **PASS**(크래시 없을 때) |
| `cand_budgetboot_N2` | 크래시 없을 때만 PASS | 3 | 4 | cap | 3, 크래시 시 5 | 크래시 없을 때만 PASS |

safety 성질은 모든 설정에서 통과했다.

해석은 다음과 같다.

- **현재 엔진은 Work818 반례를 그대로 낸다.** TLC가 찾은 `full_skip` 의 최단 반례는 11단계다. undo가 latch를 쥔 채 페이지를 비운다. sweep은 그 페이지를 건너뛴다. undo가 latch를 푼다. lap 정산이 무장을 끈다. 다음 성장은 그 빈 페이지를 둔 채 새 페이지를 잡는다. 이 반례가 성장을 무한으로 만들지는 않는다. 다음 chunk 삭제가 다시 무장하기 때문이다(조용한 설정의 최악 크기 3).
- **cursor로 훑는 설계는 동시 쓰기에 회피당한다.** `full_*` 와 `budget_*` 은 성장 중 쓰기를 허용하면 모두 cap에 닿았다. 상한을 8과 10으로 올려도 마찬가지였다(`full_skip`, `full_defer` MaxPages 8, `budget_N2` 조용 MaxPages 8·10). 반례 순서는 이렇다. cursor가 닿기 직전에 페이지를 다시 채우고, 지나간 뒤에 비운다. 실제 bestspace가 이런 배치를 고르지는 않는다. 그래도 lap의 보장은 쓰기의 배치에 기댄다는 뜻이다.
- **예산 sweep은 조용한 설정에서도 상한이 없다.** undo latch 하나가 성장마다 N 페이지 창 바로 앞 페이지로 옮겨 가고, 살아 있는 chunk가 창의 나머지를 채운다. 그러면 창은 매번 회수할 것을 찾지 못한다. 처음에는 N=2이면 약 2L에서 멈출 것으로 계산했다. 그 계산은 이 배치를 빠뜨려 틀렸다. 실제 파일은 L이 훨씬 커서 이 배치가 우연히 생기기는 어렵다. 그러나 확률적 기대일 뿐 보장은 아니다.
- **후보 집합은 회피당하지 않는다.** `cand` 는 빈 페이지가 생기는 순간 그 VPID를 집합에 넣고, 성장은 위치와 무관하게 집합을 확인한다. 성장 중 쓰기가 있어도 최악 크기는 4이고, MaxPages 8과 10에서도 4로 닫혔다(상태 12,286개). 3에서 4로 늘어난 한 페이지는 성장 도중 비워진 페이지다. 그 페이지는 다음 성장에서 회수되며 명세도 허용한다.
- **크래시와 동시 쓰기가 함께 있으면 어느 설계도 상한을 지키지 못한다.** `cand_fullboot` 도 이 조합에서는 cap에 닿는다. 모든 성장 사이에 재시작이 있고, 재시작 뒤 lap이 동시 쓰기에 회피당하는 순서다. 현실에서 나올 순서는 아니다. 이 모델로는 그 이상을 말할 수 없다.
- **비용.** 이 작은 모델에서는 파일이 3페이지에 머물러 최대 검사 수의 차이가 작다. 차이는 `NoFutileWork` 가 보인다. 성장 동안 빈 페이지가 하나도 없었는데도 `full_*` 와 `budget_*` 은 검사를 했다. 크래시가 없을 때 `cand` 는 하지 않았다. 실제 파일에서 `full_*` 의 헛된 검사는 파일 전체 READ fix다. `cand` 의 검사는 빈 페이지가 된 사건 하나당 한 번이다. 다만 latch에 걸린 후보는 다시 검사하며, 그 수는 동시에 latch를 쥔 rollback 수를 넘지 않는다.

`full_retry` 의 최대 검사가 5인 이유는 재시도 집합과 전체 lap을 함께 돌 수 있기 때문이다. (b)는 현재 무장 방식을 유지하므로 비용 문제는 그대로 남는다.

### 한계

- 페이지 5~10개, chunk 2개, 페이지당 chunk 2개, rollback 하나인 유한 모델이다. 상한 값 자체(3, 4)는 실제 파일의 상한이 아니다. 판정이 갈리는 지점(유계인지, 현재 명세를 지키는지, 헛된 검사를 하는지)만 의미가 있다.
- 다중 grower는 single-flight 직렬화를 근거로 하나로 줄였다. sector와 페이지를 1:1로 두어, 같은 sector 안 free bit를 먼저 쓰는 `file_alloc` 동작은 "FREE 페이지 우선"으로만 반영했다.
- 후보 집합 모델은 INSERT가 다시 채운 페이지를 집합에서 바로 뺀다. 상태 공간을 줄이려는 단순화다. 구현이 나중에 빼도 판정은 같고 검사가 한 번 늘 뿐이다.
- LSA gate는 모델에 없다. ADR-0008 이후의 target을 모델링했다.
- 성능 수치는 없다. CBRD-27872의 측정이 필요하다.

## 권고 설계: 빈 페이지 후보 집합

ADR-0008 구현과 함께 넣는 것을 권한다. 데이터 형태는 다음과 같다.

```text
oos_reclaim_file_state (VFID별, bestspace_mutex 아래)
  emptied   : VPID 집합, 상한 K개 (예: 4096)
  unknown   : bool   집합이 불완전할 수 있다 (boot, OOM, K 초과)
  sweep_in_progress, sweep_cursor : 손실 뒤 lap에만 쓴다
  (pending_deletes, swept_this_boot 는 삭제한다)
```

- **넣기.** 페이지를 비운 바로 그 지점에서 넣는다.
  - `oos_delete_chain` 의 3375행. 이미 같은 조건으로 fast path 목록을 만든다.
  - `oos_rv_redo_delete` 의 3655행 뒤. `spage_number_of_records == 0` 일 때다.
  - ADR-0008의 redo-only reclaimer는 이 두 삭제 primitive 중 하나를 거치게 한다.
  - 할당 뒤 첫 레코드를 넣기 전에 실패해 페이지가 빈 채 남는 경로가 있는지 구현 때 확인한다. 있다면 그 경로도 넣는다.
- **빼기.** fast path나 성장이 그 페이지를 회수했을 때 뺀다. INSERT가 빈 페이지를 다시 썼을 때(`page_was_empty`, 2158)도 빼도 되고, 성장 때 검사하며 버려도 된다.
- **성장.** 집합의 원소마다 기존 `oos_try_reclaim_page_internal` 을 쓴다. 결과에 따라 이렇게 처리한다.
  - `RECLAIMED` 면 멈추고 할당한다.
  - latch 경합이나 `DEFERRED` 면 집합에 남긴다.
  - 비어 있지 않거나 이미 해제된 페이지면 집합에서 뺀다.
  - 그다음 `unknown` 이면 기존 sweep을 한 바퀴 돌린다. 그 lap이 latch 경합을 만난 페이지는 집합에 넣고, lap이 끝나면 `unknown` 을 끈다.
- **효과.**
  - 무장된 성장마다 하던 sector 표 수집, 정렬, 파일 전체 READ fix가 사라진다. 남는 전체 lap은 파일마다 재시작 뒤 첫 성장과 집합 overflow 뒤에 한 번씩이다.
  - READ 경합 힌트 소실(Work818)이 구조적으로 닫힌다. latch에 걸린 후보는 지워지지 않는다.
  - F3(fast path 후보 공급 재연결)은 정확성 의무에서 최적화로 내려간다. fast path가 없어도 다음 성장이 집합에서 빈 페이지를 찾는다.
- **구현 크기.** 집합 필드, 두 삽입 지점, 회수 지점의 제거, sweep 앞의 집합 단계, 카운터 삭제다. 추정 100~150줄이며 대부분 `oos_file.cpp` 안이다. 소스를 고쳐 보지는 않았다.

## 비교표

| 안 | 보장 | 할당당 비용 | 정확성 위험 | 구현 크기 |
| --- | --- | --- | --- | --- |
| 현재(`full_skip`) | 현재 명세 위반(READ 경합). 조용할 때만 유계 | 무장 시 파일 전체 READ fix, sector 표 수집·정렬, 동시 grower 대기. 무장은 모든 chain 삭제 | 힌트 소실, 동시 쓰기에 회피당함 | 0 |
| (a) `full_defer` | 현재 명세. 조용할 때만 유계 | 현재와 같고, 부하 중에는 더 자주 무장 | 동시 쓰기에 회피당함 | 수 줄 |
| (b) `full_retry` | 현재 명세. 조용할 때만 유계 | 현재와 같고, 재시도 집합 검사가 더해짐 | 동시 쓰기에 회피당함 | 수십 줄 |
| 예산 sweep `budget_N` | 현재 명세 위반. 상한 없음(모델) | 할당당 N 페이지와 sector 표 수집(캐시하지 않으면) | 배치에 따라 무한 성장 | 수십 줄 |
| **후보 집합 `cand_fullboot`** | **현재 명세. 동시 쓰기에도 유계** | **상각 O(1). 재시작·overflow 뒤 파일당 lap 한 번** | 빈 페이지를 만드는 모든 지점에서 넣어야 함 | 100~150줄(추정) |
| `cand_budgetboot` | 재시작 뒤 lap 동안 현재 명세 위반, 크래시 시 상한 없음 | 상각 O(1) + 재시작 뒤 N 페이지 | 반복 재시작 시 성장 | `cand` + 수십 줄 |

## TC 판정

### a01 재실행에서 확인한 것

`cbrd_26659_snapshots_reclaim` 재실행 결과(Work820 a01, 엔진 `e3589ae42`, TC `3ec4e014d`)다.

- 세 cycle의 피크는 25, 26, 26 pages다. 첫 cycle 상한 25를 넘어 `churn_plateau1` 과 `churn_plateau2` 가 FAIL이었다. 직전 실행은 25, 23, 25로 PASS였다.
- 세 피크 모두 `Oos_num_recs` 는 25, `Oos_recs_sumlen` 은 268,876이다(`oos11.churn_positive{0,1,2}.stdout.log`). 레코드 하나는 평균 약 10.7KB라서 페이지에 하나씩 들어간다. 따라서 cycle 1과 2의 피크에는 레코드가 없는 페이지가 적어도 하나 할당돼 있었다.
- cycle 0과 1의 drain 뒤 페이지 수는 각각 25, 26이었다(`churn_idle_pages0/1`). cycle 1이 시작될 때 빈 페이지는 24개였다.

해석은 이렇다. 성장 시점에 빈 페이지 하나를 회수하지 못하고 새 페이지를 잡았다. 그 엔진에는 LSA gate가 있으므로 gate 유예(명세가 허용)와 sweep 누락(명세 위반) 중 어느 쪽인지는 return probe 없이 가릴 수 없다. 원인을 확정하지는 못한다. 다만 결론은 같다. 명세가 허용하는 유예만으로도 첫 cycle 정확 상한은 1 page 단위로 깨질 수 있다. 그런 판정은 비결정적이다.

### 변경안

[tc-bounded-oracle.patch](tc-bounded-oracle.patch)는 `tc/pr-8128` `3ec4e014d` 기준이다.

- `snapshot_controller.sh` `sn_churn` 과 `oos_churn.sh` `ch_reuse` 에서 상한을 `첫 cycle 피크 + max(2, ⌈피크/10⌉)` 로 바꾼다. 피크 25면 여유분은 3, 97이면 10이다.
- 모든 cycle을 첫 cycle과 비교하므로 누적 성장은 여전히 잡힌다. cycle당 1 page씩 누적되면 여유분이 3일 때 네 번째 cycle에서 FAIL이다. 현재 3 cycle로는 cycle당 1 page 누적을 잡지 못한다. cycle을 5회 이상으로 늘리기를 권한다. 이 patch는 cycle 수를 바꾸지 않았다.
- 정확 상한을 지켰는지는 `exact_plateau_kept`, `exact_ceiling_kept` 관측값으로 남긴다.
- `reuse_before_sector_growth`(최종 sector ≤ 첫 피크 sector)는 그대로 둔다. sector는 64페이지 단위라 1~2 page 차이에 흔들리지 않는다.
- 검증은 `bash -n` 문법 검사와 여유분 함수의 산술만 했다(9→2, 25→3, 97→10, 130→13). DB를 실행하지 않았다. a01 수치에서는 상한이 28이므로 26은 PASS다.

## 명세·ADR·JIRA에 필요한 변경

- **ADR-0009.** 결정 1~3은 바뀌지 않는다. 결정 4의 TC 문구 "the peak page count of a repeated workload does not grow"에 여유분을 둔다. 후속 commit 초안은 `cubrid-oos-context` 브랜치 `docs/adr-0010-emptied-page-candidates` 의 `899acd1` 이다(worktree `/home/vimkim/gh/cubrid-oos-context-adr-0010`, push 안 함).
- **ADR-0010(신규, proposed).** 성장 쪽 회수를 chunk 삭제 카운터가 아니라 빈 페이지 후보 집합으로 무장한다. §4의 "Growth-gate sweep" 문단과 용어 "Pending-delete counter"를 바꾼다. 같은 브랜치의 `d96c773` 이며, 상태는 proposed다.
- **JIRA.** 이미 게시한 CBRD-27925 본문, 댓글 4777975, CBRD-26659 댓글 4777976의 핵심("새 sector 전 회수·재사용")은 그대로 맞다. 보충 댓글 두 개의 초안을 [jira-growth-bound-drafts.md](jira-growth-bound-drafts.md)에 두었다. 게시는 승인 뒤에 한다.

## 사용자 결정

1. **보장 수준.** 권고는 강한 규칙 유지와 후보 집합(ADR-0010)이다. 약화를 원하면 무엇으로 약화할지를 다시 정해야 한다. 모델에서 예산 sweep은 상한을 지키지 못했다.
2. **구현 위치.** 권고는 Work742(ADR-0008 구현)에 넣는 것이다. 같은 삭제 primitive와 fast path 공급 경로를 건드리기 때문이다. CBRD-27872는 전후 비용 측정을 맡는다.
3. **TC 여유분.** 권고는 `max(2, ⌈10%⌉)` 와 cycle 5회다.
4. **ADR-0009 후속 commit과 ADR-0010 push, JIRA 보충 댓글 게시 승인.**

## 재현 기록

- 모델 `growth-model/OosGrowthBound.tla` SHA-256 `184e4c718d6449b4a5c696c7fcb000fa0376ee8418dd99fc20c2e87ce75eeb54`. runner가 출력하는 값과 같다.
- 명령: `python3 -I -B cbrd-27925/growth-model/run.py --out <새 디렉터리> --jobs 18`. 같은 디렉터리에 `--resume` 을 주면 끝난 TLC 로그의 판정을 다시 쓴다.
- 결과: exit 0, "all results match EXPECTED". 2026-11-05 run5와 run5 `--resume`(상한 확인)의 출력이다. 원시 TLC 로그는 저장소에 두지 않는다.
- 과정: 첫 매트릭스는 undo latch 횟수 제한이 없어서 모든 설계가 cap에 닿았다. 이 결과는 버렸다. 이후 성장 중 쓰기 축을 더하고, `NoFutileWork` 를 "성장 동안 빈 페이지가 없었던 경우"로 좁혔다. 처음 정의는 성장 도중 undo가 비운 페이지 검사까지 헛된 일로 세었다.

| design | crashes | writes in grow | MaxPages | safety | strong | max R | max cost/grow | no futile work |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| none | False | False | 5 | PASS | FAIL | cap | 0 | PASS |
| none | False | False | 6 | - | FAIL | cap | - | - |
| none | False | True | 5 | PASS | FAIL | cap | - | - |
| none | False | True | 6 | - | FAIL | cap | - | - |
| none | True | False | 5 | PASS | FAIL | cap | 0 | PASS |
| none | True | False | 6 | - | FAIL | cap | - | - |
| none | True | True | 5 | PASS | FAIL | cap | - | - |
| none | True | True | 6 | - | FAIL | cap | - | - |
| full_skip | False | False | 5 | PASS | FAIL | 3 | 3 | FAIL |
| full_skip | False | False | 6 | - | FAIL | 3 | - | - |
| full_skip | False | True | 5 | PASS | FAIL | cap | - | - |
| full_skip | False | True | 6 | - | FAIL | cap | - | - |
| full_skip | True | False | 5 | PASS | FAIL | 3 | 3 | FAIL |
| full_skip | True | False | 6 | - | FAIL | 3 | - | - |
| full_skip | True | True | 5 | PASS | FAIL | cap | - | - |
| full_skip | True | True | 6 | - | FAIL | cap | - | - |
| full_defer | False | False | 5 | PASS | PASS | 3 | 3 | FAIL |
| full_defer | False | False | 6 | - | PASS | 3 | - | - |
| full_defer | False | True | 5 | PASS | PASS | cap | - | - |
| full_defer | False | True | 6 | - | PASS | cap | - | - |
| full_defer | True | False | 5 | PASS | PASS | 3 | 3 | FAIL |
| full_defer | True | False | 6 | - | PASS | 3 | - | - |
| full_defer | True | True | 5 | PASS | PASS | cap | - | - |
| full_defer | True | True | 6 | - | PASS | cap | - | - |
| full_retry | False | False | 5 | PASS | PASS | 3 | 5 | FAIL |
| full_retry | False | False | 6 | - | PASS | 3 | - | - |
| full_retry | False | True | 5 | PASS | PASS | cap | - | - |
| full_retry | False | True | 6 | - | PASS | cap | - | - |
| full_retry | True | False | 5 | PASS | PASS | 3 | 5 | FAIL |
| full_retry | True | False | 6 | - | PASS | 3 | - | - |
| full_retry | True | True | 5 | PASS | PASS | cap | - | - |
| full_retry | True | True | 6 | - | PASS | cap | - | - |
| budget_N1 | False | False | 5 | PASS | FAIL | cap | 1 | FAIL |
| budget_N1 | False | False | 6 | - | FAIL | cap | - | - |
| budget_N1 | False | True | 5 | PASS | FAIL | cap | - | - |
| budget_N1 | False | True | 6 | - | FAIL | cap | - | - |
| budget_N1 | True | False | 5 | PASS | FAIL | cap | 1 | FAIL |
| budget_N1 | True | False | 6 | - | FAIL | cap | - | - |
| budget_N1 | True | True | 5 | PASS | FAIL | cap | - | - |
| budget_N1 | True | True | 6 | - | FAIL | cap | - | - |
| budget_N2 | False | False | 5 | PASS | FAIL | cap | 2 | FAIL |
| budget_N2 | False | False | 6 | - | FAIL | cap | - | - |
| budget_N2 | False | True | 5 | PASS | FAIL | cap | - | - |
| budget_N2 | False | True | 6 | - | FAIL | cap | - | - |
| budget_N2 | True | False | 5 | PASS | FAIL | cap | 2 | FAIL |
| budget_N2 | True | False | 6 | - | FAIL | cap | - | - |
| budget_N2 | True | True | 5 | PASS | FAIL | cap | - | - |
| budget_N2 | True | True | 6 | - | FAIL | cap | - | - |
| cand_fullboot | False | False | 5 | PASS | PASS | 3 | 3 | PASS |
| cand_fullboot | False | False | 6 | - | PASS | 3 | - | - |
| cand_fullboot | False | True | 5 | PASS | PASS | 4 | - | - |
| cand_fullboot | False | True | 6 | - | PASS | 4 | - | - |
| cand_fullboot | True | False | 5 | PASS | PASS | 3 | 5 | FAIL |
| cand_fullboot | True | False | 6 | - | PASS | 3 | - | - |
| cand_fullboot | True | True | 5 | PASS | PASS | cap | - | - |
| cand_fullboot | True | True | 6 | - | PASS | cap | - | - |
| cand_budgetboot_N2 | False | False | 5 | PASS | PASS | 3 | 3 | PASS |
| cand_budgetboot_N2 | False | False | 6 | - | PASS | 3 | - | - |
| cand_budgetboot_N2 | False | True | 5 | PASS | PASS | 4 | - | - |
| cand_budgetboot_N2 | False | True | 6 | - | PASS | 4 | - | - |
| cand_budgetboot_N2 | True | False | 5 | PASS | FAIL | cap | 5 | FAIL |
| cand_budgetboot_N2 | True | False | 6 | - | FAIL | cap | - | - |
| cand_budgetboot_N2 | True | True | 5 | PASS | FAIL | cap | - | - |
| cand_budgetboot_N2 | True | True | 6 | - | FAIL | cap | - | - |

| larger cap: design | crashes | writes in grow | MaxPages | NoOverflow | distinct states |
| --- | --- | --- | --- | --- | --- |
| cand_fullboot | False | True | 8 | PASS | 12286 |
| cand_fullboot | False | True | 10 | PASS | 12286 |
| budget_N2 | False | False | 8 | FAIL | - |
| budget_N2 | False | False | 10 | FAIL | - |
| full_defer | False | True | 8 | FAIL | - |
| full_skip | False | True | 8 | FAIL | - |
