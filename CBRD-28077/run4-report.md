# CBRD-28077 4차 실행: OOS 회수 수정(PR #8493) 전후 비교

- 이슈: [CBRD-28077](https://jira.cubrid.org/browse/CBRD-28077). 관련: CBRD-27872(회수 sweep), CBRD-27925(PR #8493), CBRD-27230(값 재적재)
- 측정: 2026-11-13 04:04 ~ 04:35 (Asia/Seoul), 실행 `run-20261113-0404`. 방법은 [3차 보고서](run3-report.md)와 같다. 전체 표: [run4-tables.md](run4-tables.md)

## 1. 질문과 결론

3차 실행에서 OOS의 비용 원인 두 가지를 확인했다. 작은 컬럼 UPDATE의 값 재적재(CBRD-27230)와, 큰 값 교체 때 새 OOS 페이지를 할당할 때마다 파일 전체를 훑는 회수 sweep(CBRD-27872)이다. 2026-11-13 현재 CBRD-27230의 수정은 없다. CBRD-27872의 sweep은 draft PR [#8493](https://github.com/CUBRID/cubrid/pull/8493)("[CBRD-27925] Reuse emptied OOS pages in place instead of deallocating")이 고친다. 이 PR이 OOS 비용을 얼마나 줄이는지, 다른 시나리오를 느리게 하지 않는지 측정했다.

- **회수 sweep 비용은 사라졌다.** 64 KB 값의 warm 조건 S6(750행 큰 값 교체)는 PR base에서 develop의 ×60.7이었는데, PR 적용 뒤 ×1.23이 되었다. 8 KB에서는 ×24.0에서 ×3.27로, 4 KB에서는 ×3.98에서 ×1.14로 줄었다. 같은 일을 따로 재현한 프로파일에서는 8.4초·page fetch 1,733만 회가 0.2초·7만 7천 회로 줄었다. `oos_try_reclaim_page_internal`(85%)은 프로파일에서 사라졌다.
- **다른 시나리오는 그대로다.** 읽기(S1~S3)의 PR/base 비율은 ×0.97~1.04다. 적재는 ×1.02~1.05, 동시 UPDATE는 ×0.98~1.03이다. 64 KB 반복 UPDATE+INSERT(S7 warm)는 ×0.71, 동시 INSERT(S12)는 ×0.86으로 조금 좋아졌다.
- **작은 컬럼 UPDATE(S5)는 그대로다.** PR/base ×0.83~1.09, develop 대비 ×3.5~11이다. 이 비용은 CBRD-27230이 고쳐져야 줄어든다.
- **확인이 더 필요한 것.** 작은 컬럼 UPDATE+COMMIT 반복의 io 조건(S8s)이 PR에서 ×1.02~1.26으로 조금 높았다. 그러나 3회 반복의 범위가 base와 일부 겹친다(8 KB: base 0.81~0.97 G, PR 0.82~1.08 G). DELETE(S9)의 io 조건은 base 자체의 반복 값이 0.18~2.7 G로 흔들려 판단할 수 없다.

## 2. 비교 대상

| 빌드 | 커밋 | 역할 |
| --- | --- | --- |
| develop | `a7f220d5d7` | 비율의 기준 |
| OOS | [`c02f897268`](https://github.com/CUBRID/cubrid/commit/c02f897268b03526c1b4dd0359220f924d58b810) | 3차 실행과 같은 OOS |
| OOS PR base | [`67220b7e23`](https://github.com/CUBRID/cubrid/commit/67220b7e230ff1587ba5940001d72e10477a1fc4) | PR #8493이 병합한 `feature/oos-merge` |
| OOS + PR #8493 | [`f1c78ce70b`](https://github.com/vimkim/cubrid/commit/f1c78ce70bb469f5d1d39204cc71a5fe3d832b54) | PR head. CBRD-27925 커밋과, 그 아래 쌓인 CBRD-27781 커밋(PR #8434)을 포함한다 |

PR의 효과는 "PR / base" 열로 본다. PR에는 CBRD-27781의 commit-postpone 변경도 함께 들어 있어, 아래 차이를 CBRD-27925 커밋 하나의 효과로만 볼 수는 없다. 값 크기는 4 KB, 8 KB, 64 KB이고, 모든 시나리오를 조건마다 3회 반복했다. 네 빌드를 동시에 실행했다.

검증: 측정한 문장 180개의 결과와 단계별 checksum·값 길이 검사 30개가 네 빌드에서 모두 일치했다. 실패한 문장은 없었다.

## 3. 결과

develop 대비 서버 명령어 수(drain 포함, 3회 중앙값) 비율이다. "PR / base"가 0.8 이하이거나 1.2 이상이면 굵게 표시했다.

| 시나리오 | 값 | 조건 | OOS `c02f897268` | PR base `67220b7e23` | PR #8493 `f1c78ce70b` | PR / base |
|---|---|---|---|---|---|---|
| S6 큰 컬럼 UPDATE 1/8 | 4 KB | io | ×2.35 | ×2.42 | ×2.41 | ×1.00 |
| S6 큰 컬럼 UPDATE 1/8 | 4 KB | warm | ×3.04 | ×3.98 | ×1.14 | **×0.29** |
| S6 큰 컬럼 UPDATE 1/8 | 8 KB | io | ×3.95 | ×4.06 | ×3.71 | ×0.91 |
| S6 큰 컬럼 UPDATE 1/8 | 8 KB | warm | ×23.62 | ×24.01 | ×3.27 | **×0.14** |
| S6 큰 컬럼 UPDATE 1/8 | 64 KB | io | ×5.55 | ×5.45 | ×5.12 | ×0.94 |
| S6 큰 컬럼 UPDATE 1/8 | 64 KB | warm | ×121.75 | ×60.69 | ×1.23 | **×0.02** |
| S7 UPDATE+INSERT+COMMIT 600회 | 4 KB | io | ×1.20 | ×1.25 | ×1.28 | ×1.02 |
| S7 UPDATE+INSERT+COMMIT 600회 | 4 KB | warm | ×1.00 | ×1.06 | ×1.07 | ×1.01 |
| S7 UPDATE+INSERT+COMMIT 600회 | 8 KB | io | ×1.40 | ×1.40 | ×1.38 | ×0.99 |
| S7 UPDATE+INSERT+COMMIT 600회 | 8 KB | warm | ×0.99 | ×1.00 | ×1.06 | ×1.06 |
| S7 UPDATE+INSERT+COMMIT 600회 | 64 KB | io | ×1.27 | ×1.23 | ×1.04 | ×0.85 |
| S7 UPDATE+INSERT+COMMIT 600회 | 64 KB | warm | ×1.40 | ×1.42 | ×1.01 | **×0.71** |
| S12 8 client 큰 값 INSERT | 4 KB | warm | ×0.92 | ×0.91 | ×0.95 | ×1.04 |
| S12 8 client 큰 값 INSERT | 8 KB | warm | ×1.70 | ×1.72 | ×1.48 | ×0.86 |
| S12 8 client 큰 값 INSERT | 64 KB | warm | ×2.49 | ×2.49 | ×2.15 | ×0.86 |
| S5 작은 컬럼 UPDATE 전체 | 4 KB | io | ×3.83 | ×3.75 | ×3.93 | ×1.05 |
| S5 작은 컬럼 UPDATE 전체 | 4 KB | warm | ×3.87 | ×3.83 | ×3.48 | ×0.91 |
| S5 작은 컬럼 UPDATE 전체 | 8 KB | io | ×7.18 | ×7.20 | ×7.85 | ×1.09 |
| S5 작은 컬럼 UPDATE 전체 | 8 KB | warm | ×10.19 | ×10.24 | ×9.63 | ×0.94 |
| S5 작은 컬럼 UPDATE 전체 | 64 KB | io | ×10.49 | ×10.50 | ×11.14 | ×1.06 |
| S5 작은 컬럼 UPDATE 전체 | 64 KB | warm | ×11.14 | ×11.07 | ×9.18 | ×0.83 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | 4 KB | io | ×1.41 | ×1.53 | ×1.56 | ×1.02 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | 4 KB | warm | ×1.11 | ×1.13 | ×1.21 | ×1.07 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | 8 KB | io | ×1.61 | ×1.51 | ×1.91 | **×1.26** |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | 8 KB | warm | ×1.49 | ×1.39 | ×1.18 | ×0.85 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | 64 KB | io | ×2.09 | ×2.15 | ×2.41 | ×1.12 |
| S8s 작은 컬럼 UPDATE+COMMIT 600회 | 64 KB | warm | ×1.17 | ×1.18 | ×1.07 | ×0.91 |

OOS `c02f897268`과 PR base `67220b7e23`은 거의 같은 값을 보인다. 64 KB warm S6에서만 ×121.75와 ×60.69로 다른데, 이는 sweep이 반복마다 다른 양을 훑기 때문이다(반복별 값: OOS 204 G·3.4 G·42 G, base 205 G·3.5 G·21 G).

## 4. 프로파일로 확인

3차 보고서 6.2절과 같은 재현을 PR 빌드에서 했다. 64 KB 값 6,000행을 적재하고, 작은 컬럼 UPDATE(S5)로 OOS 파일을 두 배로 만든 뒤, 750행의 큰 값을 교체했다. 도구는 [tools/oos_s6_probe.py](tools/oos_s6_probe.py)다(`python3 oos_s6_probe.py OUTDIR oos-8493`).

| 빌드 | 경과 시간 | page fetch | 프로파일 상위 |
| --- | ---: | ---: | --- |
| OOS `c02f897268` | 8.4초 | 17,329,620 | `oos_try_reclaim_page_internal` 82% → `pgbuf_fix_release` |
| OOS + PR #8493 | 0.2초 | 77,382 | `oos_insert_many` 20%(새 값 적재). 회수 sweep 함수 없음 |

## 5. CBRD-28077 결론에 미치는 영향

3차 보고서의 "큰 값 교체(S6)" 행에서 OOS는 ×2.33~597이었다. PR #8493을 적용하면 ×1.14~5.12가 된다. warm 조건(×1.14~3.27)은 Sidecar(×1.47~2.17)와 비슷하다. io 조건(×2.41~5.12)은 여전히 Sidecar보다 크고, Inner Table(×3.01~8.21)과 비슷하다. 작은 컬럼 UPDATE(S5)와 작은 컬럼 반복 UPDATE(S8s)의 OOS 비용은 CBRD-27230이 고쳐질 때까지 그대로다. 그 수정이 나오면 같은 방법으로 다시 측정한다.
