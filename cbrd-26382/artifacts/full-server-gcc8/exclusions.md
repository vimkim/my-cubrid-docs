# Excluded runs

최종 통계에는 `/home/vimkim/gh/cb/cbrd-26382-results/bench/timings.csv`의 correctness-gated matrix만 사용한다.
다음 pilot/incomplete run은 local evidence에 보존하지만 통계에서는 제외한다.

| local directory | 제외 이유 |
|---|---|
| `instances-onecpu-failed` | server 전체 thread를 CPU 한 개에 고정해 watchdog/server restart 발생 |
| `instances-twocpu-multimaster-failed` | 네 container 동시 실행 중 master lifecycle gate 실패 |
| `single-objcopy-rewritten-failed` | 잘못된 read-only 가정으로 `objcopy --dump-section`이 설치 DSO를 재작성; hash audit에서 발견 |
| `single-external-build-contaminated-failed-20260826` | 타 사용자의 대규모 GCC build로 load average 80+, B 표본 37.596649초 발생 |
| `single-guard-false-positive-incomplete-20260826` | runnable threshold 12가 80-CPU host의 정상 13 tasks를 과민 감지 |
| `single-transient-compiler-gate-incomplete-20260826` | 시작 전에 `cc1plus` 2개를 감지해 query 실행 없이 차단 |

재작성된 DSO는 `objcopy-rewritten-quarantine`에 격리했고, 최종 측정 전에 untouched build tree에서 다시
install하여 네 DSO의 SHA-256이 최초 manifest와 정확히 일치하는지 확인했다.
