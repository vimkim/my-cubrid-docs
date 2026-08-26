# Stable-PC `cubridci` evidence

This directory contains the compact evidence for the stable-PC rerun of CBRD-26382.

- Build: current `docker.io/cubridci/cubridci:develop`, CentOS 6.10, devtoolset-8 GCC 8.3.1.
- Build action: repository `./build.sh -m release ... build`; every cache records `RelWithDebInfo` and
  `-O2 -g -DNDEBUG`.
- Runtime: Rocky Linux 8 container on an Intel Core Ultra 7 270K Plus host.
- Scheduling: server and CSQL may migrate inside P-core set `0-7`; they are not pinned to one CPU.
- SQL result: `49^5 = 282475249` for every accepted run.

Files:

- `timing-summary.json`, `qa-pcores-five.csv`, `pcores-io.csv`: timing, bootstrap, migration, process I/O,
  page-fault, and CPU-tick evidence.
- `pmu-summary-60-runs.json`: 최초 2-repetition central-group snapshot.
- `pmu-summary-110-runs.json`: A/B central group을 5회로 늘리고 Top-down L1/L2 각 5회를 추가한 최종 summary.
- `hot-symbols.csv`, `hot-function-hashes.csv`: final `libcubrid.so.11.5` layout and raw function bytes.
- `layout-shift-chain.csv`: 7-byte recovery cold-code 축소가 8-byte, 16-byte final-address 이동으로 전파된 chain.
- `perf-profile-summary.csv`: address-resolved flat cycle-profile functions reported at or above 0.5%.
- `plan-hashes.csv`: normalized plan hashes.
- `padding-balanced.csv`, `padding-balanced-summary.json`: A/B/D shared-DB balanced-position timing and bootstrap.
- `padding-freshdb.csv`, `padding-freshdb-summary.json`: QA automatic-shell lifecycle을 재현한 fresh-DB A/B/D timing.
- `padding-D-elf-gates.csv`, `padding-D-query-object-hashes.csv`: D의 7-byte section, A/D hot-address,
  B/D query-object, B/D `log_Gl` causal gates.
- `pmu-padding-abd-summary.json`: 6개 순서로 균형화한 A/B/D 90-run core/DSB-MITE/retired-FE/Top-down summary.
- `D-plan.log`: D의 cardinality와 query plan capture.
- `manifests/`: source/submodule, toolchain, CMake mode, binary hash, Build ID, and ELF section evidence.

D is a diagnostic control, not a proposed product patch. It keeps B's source logic and adds seven unreachable NOP bytes to
the contributing `.text.unlikely` input section. Its pre-link query objects are identical to B, its final hot-function starts
match A, and its `log_Gl` address matches B. D was rebuilt one day later, so release-date content and 32 bytes of `.rodata`
remain a disclosed residual difference.

The first D build's pre-build probe captured the image's default Java 7 even though `build.sh -j /opt/jdk8` selected Java 8.
The portable build script was corrected to prepend the configured JDK to `PATH`, and the final D manifest now records
Java/Javac `1.8.0_442`. D was rebuilt after adding the required GNU-indent off/on comments around its inline assembly; the
old and final D runtime `.text` have the same SHA-256, so the comment-only rebuild does not change the measured executable
instructions.

The mutable image tag resolved to local image ID
`3f5731ae2f0b41804857eb35b2e1f8948c6d1b341e7594d3d0146ff3f94168ba` and repository digest
`sha256:3a6f53a2dd3c9bca3b5b0b88293bad92109ac304480493e1ff301a6aa563a157` on 2026-08-26.
This proves the stable rerun provenance, not the historical November 2025 `develop` digest used by QA.
