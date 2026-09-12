# Evidence for CBRD-26659 campaign ticket 16 — injection-site validation

Record: [`../../CBRD-26659-injection-site-validation_f4299ac_claude.md`](../../CBRD-26659-injection-site-validation_f4299ac_claude.md).
Engine baseline `f4299ac0cd777a2a964c1f197ae5ebf9841a4936`; instrumentation worktree `/home/vimkim/gh/cb/oos-instr-f4299ac0c`;
install under test `~/.cub/install/oos-instr-f4299ac0c/debug_gcc`. Bulky artifacts stay under
`~/.cub/campaign/cbrd-26659/ticket16/` and are listed with sha256 in [`SHA256SUMS-bulky.txt`](SHA256SUMS-bulky.txt);
every file in this directory is listed in [`SHA256SUMS-evidence.txt`](SHA256SUMS-evidence.txt).

| Path | What it holds |
|---|---|
| `patches/0001…0007-*.patch`, `patches/SHA256SUMS` | The seven per-file patches of patch set `t16-set1` against the pin (generated with `git diff HEAD -- <file>` in the worktree) and their hashes. `full-diff-against-pin.patch` is the whole worktree diff; `patch-union-proof.txt` shows that applying the seven patches to a pristine checkout of the pin reproduces it byte for byte. |
| `identity/identity-unmodified-instr-worktree.txt` | Version string, library and binary hashes of the instrumentation worktree's build BEFORE any patch (differs from the pinned install's hashes only by build path and time). |
| `identity/identity-patched-set1.txt` | The same for the build under test (patch set `t16-set1`): `libcubrid.so` `dec89384…`, `libcubridsa.so` `a457e0ff…`, `VERSION_STRING 11.5.0.2648-f4299ac`, `BUILD_TYPE debug`. |
| `identity/cores-listing-*.txt` | Core files produced by the abort-path scenarios (two 3.8 GB cores were deleted after being listed; a 200 MB core-size limit applies to later runs). |
| `sites/<site>/` | One fault run per site: `journal.txt` (timeline, pids, wall clock), `cubrid.conf` (instrumented configuration of the run), `*.sql` (the workload as executed, arming statements included), `csql-*.out` (client output), `acks.txt` (the "FAULT INJECTION ACK" lines with their error-log header: time, site file:line, transaction, client), `server-err-excerpt.txt` (acknowledgement in context plus the engine's reaction lines), `pids.txt`, server status outputs. Full server error logs are bulky (hashed). |
| `sites/conf-arming-probe/` | Proof that arming through `cubrid.conf` (used only by site l1) works: site 700000 armed in the file fires. |
| `sites/run-all-first-pass.log` | Console log of the first sequential pass over all twelve sites (a1 fault, c1, i1, j1, k1, l1 were re-run afterwards; their directories hold the final runs). |
| `controls/<site>/` | The fault-disabled control run of each site: identical workload and build, `fault_injection_ids=1` (FI_TEST_HANG, a code no site tests), same layout as `sites/`. `acks.txt` is empty in every control. |
| `corruption/` | The copied-image corruption procedure: `journal.txt`, the byte mutations (`E*-mutation.json`, with the bytes before and after), the PAGE_OOS page scans used to choose targets (`E0-oos-pages*.json`), checkdb and read outputs per experiment (`E*-checkdb-tail.txt`, `E*-read-tail.txt`), and the source-image hashes before and after (`SHA256SUMS.sources.*`, identical). |
| `bounded-fs/` | The bounded test filesystem procedure: `journal.txt` (final attempt), `journal-attempts-1-2.txt` and `journal-attempt-3-*.txt` (earlier attempts and why they stopped), `A-inner.txt` (what ran inside the namespace), `A-createdb.out`, `A-fill-excerpt.txt`, `A-csql-err-excerpt.txt` (the ER_IO_FORMAT_OUT_OF_SPACE error and the OOS allocation assertion), confinement checks (`A-mnt-*.txt`, `A-mount-visible-outside.txt`, `A-home-df-*.txt`), variant B (CUBRID-level bound) outputs, and the earlier tmpfs probes. |
| `tools/` | Everything needed to reproduce: `apply_t16_patches.py` (exact-anchor patch application), `t16env.sh` (environment of the install under test; never references the pinned install), `cubrid.conf.template`, `t16_run.sh` (per-site scenario runner), `t16_run_all.sh` (sequential driver that stops only its own master), `t16_corruption.sh`, `oos_pages.py`, `t16_boundedfs.sh`, `t16_assemble_evidence.sh`. |

Reading an acknowledgement: the error log carries a two-line entry

```
Time: 09/11/26 18:17:21.359 - NOTIFICATION *** file .../src/storage/oos_file.cpp, line 2088  CODE = -588, Tran = 1, CLIENT = dev2:csql(2649123), EID = 3
INTERNAL ERROR: Assertion 'FAULT INJECTION ACK site=oos_publish_oos_oid code=700000 target_operation="…" requested_action="throw std::bad_alloc" reach=1 fired=1 fire_at=0' failed.
```

`site`/file:line identify the site, `target_operation` and `requested_action` are the site's declaration, `reach` is the occurrence at which it fired, `fired` counts firings in this server lifetime, `fire_at` echoes `fault_injection_fire_at_occurrence`. The `Assertion … failed` wording is CUBRID's message for error code -588 (`ER_FAILED_ASSERTION`), which the existing fault-injection handlers also use; no assertion is involved.
