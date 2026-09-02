# 01: Extend the Question-bank authoring and validation contract

**What to build:** Make the documentation contract and aggregate validation seam aware of the confirmed Question bank before reader-facing pages are added, with red tests for discovery and structural requirements.

**Blocked by:** Nothing

**Status:** ready-for-agent

- [ ] Update `AGENTS.md` and `maintainer-guide-notes.md` so `questions/` is a fifth reader mode and all ten approved Question-bank pages are aggregate-owned Evidence references.
- [ ] Preserve the confirmed English, pinned-baseline, canonical-ownership, evidence-label, asset, and Copyparty contracts.
- [ ] Extend the aggregate's single discovery seam recursively through `questions/`; all existing Markdown, link, language, asset, HTTP, and DOM gates consume that same discovered set.
- [ ] Add a focused Question-bank validator module or cohesive functions callable by the aggregate; do not fork page discovery.
- [ ] Add red tests for the exact ten-page topology, required prompt/answer fields, recognized routes/modes/evidence labels, canonical-ID syntax/uniqueness, prompt-answer pairing, controlled migration rows/counts, reader-intake digest preservation, and required navigation.
- [ ] Add negative aggregate fixtures proving a broken Question-bank link and Korean prose fail through normal aggregate discovery.
- [ ] Test behavior rather than incidental implementation or prose wrapping.
- [ ] Preserve unrelated worktree changes and do not edit the legacy banks or Reader question intake.
- [ ] Complete when the tests fail for missing Question-bank deliverables for the intended reason and all pre-existing tests remain green.

