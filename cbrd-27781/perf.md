# ADR-0008 회수 변경의 성능 측정 (decision 7)

2026-11-05, Work742. ADR-0008 decision 7은 엔진 변경의 병합 조건으로 측정된 개선을 요구한다: 회수한 값 하나당 로그 바이트, OOS UPDATE 부하의 vacuum 시간, UPDATE/DELETE churn 뒤 OOS 파일 크기, 그리고 INSERT·UPDATE 지연이 나빠지지 않을 것.

## 대상과 방법

| 항목 | 값 |
| --- | --- |
| 기준(base) | `feature/oos-merge` `d52b1889e` release_gcc |
| 변경(new) | `CBRD-27781-postpone-commit` `3e8072f56` release_gcc |
| 서버 | server mode, 표본마다 새 DB(1G 볼륨, 512M 로그, data_buffer 512M), 별도 포트 |
| 부하 | `t(id INT PK, v BIT VARYING)` 3000행, 값 6000바이트(서로 다른 MD5 375개를 이은 값이라 로그 LZ4 압축이 거의 듣지 않음, 값 하나가 OOS chunk 하나). INSERT → UPDATE 3회(매회 새 값, 회마다 commit) → vacuum drain → DELETE → drain → 재삽입 |
| 반복 | base·new 교대로 3회씩, 중앙값 |
| 측정 | 문장 지연(csql -C 클라이언트 벽시계), `SHOW LOG HEADER`의 `Current_append` 차이(로그 바이트), `SHOW HEAP OOS`의 `Oos_num_recs`·`Oos_num_user_pages` |
| 스크립트 | [bench/oos_update_churn.sh](bench/oos_update_churn.sh), [bench/run_all.sh](bench/run_all.sh), 원자료 [bench/results-3e8072f56-vs-d52b1889e.csv](bench/results-3e8072f56-vs-d52b1889e.csv) |

vacuum은 닫힌 로그 block만 처리하므로 drain 동안 OOS가 없는 filler 테이블에 행을 넣어 로그를 밀었다. filler 한 번의 로그 바이트를 부하 전에 세 번 재고 중앙값을 뺐다. 이번 측정에서는 두 쪽 모두 drain에 filler가 한 번만 필요했다.

## 결과 (중앙값)

| 지표 | base | new | 변화 |
| --- | --- | --- | --- |
| UPDATE 3회 + drain 로그 합계 | 114.8 MB | 66.2 MB | −42% |
| 버린 값 하나당 회수 로그 (위 합계 − 새 값 삽입분 3×19.9 MB, ÷ 9000) | 약 6.1 KB | 약 0.71 KB | −88% |
| DELETE + drain의 vacuum 로그 | 16.5 MB | 2.8 MB | −83% |
| churn 뒤 OOS 페이지 | 3539 | 1502 | 빈 페이지 반환 |
| DELETE drain 뒤 OOS 페이지 | 3539 | 1 | |
| 재삽입 뒤 OOS 페이지 | 3539 | 1501 | 반환된 페이지 재사용 |
| drain 시간(마지막 UPDATE commit부터) | 0.37 s | 0.31 s | 차이 작음 |
| INSERT 3000행 | 5.75 s (5.75–6.79) | 6.39 s (6.08–7.90) | 판단 불가 |
| UPDATE 1/2/3회 | 5.76 / 6.80 / 6.22 s | 6.98 / 5.99 / 6.10 s | 판단 불가 |

해석:

- 로그: base는 vacuum이 chunk를 지울 때 6 KB undo image를 남긴다. new는 UPDATE 때 drop postpone, commit 때 알림, vacuum 때 redo-only 삭제만 남긴다. UPDATE 회당 new는 행마다 약 400바이트를 더 쓰지만(1회차 19.9 → 21.1 MB), vacuum 쪽 6 KB를 없앤다.
- 파일 크기: base는 churn 동안 삭제 뒤의 빈 페이지가 LSA gate와 fast path 부재로 남아 3539 페이지가 되고 DELETE 뒤에도 그대로다. new는 알림 소비와 REMOVE가 비운 페이지를 즉시 반환한다.
- vacuum 진행: 마지막 UPDATE 직후 남은 OOS 레코드는 base 3009, new 3916이다. new는 알림이 commit 뒤에 생기므로 vacuum이 조금 늦게 따라온다. 어느 쪽도 drain에 1초 미만이 걸렸다.

## 한계

- 측정 장비는 80코어 공용 서버이고 측정 중 load average가 57–60이었다. 지연의 범위가 겹치고 반복이 3회뿐이라 INSERT·UPDATE 지연이 나빠지지 않았다고 말할 수 없다. decision 7의 지연 조건은 조용한 장비에서 반복을 늘려 다시 재야 한다.
  - 2026-11-12에 다시 쟀다([재측정](latency-8495/README.md)). PR만으로는 지연 조건을 통과하지 못한다. postpone이 있는 커밋이 로그를 두 번 flush해서, 행 단위 UPDATE+COMMIT 3000번이 base 12.28 s에서 16.22 s(+32%)로 늘었다. 이 flush를 없애는 #8495(CBRD-28046)를 얹으면 11.13 s로 base와 차이가 없다. 그래서 #8434는 #8495가 `feature/oos-merge`에 들어온 뒤 merge한다.
- vacuum 시간은 log block당 시간이 아니라 drain 벽시계로만 봤다. vacuum이 UPDATE 동안 대부분 따라잡아 차이가 작다.
- 부하는 단일 세션, 값당 chunk 하나다. 다중 chunk 값, 동시 UPDATE, 긴 snapshot은 재지 않았다.
- `REPEAT(MD5(...))`처럼 압축이 잘 되는 값으로 처음 잰 결과(로그가 오히려 늘어 보임)는 로그 압축이 undo image를 줄여 이 변경의 효과를 가렸으므로 쓰지 않았다.
