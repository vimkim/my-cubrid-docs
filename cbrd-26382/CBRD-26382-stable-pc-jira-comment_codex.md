## Stable-PC padding control 및 cold-state 재검증

기존 stable-PC 결과의 server/DB lifecycle을 QA shell과 다시 대조하고, B의 실행 로직은 유지한 채 linker 입력
section 길이만 복원하는 diagnostic D를 추가해 재측정했습니다.

- **Lifecycle 정정:** stable harness도 매 sample마다
  `server start → query 1회 → server stop`을 실행하고 `cub_server`/`cub_master` 종료를 확인했습니다. 따라서 이전
  sample의 CUBRID buffer pool을 재사용한 결과가 아닙니다. QA 자동 shell은 여기에
  `createdb → ... → deletedb`가 더해지지만, 어느 쪽도 host page cache를 drop하지 않습니다. 또한 현재 QA 자동
  shell의 `TRACE ON`/`LIMIT` query와 JIRA의 수동 `TRACE OFF` 5회 측정은 서로 다른 protocol이며, 수동 5회
  사이의 restart cadence는 기록돼 있지 않습니다.
- **Diagnostic D:** B와 같은 source logic/query object/`log_Gl` layout을 유지하고, 앞쪽
  `log_recovery.c.o:.text.unlikely`에 실행 불가능한 NOP 7 bytes만 복원했습니다. D의 주요 query hot-function
  시작 주소는 A와 같아졌습니다. 즉 B/D는 실행 로직, A/D는 hot-code address phase를 각각 통제합니다.
- **Timing:** shared-DB balanced 54회 중앙값은 B/A `+1.336%`, D/B `-1.786%`, D/A `-0.474%`였습니다. QA
  shell lifecycle을 따른 fresh-DB 27회 round-paired 결과도 B/A `+0.857%`, D/B `-1.520%`, D/A
  `-0.676%`로 같은 방향이었고, 세 round 모두 B가 A보다 느리고 D가 B보다 빨랐습니다. query 구간의
  `read_bytes`와 major fault는 27/27 모두 0이었습니다.
- **PMU:** A/B/D balanced 90회에서 B→D는 cycles/query `-1.446%`, IPC `+1.467%`, MITE µops/query
  `-7.048%`, host-perf DSB→MITE penalty/query `-24.214%`였습니다. Top-down core bound는
  `13.714% → 9.865%`, retiring은 `80.947% → 82.443%`로 A 수준에 돌아왔습니다. 반면 front-end bound는
  D에서 높아졌는데도 D가 빨랐으므로, **DSB miss 하나가 slowdown의 단독 원인이라는 설명은 기각**합니다.
- **결론:** `scope_exit` callback의 직접 실행 비용이나 forced `noexcept`, `log_Gl`, disk read가 원인이 아닙니다.
  7-byte control에서 hot-code phase와 time/pipeline이 함께 복원됐으므로, PR이 만든 **final-link layout 변화가
  성능을 움직였다는 인과는 강하게 확인**됐습니다. 다만 QA의 `+10.56%` 전체와 마지막 execution resource를
  확정하려면 historical QA ELF/PMU와 추가 phase/PEBS가 필요합니다.
- **최신 compiler:** 작성일 기준 GCC 16.2/Clang 22.1.8은 GCC 8보다 세밀한 alignment 및 profile-driven
  ordering 수단을 제공하지만, non-PGO compiler upgrade만으로 실제 SQL의 hotness나 최적 `%32` phase를 알거나
  보장하지는 못합니다. 동일 runtime에서 compiler와 linker를 분리한 A/B 및 PGO matrix로 확인해야 합니다.

문서와 재현 자료:

- 원인 설명 및 SVG:
  <https://github.com/vimkim/my-cubrid-docs/blob/83ef30bd5c42105dfa41939e3b52951a34b318ac/cbrd-26382/CBRD-26382-scope-exit-frontend-causal-chain_codex.md>
- 상세 보고서와 A/B/D timing·PMU evidence:
  <https://github.com/vimkim/my-cubrid-docs/blob/83ef30bd5c42105dfa41939e3b52951a34b318ac/cbrd-26382/CBRD-26382-gcc8-full-server-follow-up_codex.md>
- hot-function alignment 및 최신 GCC/Clang 선택지:
  <https://github.com/vimkim/my-cubrid-docs/blob/83ef30bd5c42105dfa41939e3b52951a34b318ac/cbrd-26382/CBRD-26382-hot-function-alignment-options_codex.md>
- compact artifacts와 재현 scripts:
  <https://github.com/vimkim/my-cubrid-docs/tree/83ef30bd5c42105dfa41939e3b52951a34b318ac/cbrd-26382/artifacts/full-server-gcc8>
