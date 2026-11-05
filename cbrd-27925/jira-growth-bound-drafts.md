# JIRA 보충 댓글 초안: 성장 상한 설계 (Work821)

2026-11-05, Asia/Seoul. 게시 전 초안이다. 게시는 사용자 승인 뒤에 `cubrid-jira` 로 한다. 근거는 [growth-bound-design.md](growth-bound-design.md)다.

이미 게시된 CBRD-27925 본문, 댓글 4777975, CBRD-26659 댓글 4777976의 핵심은 바꾸지 않는다. 핵심은 "새 sector를 예약하기 전에 회수하거나 재사용한다"이다. 두 댓글은 그 규칙을 지키는 방식과 TC 판정을 보충한다.

## CBRD-27925 댓글

```text
[보충] 성장 전 회수 규칙의 비용과 무장 방식

ADR-0009의 규칙("회수 가능한 빈 페이지가 있으면 새 sector를 예약하지 않는다")은 유지합니다. 이 규칙이 INSERT/UPDATE 비용을 키우는지 확인했고, 결과는 다음과 같습니다.

1. 비용의 원인은 규칙이 아니라 무장 신호입니다.
   feature/oos-merge d52b1889e에서 oos_delete는 chain 삭제가 성공할 때마다 growth-gate sweep을 무장합니다(oos_file.cpp 3512). 페이지가 비었는지는 보지 않습니다. 무장된 다음 성장은 sector 표 전체를 모아 정렬하고, 파일의 모든 페이지를 READ fix합니다. 그동안 같은 파일에서 성장하려는 다른 INSERT는 기다립니다. vacuum fast path가 빈 페이지를 이미 반환했어도 무장은 풀리지 않습니다.

2. 제안: 빈 페이지 후보 집합 (ADR-0010 초안)
   페이지를 비운 지점(oos_delete_chain, oos_rv_redo_delete)에서 그 VPID만 파일별 집합에 넣습니다. 성장은 그 집합만 확인합니다. 재시작이나 OOM으로 집합을 잃으면 파일 전체 lap을 한 번 돕니다(지금의 boot rule과 같습니다). pending_deletes 카운터는 없앱니다.
   - 할당당 비용은 상각 O(1)입니다. 파일 전체 lap은 재시작 뒤 파일당 한 번만 남습니다.
   - READ 경합 힌트 소실(rollback undo가 latch를 쥔 동안 sweep이 페이지를 건너뛰고 lap 정산이 힌트를 지우는 문제)은 구조적으로 닫힙니다. latch에 걸린 후보는 집합에 남습니다.
   - Work818이 제시한 (a) 1차 READ 실패를 DEFERRED로 세기, (b) callback VPID 재시도 집합 중에서는 (b)를 일반화한 형태입니다.

3. TLA+ 검증 (유한 모델: 페이지 5~10개, chunk 2개)
   - 현재 방식: TLC가 Work818 READ 경합 반례를 재현했습니다(현재 규칙 위반).
   - (a), (b): 현재 규칙은 지키지만, 성장 중 동시 쓰기가 sweep cursor를 피해 가면 파일 크기가 모델 상한까지 커집니다.
   - 할당당 N 페이지만 보는 예산 sweep(규칙 약화안): N=1, 2 모두 상한이 없었습니다.
   - 후보 집합: 현재 규칙을 지키고, 동시 쓰기가 있어도 파일 크기가 유계였습니다. 빈 페이지가 없던 성장에서는 페이지를 하나도 검사하지 않았습니다.
   모델은 엔진 코드와의 대응을 자동으로 확인하지 않으며, 성능 수치는 측정하지 않았습니다. 비용 측정은 CBRD-27872에서 합니다.

구현은 ADR-0008 구현(같은 삭제 경로와 fast path 공급을 바꾸는 작업)과 함께 넣는 것을 제안합니다.
보고서: my-cubrid-docs cbrd-27925/growth-bound-design.md
```

## CBRD-26659 댓글

```text
[보충] 회수 TC의 반복 workload 판정 변경 제안

댓글 4777976에서 TC 판정을 "같은 workload를 반복해도 페이지 수가 첫 cycle 피크를 넘지 않는다"로 바꿨습니다. 재실행에서 이 정확 상한이 1 page 단위로 비결정적임을 확인해 여유분을 두는 판정을 제안합니다.

관측 (Work820 a01, 엔진 e3589ae42, TC tc/pr-8128 3ec4e014d, cbrd_26659_snapshots_reclaim)
- cycle 피크: 25 -> 26 -> 26 pages. 첫 cycle 상한 25를 넘어 churn_plateau1·2가 FAIL이었습니다. 직전 실행은 25/23/25로 PASS였습니다.
- 세 피크 모두 OOS 레코드 25개, 합계 268,876B입니다. 레코드가 페이지당 하나라서, 26 pages인 피크에는 빈 페이지가 적어도 하나 할당돼 있었습니다.
- 이 엔진에는 LSA gate가 있어, 명세가 허용하는 유예만으로도 이런 1 page 차이가 생길 수 있습니다. 원인 확정은 하지 않았습니다.

제안 판정
- 모든 cycle k에서: peak_k <= peak_1 + max(2, ceil(peak_1 / 10)). 모든 cycle을 첫 cycle과 비교하므로 누적 성장은 계속 FAIL입니다.
- cycle은 5회 이상으로 늘립니다(현재 3회로는 cycle당 1 page 누적을 잡지 못합니다).
- 정확 상한 유지 여부는 관측값으로 남깁니다.
- 최종 refill의 sector 비교(reuse_before_sector_growth)는 그대로 둡니다.
patch 초안: my-cubrid-docs cbrd-27925/tc-bounded-oracle.patch (bash -n만 확인, DB 미실행)
```
