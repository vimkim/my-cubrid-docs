# VERIFICATION — CBRD-26847

source anchor (조사 시작): `6816023df4ed910687523ab4d34bf667ab32b9cd`
최종 검증 commit: `89937d7bdac3d928c06b077fb80f0e6a12985a12`

- 최신 `origin/feat/oos` merge: conflict 없음
- `origin/feat/oos...HEAD` diff: 의도한 11개 파일, 196 insertions, 26 deletions
- whitespace 검증: `git diff --check origin/feat/oos...HEAD` 통과
- debug GCC 전체 build/install: 성공
- OOS CTest: 25/25 통과, 실패 0개, 최종 실행 45.40초
- 전용 visible-version binary: 2/2 통과
- `heap_scanrange_next` first-object 정책 red/green: `CONSUME_RAW_BYTES`에서 OOS batch read 1회로 실패,
  `DONT_CONSUME_RAW_BYTES`에서 0회로 통과
- scanrange following/prior 변경 branch와 locator old-record fetch 두 지점: 동적 계측 없이 정적 소비 흐름 감사
- CTP shell 사용자 관점 회귀: 1/1 통과
- CTP SQL: 로컬 JDBC class 누락으로 case 실행 전에 중단되어 미검증; runner exit code를 성공으로 해석하지 않음
