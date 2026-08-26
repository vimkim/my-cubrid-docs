## Stable-PC full-binary follow-up

QA build/runtime 계열에 맞춘 전체 바이너리 재현과 “왜 호출되지 않는 `scope_exit` 변경이 `COUNT(*)`까지
흔들었는가”에 대한 link/CPU pipeline 분석을 완료했습니다.

- QA-2029/A/B/C를 현재 `cubridci/cubridci:develop`의 CentOS 6.10 + devtoolset-8 GCC 8.3.1에서 명시적
  release/`RelWithDebInfo`로 빌드하고 Rocky Linux 8.10에서 실행했습니다.
- QA-2029과 B 각 20회에서 B는 평균 `+1.464%` 느렸고 bootstrap 95% CI는 `+1.039% ~ +1.899%`였습니다.
  QA `+10.56%`의 크기는 재현하지 못했고 사전 5% causal-effect gate도 충족하지 않습니다.
- 원인은 `scope_exit` callback의 직접 실행 비용이 아닙니다. refactor가 GCC 8의
  `log_recovery_redo(...).cold`를 7 byte 줄였고, linker alignment를 거치며 다음 symbol이 8 byte, query hot
  function들이 16 byte 이동했습니다. 예를 들어 `qexec_execute_scan`은 `0x4db580 → 0x4db570`으로 이동해
  32-byte block 내 위치가 `0 → 16`으로 바뀌었습니다.
- A/B central PMU를 5회로 늘리자 IPC는 `-1.519%`, MITE µop/query는 `+12.664%`였습니다. CPU front-end 공급
  경로가 바뀐 것은 맞지만, Top-down에서 front-end bound는 `5.73% → 3.85%`로 감소하고 core bound가
  `10.58% → 13.48%`로 증가했습니다. 따라서 초기 2회의 DSB miss 증가만으로 slowdown을 설명하면 안 되며,
  현재 정확한 분류는 final-binary layout에 민감한 **execution-core pipeline balance 변화**입니다. 마지막
  hardware resource의 인과 확정에는 padding sweep과 PEBS가 필요합니다.
- query I/O matrix 40/40에서 `read_bytes=0`, major fault=0이었고 migration/time 상관은 `r=0.085`였습니다.
  B/C hot address와 raw bytes도 동일합니다. storage, CPU migration, forced destructor `noexcept`, `log_Gl`은
  수정점이 아닙니다.

소스 변경 → 7-byte cold-code 축소 → 16-byte hot-code phase → DSB/MITE 공급 변화 → Top-down core-bound 분류를
모두가 따라갈 수 있도록 SVG와 쉬운 설명을 별도 문서에 정리했습니다.

- 원인 설명 및 SVG:
  <https://github.com/vimkim/my-cubrid-docs/blob/1e2631f/cbrd-26382/CBRD-26382-scope-exit-frontend-causal-chain_codex.md>
- 상세 보고서와 110-run PMU evidence:
  <https://github.com/vimkim/my-cubrid-docs/blob/1e2631f/cbrd-26382/CBRD-26382-gcc8-full-server-follow-up_codex.md>
