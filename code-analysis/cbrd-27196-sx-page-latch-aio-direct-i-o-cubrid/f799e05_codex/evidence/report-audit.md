# Independent Completeness Audit

- Reviewer: `codex-final-report-auditor-20260811-f799e05`
- Phase: `report`
- Round: `2`
- Timestamp UTC: `2026-08-11T06:16:52Z`
- Scope SHA-256: `db5ba3f0288fbb966ca5a4a832b420e7b5c582b461dc266ceda80a816c410885`
- Material basis: 최종 동결 뒤 `reportctl.py materials --phase report`가 산출한 131개 `reviewed_files`
- Raw digest validation: 각 파일을 직접 다시 읽어 SHA-256을 계산했으며 mismatch는 0건이다.
- Isolation note: 별도 reviewer task에서 원시 보고서와 pinned source를 독립 검토했다. 기존 audit의 verdict와 critique를 결론으로 사용하지 않았다. `isolated_reviewer=true`는 host trust boundary이며 암호학적 독립성 증명은 아니다.

## 결론

보고서는 18개 Coverage Obligation을 실질적으로 다루고, 현행 CUBRID snapshot-copy flush와 미래 frame/copy AIO 계약을 source fact, runtime observation, inference, unknown으로 구분한다. `READY WITHIN DECLARED SCOPE`는 현행 flush 재구성과 request-owned freeze Interface·total transition·conformance oracle에 한정되며, 미구현 대안의 처리량·공정성, public SX ABI, timing 또는 on-disk equivalence는 명시적으로 제외하거나 Unknown으로 남겼다.

최신 verifier의 비-audit 영역은 `provenance=[]`, `quiz_or_grill=[]`이다. 교체 전 audit narrative/seal만 최신 artifact와 맞지 않았으며, 이 audit이 최신 digest seal을 제공한다.

## Findings

1. **F-001 — Material/provenance seal**
   - Severity: `INFO`
   - Status: `RESOLVED`
   - Category: `provenance-and-artifact-integrity`
   - Location: `provenance.json`, `report.json`, `research/scope.md`, 전체 materials
   - Evidence: 최종 materials 131개를 raw bytes에서 재해시해 mismatch 0건을 확인했다. `report.json.status=REPORT_READY`이고 scope hash가 raw `research/scope.md` hash 및 `report.json.scope.sha256`과 일치한다. 세 repository revision과 baseline dirty fingerprints의 verifier 오류는 없다.
   - Remediation: 없음. 이후 material 변경 시 이 seal을 폐기하고 재감사해야 한다.

2. **F-002 — Overflow OID AS-IS/TO-BE 정확성**
   - Severity: `INFO`
   - Status: `RESOLVED`
   - Category: `cubrid-source-correctness`
   - Location: `chapters/06-policy.html#btree-overflow-oid-case`, `CUBRID-C016`~`CUBRID-C021`
   - Evidence:
     - literal `CREATE INDEX` bulk loader는 current overflow tail을 직접 연결하고, 후속 DML만 head부터 first-fit 탐색한다.
     - leaf의 첫 OID slotid `0x2000` flag와 record-tail head VPID, link 제거 시 VPID+flag 제거, overflow header의 단일 `next_vpid`, runtime 새 page의 head insertion이 pinned source와 일치한다.
     - DML helper는 overflow page를 한 장씩 WRITE fix하고 full이면 next VPID를 복사한 뒤 unfix한다. 동시에 보유하는 overflow latch는 최대 한 장이며 caller의 leaf WRITE는 계속 유지된다. 공간을 찾은 page는 WRITE-held 상태로 반환되고 같은 latch 아래 삽입되므로 post-return 공간 선점 race가 없다.
     - 한 호출의 worst case는 O(K)이지만 새 runtime head에 공간이 있는 common append는 O(1)에 가깝다. bulk-built partial tail, head-full 증설, 깊은 fragmentation의 긴 scan은 측정 전 inference로 제한했다.
     - unique index도 MVCC physical version 공존 시 overflow 경로를 사용할 수 있다는 설명이 unique relocation 및 CLASS_OID assertion과 일치한다.
     - SX→WRITE는 single SX, 신규 reader gate, 기존 reader drain, 무교착 latch order를 조건으로 한 eventual upgrade이며 즉시·무조건 성공으로 쓰지 않았다.
     - overflow-only SX는 O(K), fix/unfix, leaf WRITE 및 same-leaf writer serialization을 제거하지 않으며 표준 range scan의 leaf READ/insert leaf WRITE gate가 효과를 가릴 수 있음을 명시했다.
     - `bt_fix_ovf_oids`는 helper 전체 timer일 뿐 page별 fix 수, chain length 또는 latch wait 증거가 아니라는 제한도 ledger와 본문에 반영됐다.
   - Remediation: 없음.

