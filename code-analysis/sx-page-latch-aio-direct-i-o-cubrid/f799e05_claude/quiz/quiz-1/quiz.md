# quiz-1: B-tree insert 하나가 page latch 승격을 몇 번 일으킬까

## 학습 목표

B-tree insert 가 page latch 를 어떤 mode 로 잡고 내려가는지, "읽다가 고쳐야 하는 순간"에 무슨 일이 일어나는지를 직접 관측하고 설명한다.

## 사전 지식

- 3장(scope-interface-seams)과 5장(core-workflows)의 `pgbuf_promote_read_latch` 절.
- csql 기본 사용법. 실험은 버려도 되는 개발용 데이터베이스에서 한다(전용 테이블 `sx_quiz1_t` 만 만들고 지운다).

## 예상 시간

10분.

## 실행 전 예측 (먼저 적고 시작할 것)

PRIMARY KEY 가 있는 빈 테이블에 key 가 1부터 20,000까지 증가하는 행을 한 문장으로 insert 한다.

1. 이 실행에서 page latch 의 READ→WRITE 승격은 몇 번 일어날까? (0번 / 약 20번 / 약 2만 번 / 그 이상)
2. 승격 실패(`Data_page_total_promote_fail`)는 몇 번일까? 그 이유는?

## 절차

```bash
bash run.sh <버려도-되는-DB이름>
```

`run.sh` 는 `promote_quiz.sql` 을 csql 로 실행한다. SQL 파일은 세션 histogram 을 켜고(`;.hist on`), 테이블 생성 → 20,000건 insert → `;.dump_hist` → 테이블 삭제 순으로 진행한다.

## 관측할 것

`;.dump_hist` 출력에서 다음 세 줄을 찾아 기록한다.

- `Num_btree_inserts`
- `Data_page_total_promote_success`
- `Data_page_total_promote_fail`

## 분석 질문

1. 승격 성공 횟수를 insert 건수로 나누면 얼마인가? 왜 insert 1건에 승격이 여러 번인가? (힌트: 하강 경로에서 몇 개의 page 를 지나는지, split 이 나면 어떤 page 들을 고쳐야 하는지)
2. 승격 실패가 관측값처럼 나온 이유는 무엇인가? 어떤 조건이 갖춰지면 실패가 나기 시작하는가?
3. (teach-back) 두 세션이 같은 leaf 근처에 동시에 insert 하는 상황을 가정하고, `pgbuf_promote_read_latch` 가 실패를 반환한 뒤 B-tree 가 무엇을 하는지, SX latch 가 있다면 이 그림이 어떻게 달라지는지 1분 분량으로 설명하라.

## 정리

`promote_quiz.sql` 이 마지막에 `DROP TABLE sx_quiz1_t` 를 실행하므로 별도 정리가 필요 없다. 실행이 중간에 끊겼다면 `DROP TABLE IF EXISTS sx_quiz1_t;` 만 수동 실행하면 된다.

## 관련 자료

- 5장 `chapters/05-core-workflows.html#promote-fail-restart` (claim: CUBRID-C004, CUBRID-C005, CUBRID-C011)
- 실험: experiments/experiment-1
