# Fresh baseline and preparation

The source at build and probe time was `c63a3b993be552ef6ad3ce244c386d5081147958`, debug_gcc. See `identity.json` for installed binary hashes and `present.json` for raw evidence. The existing namespace probe ran with separately started master and PID-1 reaping.

Startup returned 0 at 2.106 seconds. At two seconds after exit neither stdout nor stderr had EOF; the caller lock could not be reacquired. Server and PL retained the caller resources. Cleanup completed. This is a failing baseline, not a fixed-binary pass.

Compilation and installation succeeded. The complete build recipe initially returned 4 during runtime preparation because its shared legacy guard rejected another worktree's retained transaction. No guard records were changed. Explicit supported `cub-workenv init --no-db` subsequently initialized this task runtime successfully.

A rebuild was interrupted after discovering an external fast-forward of this engine worktree to `15e7dc8b5b56fd8751d56ccae1fdf87d315bd35d` at 2026-10-02 20:19:22 +09:00. Neither the main nor ticket 01 worker performed that merge. Source/install preflight correctly rejected the resulting commit mismatch. The user subsequently confirmed adopting the new HEAD and exclusive worktree availability. New-base build/probe results will be stored separately. Ticket 01 has made no source or test edits.

Local logs retained:
- `/home/vimkim/.cache/cbrd27443-configure.log`
- `/home/vimkim/.cache/cbrd27443-build-baseline.log`
- `/home/vimkim/.cache/cbrd27443-probe-baseline.log`
- `/home/vimkim/.cache/cbrd27443-workenv-init.log`
- `/home/vimkim/.cache/cbrd27443-build-baseline-retry.log`
- `/home/vimkim/.cache/cbrd27443-testkit-preflight.txt`

Runtime evidence: `/home/vimkim/.cache/cbrd27443-present.ROrdHO`.
