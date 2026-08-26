## Stable-PC full-binary follow-up

QA build/runtime 계열에 맞춰 전체 CUBRID 바이너리를 다시 비교했습니다.

- QA-2029/A/B/C를 현재 `cubridci/cubridci:develop` image의 CentOS 6.10 + devtoolset-8 GCC 8.3.1에서
  `./build.sh -m release ... build`로 순차 빌드했습니다. 네 CMake cache 모두 `RelWithDebInfo`,
  `-O2 -g -DNDEBUG`를 확인했고, 설치 바이너리는 Rocky Linux 8.10에서 실행했습니다.
- QA-2029과 B를 각 20회 측정한 결과 B가 평균 `+1.464%` 느렸고, 100,000회 bootstrap 95% CI는
  `+1.039% ~ +1.899%`였습니다. QA에서 보고된 `+10.56%`의 크기는 재현하지 못했지만 slowdown 방향과
  통계적 분리는 확인했습니다. 사전에 정한 5% causal-effect 기준은 충족하지 않습니다.
- 모든 I/O matrix query 40회에서 physical `read_bytes=0`, major fault=0이었고, elapsed time과 server CPU
  migration 횟수의 상관은 `r=0.085`였습니다. 이 SQL의 stable-PC 차이를 storage 또는 migration으로 설명할
  근거는 없습니다.
- A→B에서 query hot function들이 16 byte 이동하여 cache-line phase가 바뀌었습니다. 두 PMU 반복 평균에서
  IPC `-1.615%`, retired DSB(decoded-uop cache) miss/s `+52.819%`, MITE uops/s `+21.727%`였고, cycle
  profile은 실제 workload가 이동한 query executor/scan 함수들에서 실행됨을 확인했습니다.
- B/C의 query hot-function 주소와 raw bytes는 동일하고 forced destructor `noexcept`의 timing 방향도
  일관되지 않았습니다. `log_Gl`도 B/C에서 동일합니다. 따라서 forced `noexcept`와 `log_Gl` 배치는 수정점이
  아니며, PR 전체 refactor가 만든 final-link instruction front-end layout 변화가 현재 가장 강한 원인 후보입니다.

현재 `develop` image tag는 mutable이고 2025년 QA 원본 package/image digest는 확보하지 못했습니다. 따라서
정확한 `+10.56%` 전체를 단정하지 않으며, 오래된 QA CPU/RAM 계층에서 같은 front-end/cache 차이가 더 크게
증폭됐을 가능성으로 결론을 제한합니다. 성능을 이유로 generic `scope_exit` destructor를 강제 `noexcept`로
바꾸는 것은 권고하지 않습니다.

- 상세 보고서 및 compact evidence:
  <https://github.com/vimkim/my-cubrid-docs/blob/afe5f11/cbrd-26382/CBRD-26382-gcc8-full-server-follow-up_codex.md>
