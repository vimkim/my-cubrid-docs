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
- `manifests/`: source/submodule, toolchain, CMake mode, binary hash, Build ID, and ELF section evidence.

The mutable image tag resolved to local image ID
`3f5731ae2f0b41804857eb35b2e1f8948c6d1b341e7594d3d0146ff3f94168ba` and repository digest
`sha256:3a6f53a2dd3c9bca3b5b0b88293bad92109ac304480493e1ff301a6aa563a157` on 2026-08-26.
This proves the stable rerun provenance, not the historical November 2025 `develop` digest used by QA.
