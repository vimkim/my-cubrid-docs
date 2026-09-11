Format and feasibility probes, run before the case's oracle was written
=======================================================================

These established how the channels the case parses actually look and behave. They are NOT
the source of any expected value: every expectation in expected-oracle.md is derived from
the engine's record accounting or computed from the byte pattern with md5sum, and would
have produced the same numbers with no engine available.

READ THIS BEFORE CITING THEM AS "FORMAT ONLY". probe_format.sh is not format-only: it used
a table of the same shape as the case's, with rows of exactly 4036 AA, 16284 BB and 4011
CC, applied the same EE update, crashed and restarted the server, and read back COUNT(*),
the three MD5 digests and SHOW HEAP OOS before and after recovery. It therefore showed the
engine's answer for this fixture before expected-oracle.md was written, which is why that
file's provenance claim was corrected: the oracle's independence rests on its derivation,
not on the ordering. Only probe_restart.sh and probe_restart2.sh used a deliberately
unrelated fixture. The lesson for the remaining tickets is in the oracle: probe format on
a fixture that is not the case's fixture.

What each one settled:

  probe_format.sh / probe-debug.txt
      the column layout of SHOW HEAP OOS OF <class>; that CUBRID's MD5 of a BIT VARYING
      digests its lowercase hex form (cross-checked against coreutils and Python, which
      agree); that DISK_SIZE reports the serialized length; and that with the default
      auto_restart_server=y the master restarts a killed server on its own, so the case
      must turn it off.

  probe_restart.sh / probe-restart.txt
      that with auto_restart_server=no the master keeps a stale registration: `cubrid
      server start` returns 0 while doing nothing and connections then fail -- and that
      csql exited 0 while printing "Failed to connect", which is why no assertion in the
      case trusts a csql exit status alone.

  probe_restart2.sh / probe-restart2.txt
      the crash protocol that does work: kill -9 the server, its cub_pl and the master
      together, then `cubrid server start`, which restarts the master and recovers.
      Also that csql exits 1 on a SQL error and on an unknown database.

  probe_fmt3.sh / probe-fmt3.txt
      the spacedb page-size line, the delimited extraction query the value assertions
      use, the awk field positions of the SHOW HEAP OOS row, and checkdb's output.

All four ran inside the campaign namespace against the pinned debug install, on databases
they created and deleted themselves. probe_restart.sh and probe_restart2.sh used a
one-row non-OOS fixture; probe_format.sh and probe_fmt3.sh used the case's own sizes, with
the consequence described above.
