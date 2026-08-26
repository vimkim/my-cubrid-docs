# Full-server GCC 8 artifacts

이 디렉터리는 CBRD-26382 후속 분석에서 Git으로 검토하기에 충분한 compact evidence만 보존한다.

- `build-provenance.csv`: source/toolchain과 최종 server DSO identity
- `binary-layout.csv`: A/B/C 최종 `libcubrid.so.11.5` 주요 ELF section
- `hot-symbols.csv`: query hot function과 `log_Gl` 주소 및 64-byte line offset
- `hot-function-hashes.csv`: 해당 함수의 final-file raw byte SHA-256
- `scope-exit-C.patch`: B에서 C를 만드는 단일 forced-`noexcept` patch
- `exclusions.md`: 통계에서 제외한 pilot/incomplete run과 제외 근거
- `query.sql`: correctness-gated workload
- `query-plan.sql`: plan capture workload
- `timings.csv`: 공유 host에서 compiler-contamination gate를 통과한 A/B/C 각 60개 randomized sample
- `timing-summary.json`: 100,000회 paired bootstrap을 포함한 timing summary
- `wayfinder/`: portable map, context, research/hand ticket state
- `manifests/`: origin host의 네 build source/submodule/toolchain/CMake/binary manifest
- `container/`: image inspect/history, observed RPM list, fallback Containerfile
- `scripts/`: worktree 준비, build, timing, paired bootstrap, plan, PMU, profile 수집/요약 script
- `SHA256SUMS`: 이 디렉터리에 포함된 portable artifact 82개의 무결성 목록

PMU/plan evidence는 안정 PC에서 재현 후 같은 디렉터리에 추가한다. 약 160 MiB인 각 ELF, build tree,
`perf.data`, 전체 raw log는 저장소에 넣지 않는다. 원본은 분석 host의
`/home/vimkim/gh/cb/cbrd-26382-results`에 보존한다.

마지막 origin-host 경로는 portable dependency가 아니다. 안정 PC에서는 `scripts/prepare-worktrees.sh`로 source를
재생성하고 새 evidence root에 다시 빌드한다. 원본 ELF/raw log가 추가로 필요한 경우에만 별도 전송한다.

## Runtime configuration

실행 스크립트에는 host results path, container 이름, CPU 번호의 기본값이 없다. 예제 설정을 Git checkout 밖으로
복사하고 안정 PC topology에 맞게 한 번 수정한다.

```bash
cp scripts/runtime-config.example.env /path/to/cbrd-26382-runtime.env
vi /path/to/cbrd-26382-runtime.env
export RUNTIME_CONFIG=/path/to/cbrd-26382-runtime.env
scripts/check-portability.sh
```

모든 build/timing/plan/PMU/profile script는 같은 `RUNTIME_CONFIG`를 읽는다. `RESULTS_ROOT`, `CONTAINER_NAME`,
`SERVER_CPUS`, `CLIENT_CPU`는 필수이며, build에는 `BUILD_IMAGE`와 `BUILD_JDK_HOME`도 필요하다. bundled
`query.sql`, `query-plan.sql`, `scope-exit-C.patch`는 script 위치에서 자동으로 찾는다.
