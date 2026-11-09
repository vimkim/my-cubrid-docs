# A. `cand_fullboot` 깨 보기

이 보고서는 coordinator가 썼다. A 에이전트는 TLC 실행(`runs/r2`)을 마쳤지만 보고서를 쓰기 전에 멈췄다. 아래 표는 `runs/r2/results-main.json`과 `runs/r2/results-combo_NG2.json`을 `table.py`로 출력한 값이다. 반례는 `trace.py`로 `runs/r2/*/tlc.log`에서 뽑았다.

## 1. 후보

이전 추천안 `cand_fullboot`를 그대로 둔다. 페이지가 비면 파일별 집합에 VPID를 넣는다. 성장할 때는 새 sector를 잡기 전에 집합에서 꺼낸 빈 페이지를 먼저 회수한다. 재시작이나 집합 overflow로 목록을 잃으면(`unknown`) single-flight lap을 한 번 돈다.

A의 역할은 이 설계를 공격하는 것이었다. 이전 모델이 둔 제한을 상수 하나씩 풀고, 엄격 규칙(`Strict`, 빈 페이지가 남아 있는 동안 새 sector를 잡지 않음)과 유계 성장(`NoOverflow`)이 버티는지 확인했다.

데이터 형태:

- 파일별 집합. 기본은 중복을 제거하는 VPID 집합, 용량 `K`.
- `unknown` 플래그와 lap 커서.
- 성장자별 `claim`(꺼내서 검사 중인 페이지)과 `checked`(이번 성장에서 본 페이지).

## 2. 결과

유한 모델이다. 공통 상수는 `MaxPages=4`, `Cap=2`(페이지당 chunk), `L=2`, 성장자 `NG=1`, rollback `NU=1`, `K=4`, lap 형태는 d52b1889e의 sweep(`call`)이다. 행마다 하나씩 바꿨다. spec `CandAttack.tla` sha256 `5f06f4c9714c…`. 셀은 cw, cW, Cw, CW 순서다(C = 크래시, W = 성장 중 쓰기). "cap"은 `MaxPages`까지 자랐다는 뜻으로, 모델 안에서는 무한 성장이다. 비용은 성장 한 번에 검사한 페이지 수의 최댓값이다. 쓰기가 있는 셀은 비용을 재지 않았다.

| 행 | 바꾼 것 | Strict | 최악 크기 | 비용 cw/Cw |
| --- | --- | --- | --- | --- |
| base | 없음 | PASS | 3 / 4 / 3 / cap | 3 / 6 |
| span_lap | lap을 여러 성장에 나눠 돎 | PASS | 3 / 4 / 3 / cap | 3 / 6 |
| relatch_free | rollback이 성장 중 latch를 제한 없이 잡음 | PASS | 3 / cap / 3 / cap | 3 / 6 |
| relatch_free_NU2 | 위 + rollback 2개 | PASS | 4 / cap / 4 / cap | 4 / 8 |
| lazy | 다시 채운 페이지를 집합에서 늦게 뺌 | PASS | 3 / 4 / 3 / cap | 4 / 7 |
| visit_once | 한 성장에서 같은 페이지를 한 번만 봄 | PASS | 3 / cap / 3 / cap | 3 / 6 |
| dup_list | 집합 대신 중복 허용 리스트 + lazy | PASS (W는 TIMEOUT) | 3 / cap / 3 / cap | 8 / 8 |
| K1 | 용량 1, overflow 뒤 lap 재실행(epoch) | PASS | 3 / cap / 3 / cap | 5 / 5 |
| K1_noepoch | 용량 1, epoch 없음 | **FAIL** | 4 / cap / 4 / cap | 6 / 6 |
| K1_span | 용량 1, span lap | **FAIL** | cap 전부 | 6 / 6 |
| NG2 | 성장자 2개 | **FAIL** | 4 / 4 / 4 / cap | 3 / 10 |
| NG2_growlock | 성장자 2개, `file_alloc`까지 성장 잠금 | PASS | 3 / 4 / 3 / cap | 3 / 6 |
| NG2_inplace | 성장자 2개, 빈 페이지를 그 자리에서 재사용 | PASS | 4 / 4 / 4 / cap | 3 / 7 |
| fail_eager | 첫 레코드 전에 insert 실패 | **FAIL** | cap 전부 | 3 / 7 |
| fail_lazy | 위 + lazy | **FAIL** | cap 전부 | 5 / 9 |
| fail_note | 실패 경로가 빈 페이지를 집합에 넣음 | PASS | 3 / 4 / 3 / cap | 3 / 6 |
| fail_allocnote | 새로 할당한 페이지를 모두 집합에 넣음 | PASS | 3 / 4 / 3 / cap | 4 / 7 |
| combo | lazy, K=2, in-place, 실패 + note | PASS | 3 / cap / 3 / cap | 6 / 6 |
| combo_NG2 | combo + 성장자 2개 (cw만) | PASS | 4 | ≥11 (TIMEOUT) |

