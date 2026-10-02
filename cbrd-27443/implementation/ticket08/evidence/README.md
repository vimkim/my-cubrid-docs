# Final native evidence

Exact attempt: `/home/vimkim/.cache/cbrd27443-08.QVVajj`. Engine `0809a480df55ac6767a905d03fa3d31edd40a93c`; tests `6bdbb89738088948c479a6d85662276126a31bb5`.

Native artifacts establish four selected/executed/passing cases, zero failures and skips. The main independently reran the focused verifier and checked 2,566 matrix assertions, nine supplemental observations, 179 background captures plus one intentional PID1 foreground capture, the separate present probe, twelve fresh logging-fault records, fifteen replicated rows, eighteen installed/native-copy pairs and 252 actual fixture files. `main-independent-audit.json` records that audit; `main-audit.py` makes its checks reproducible against the retained attempt.

`all-assertions.json` and `observations.json` preserve verdicts and relevant actual observations. Strings longer than 8,192 characters in observations are represented by UTF-8 byte length, SHA-256 and 1,024-character prefix/suffix; full output remains in the original attempt. This compaction does not change assertions or counts. `safe-summary.json` is the worker's independent audit output. Raw config and full runtime volumes remain in the retained attempt; `config-identity.json` binds the effective configuration.

The main audit initially used `hashlib.file_digest`, unavailable in system Python; streaming SHA-256 corrected that audit-only compatibility issue. Native execution and testcase bytes were unchanged. Both audit implementations account explicitly for master cleanup snapshot lists and the intentionally attached PID1 supervisor streams. These schema distinctions are not exemptions for background services.

`run-verdict.log` retains the native selection, dispatch and final verdict section. The unrelated initial host/environment inventory is omitted from this archive; the complete original `run.log` remains in the attempt (SHA-256 `34cef429e60cfa9b25b890dae304df9e07fb188e40709628c22ba38e612aa06a`).
