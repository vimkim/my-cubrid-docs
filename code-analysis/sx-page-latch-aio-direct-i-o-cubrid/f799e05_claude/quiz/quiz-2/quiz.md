# quiz-2: flush를 카운터로 관측하기

## 학습 목표

CUBRID flush 깔때기(`pgbuf_bcb_flush_with_wal`)의 실행을 런타임 카운터로 관측하고, 각 카운터가 정확히 무엇을 세는지 소스에서 확인한다. 여기서 고른 지표가 SX 도입 효과 측정의 오라클이 된다.

## 사전 지식

- 6장(flush-frame-stability)의 flush 흐름도.
- `cubrid statdump` 사용법. 버려도 되는 개발용 데이터베이스 필요(전용 테이블 `sx_quiz2_t` 만 만들고 지운다).

## 예상 시간

15분.

## 실행 전 예측 (먼저 적고 시작할 것)

10,000건을 insert(commit)한 뒤 `cubrid backupdb`(동기 checkpoint 유발)를 실행하고 `cubrid statdump` 를 찍는다.

1. `Num_data_page_dirties` 는 0일까, 수십일까, 수만일까?
2. checkpoint 가 dirty page 를 디스크로 밀어냈다면 `Num_data_page_flushed` 는 얼마가 되어 있을까?
3. `Num_data_page_iowrites` 는?

## 절차

```bash
bash run.sh <버려도-되는-DB이름> <백업파일을-쓸-임시디렉터리>
```

`run.sh` 는 (1) 백그라운드 statdump watcher 를 붙이고 (2) `flush_quiz.sql` 로 insert + 세션 histogram 을 실행하고 (3) `backupdb -C -r` 로 checkpoint 를 강제한 뒤 (4) 최종 statdump 를 출력하고 (5) watcher 를 정리한다.

## 관측할 것

- csql 출력(`;.dump_hist`)의 `Num_data_page_dirties`
- 최종 statdump 의 `Num_data_page_iowrites` 와 `Num_data_page_flushed`

## 분석 질문

1. 왜 watcher 를 붙여야만 카운터가 움직이는가? (힌트: `stats_on` 파라미터의 기본값)
2. 세 카운터의 관측값 조합이 말이 되려면 `Num_data_page_flushed` 는 정확히 무엇을 세는 카운터여야 하는가? 소스에서 그 증가 지점을 찾아 확인하라. (힌트: `rg PSTAT_PB_NUM_FLUSHED src/`)
3. (teach-back) flush 깔때기가 page 사본을 뜨는 이유, 그리고 그 사본 덕분에 I/O 동안 writer 가 자유로운 구조를 설명하라. buffered write 대신 direct I/O/AIO write 로 바꾸면 이 구조의 어디가 깨지는가?

## 정리

`flush_quiz.sql` 이 `sx_quiz2_t` 를 스스로 삭제하고, `run.sh` 가 watcher 와 백업 아카이브를 정리한다. 중간에 끊겼다면: `DROP TABLE IF EXISTS sx_quiz2_t;` 실행, `pgrep -f "statdump.*<DB이름>"` 로 자기 소유 watcher 확인 후 종료.

## 관련 자료

- 6장 `chapters/06-flush-frame-stability.html#flush-frame-stability` (claim: CUBRID-C007, CUBRID-C012)
- 11장 `chapters/11-performance-observability.html` — 관측 지표 (실행 후에 읽을 것)
- 실험: experiments/experiment-2