3. **F-003 — PostgreSQL/MySQL non-equivalence와 학습 연결**
   - Severity: `INFO`
   - Status: `RESOLVED`
   - Category: `comparison-and-traceability`
   - Location: `chapters/08-postgresql.html`, `chapters/09-mysql.html`, `chapters/10-comparison.html`, `quiz/quiz-2/`
   - Evidence: PostgreSQL nbtree는 heap TID ordering과 bounded leaf-local posting tuple 및 EXCLUSIVE leaf insert를 사용하며 조사 범위에 SHARE_EXCLUSIVE insert나 SX→X API가 없다. InnoDB secondary index는 clustered-key columns를 포함한 개별 record와 X-latched leaf modification을 사용하고 tree/block SX는 구조 변경 coordination이다. 따라서 `CMP-C006`의 `no equivalent`와 호환성만의 `partial analogy` 구분이 타당하다. CUBRID-C016~C021, PG-C007, MYSQL-C007, CMP-C006의 report anchors가 모두 존재하며 Quiz 2는 AS-IS latch 흐름, held-page race, O(1)/O(K), conditional promotion, leaf gate와 남는 비용을 answer와 분리해 다룬다. overflow runtime 성능은 검증하지 않았다고 명시한다.
   - Remediation: 없음.

4. **F-004 — 전체 report readiness, Experiment 및 Quiz**
   - Severity: `INFO`
   - Status: `RESOLVED`
   - Category: `completeness-and-readiness`
   - Location: `report.json`, 모든 HTML, `evidence/claims.jsonl`, `experiments/experiment-1/`, `quiz/`
   - Evidence: 13개 Book HTML은 Korean language, unique title/h1/main, offline-only resource, local link/fragment 및 navigation 검사를 통과했다. 41개 Claim의 135개 report location이 모두 실제 anchor로 해석된다. 현행 flush의 ownership, lifecycle, concurrency, WAL/DWB recovery, failure, performance/observability, 세 DB 비교와 구현 청사진이 포함된다. Experiment는 pinned baseline build/tool snapshot과 direct `csql -i` runner 3회를 봉인하며 CUBRID-C006이 SQL runs, statdump before/after, backup trigger를 모두 연결하고 attribution 한계를 밝힌다. Quiz 두 개의 self-check는 성공했고 Quiz 2 state-model도 모든 terminal cleanup assertion을 통과한다. instrumentation은 사용하지 않았고 cleanup receipt는 DB·backup directory·watcher 부재를 확인한다.
   - Remediation: 없음.

## Coverage reviewed

`orientation`, `mental-model`, `scope-interface-seams`, `data-ownership-lifetime`,
`lifecycle-state-machines`, `core-workflows`, `concurrency`,
`storage-durability-recovery`, `policies-algorithms`, `errors-resource-pressure`,
`performance-observability`, `experimental-validation`, `postgresql-analysis`,
`mysql-analysis`, `cross-database-comparison`, `reimplementation-blueprint`,
`glossary-evidence-unknowns`, `teaching-map`.

VERDICT: APPROVED