`dup_list`는 모든 셀에서 `NoSetOverflow`도 깨졌다. 상태 수와 시간은 `table.py --full` 출력에 있다. 가장 큰 실행은 2,892만 상태, 602초(`dup_list` cW, TIMEOUT)였다. 전체 실행 시간은 약 36분이다.

## 3. 반례

- **NG2 (19단계).** 성장자 1이 후보를 꺼내 검사하는 동안, 성장자 2는 집합에서 그 후보를 보지 못한다. 성장자 2가 `alloc`으로 가서 새 sector를 잡는다. 원인은 소스의 single-flight가 sweep만 감싸고 `oos_file_alloc_new` 전에 풀린다는 점이다(oos_file.cpp:1890, 2012-2026).
- **fail_eager (7단계).** 새 페이지를 할당한 뒤 첫 레코드를 넣기 전에 insert가 실패한다. 페이지는 빈 채로 남지만 집합에 없다. 다음 성장이 또 새 sector를 잡는다.
- **K1_noepoch (26단계).** lap 도중 rollback이 커서 뒤의 페이지를 비우고, 집합이 넘친다. lap이 끝나면서 `unknown`을 지운다. 놓친 빈 페이지가 남은 채 새 sector를 잡는다.
- **visit_once, 쓰기 (NoOverflow, 42단계).** 다시 채워진 페이지가 집합에 남는다. 성장자는 그 페이지를 보고 버린다. 그 사이 vacuum이 페이지를 다시 비운다. 이것이 성장마다 반복된다.

## 4. A와 C의 "늦게 빼기" 결론 차이

결론은 같다. A의 기본값은 `Revisit=TRUE`여서 한 성장 안에서 같은 페이지를 다시 볼 수 있다. 그래서 `lazy` 행의 크기는 유계로 나왔다. 쓰기가 있는 셀에서는 비용을 재지 않았으므로, 이 PASS는 한 성장이 끝없이 같은 페이지를 다시 보는 경우를 숨긴다. C는 이것을 livelock으로 보고했다. 같은 페이지를 한 번만 보는 `visit_once` 행은 C의 `cand_lazy` 반례와 같은 cap이다. 다시 채운 페이지는 즉시 집합에서 빼야 한다.

## 5. 비용과 구현 크기

성장 한 번에 검사하는 페이지는 base에서 크래시 없이 최대 3개, 크래시 뒤 최대 6개다(모델 단위). 보강 네 가지가 추가하는 비용은 다음과 같다(소스 판독 추정).

- 성장 잠금. `file_alloc`까지 single-flight를 늘린다. 성장 중 다른 INSERT가 기다리는 시간이 늘어난다.
- 실패 경로 note. 실패 경로 하나에 집합 추가 한 번.
- overflow epoch. lap 시작 시 플래그 하나, lap 끝에서 검사 하나.
- lap 뒤 재확인(C의 결과). lap 끝에서 집합을 한 번 더 읽는다.

## 6. 추천

조건부 추천. `cand_fullboot`는 네 가지 보강 없이는 엄격 규칙을 지키지 못한다. 보강하면 모든 행이 통과한다.

1. lap 뒤 집합 재확인 (C `cand_recheck`).
2. 성장 잠금(`NG2_growlock`) 또는 in-place 재사용(`NG2_inplace`).
3. insert 실패 경로의 note(`fail_note`) 또는 할당 시 note(`fail_allocnote`).
4. overflow epoch(`K1`).

다시 채운 페이지는 즉시 집합에서 뺀다(4절).

## 7. 모델의 한계

- 페이지 4개, 성장자 1~2개, rollback 1~2개다. 크기 3·4는 실제 상한이 아니다.
- 크래시와 쓰기가 같이 있는 셀(CW)은 모든 행에서 cap이다. A 모델에는 lap 뒤 재확인이 없다. C는 이 cap의 원인이 재확인 누락이라고 보였다(`cand_recheck` 유계).
- rollback이 성장 중 latch를 제한 없이 잡으면(`relatch_free`) 쓰기 셀이 cap이다. 후보마다 정확한 시점에 insert 후 rollback이 일어나야 하는 경우다. C도 같은 결과를 냈다. 어떤 후보도 이를 막지 못했으므로 모델 한계로 기록한다.
- 쓰기가 있는 셀은 비용을 재지 않았다.
- `combo_NG2`는 cw만 돌렸고 비용 탐색이 시간 제한에 걸렸다.
- 엔진 소스 위치는 d52b1889e 판독에 근거한다.

## 8. 재현

```
python3 -I -B run.py --out runs/r2 --jobs 4 --workers 3
python3 -I -B table.py runs/r2/results-main.json runs/r2/results-combo_NG2.json --full
python3 -I -B trace.py runs/r2/NG2-cw-Safety_Strict-B4-K100-P4
```
