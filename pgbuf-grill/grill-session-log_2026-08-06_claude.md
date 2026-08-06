# Grill 세션 로그 — CUBRID Page Buffer 3사 비교 (2026-08-06)

> 목적: pgbuf 세미나 리포트 + quizzes 학습 후 grill 세션의 진행 상태 기록. **재개 시 이 파일을 읽으면 전체 맥락 복원 가능.**
> 워크트리: `~/gh/cb/pgbuf-analysis` (commit 5cd4f860e — 주의: pgbuf 로컬 커밋 포함, stock 11.5 아님)
> 선행 세션: `../storage-grill/grill-session-log_2026-08-03_claude.md` (WAL/vacuum/sysop 기초 — 4/4 정답, 기초 레벨은 재출제하지 않음)

## 출제 소스

- 리포트: `../pgbuf-analysis/cubrid-page-buffer-report_5cd4f860e_claude.html`
- 팩트시트: `../pgbuf-analysis/research/*.md` (cubrid-structs-fix / cubrid-lru-victim / cubrid-flush-wal-dwb / postgres-bufmgr / innodb-bufpool)
- 실습: `~/gh/cb/pgbuf-analysis/quizzes/01..12` (실측 수치 포함)

## 세션 설계

- **형식**: 4지선다 rapid-fire + 자유서술 심화. 매 답변 후 `file:line` 근거로 채점/해설. 오답 영역은 레벨 내 재출제.
- **레벨 설계**:
  - L1 어휘/해부학 — fix vs latch vs 홀더, BCB 플래그 워드, zone/quota 용어, 게이지 vs 누적 카운터
  - L2 메커니즘 워크스루 — miss 경로 전체, unfix의 LRU 결정 트리, victim 선택 3단계, flush_with_wal 순서, DWB 블록 flush 순서
  - L3 엣지/함정 — AOUT 비활성, restrict_other, direct victim 기아 방지, latch 타임아웃(=deadlock 해결), NEW_PAGE 히트 집계, DWB 시 iowrites 이중 집계, 사문화 코드 3종
  - L4 크로스 엔진 설계-왜 — clock-sweep vs LRU 리스트, ring vs quota vs midpoint, FPW vs DWB, fuzzy checkpoint 3사 비교
- **선행 세션에서 이미 확인된 것 (재출제 금지)**: WAL 규칙의 pgbuf 강제 지점(`pgbuf_bcb_flush_with_wal`), vacuum의 로그 기반 동작, DELETE의 MVCC 도장, sysop 롤백.

## 진행 상황

(세션 시작 전 — 사용자가 리포트/퀴즈 학습 후 "grill 시작" 시 여기부터 기록)
