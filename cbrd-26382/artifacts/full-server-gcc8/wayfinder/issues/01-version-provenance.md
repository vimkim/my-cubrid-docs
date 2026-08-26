# Version Provenance

Type: research
Status: resolved
Blocked by: none

## Question

Which source states represent the reported QA builds and which comparison
isolates PR #6636?

## Answer

The CUBRID build counter maps `11.5.0.2029` to `000a465c8`, `.2030` to
`6146cdb6a`, and `.2031` to `8fd3ca03e`. The 2029→2031 range includes the
CBRD-26266 optimizer change and PR #6636. Therefore only 2030→2031 isolates
PR #6636. Archived QA package manifests were not found, so the numeric-version
mapping must be reported as a source reconstruction caveat.

[Back to map](../map.md)

