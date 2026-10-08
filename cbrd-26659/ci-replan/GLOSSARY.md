# Developer-owned OOS regression work

Terms for developer-created SQL and shell regression coverage. Canonical storage terms remain defined in [the normative OOS context](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md) and the repository's existing [CUBRID vocabulary](../../CONTEXT.md).

## Language

**Coverage inventory**:
The complete list of relevant OOS behaviors and the evidence and disposition associated with each behavior. An inventory entry does not by itself establish verified coverage.
_Avoid_: Passing suite when referring to the inventory

**Delivered OOS suite**:
The SQL and shell cases selected for integration into company CI under CBRD-26659. Existing unit tests and historical campaign probes may support its design without being delivered cases.
_Avoid_: Entire OOS issue graph when referring to executable selected cases

**Validation configuration**:
One recorded set of execution conditions used to validate a selected testcase set. SQL and shell have separate local executions and timing reports.
_Avoid_: Combined timing limit when referring to this work's separate runtime guidance

**CI-ready testcase delivery**:
A delivered OOS suite whose selected cases pass under the required validation configurations. A documented engine defect remains a coverage disposition until its correct testcase passes.
_Avoid_: Campaign acceptance when referring to a CI-ready delivery, because the historical campaign allowed documented failures
