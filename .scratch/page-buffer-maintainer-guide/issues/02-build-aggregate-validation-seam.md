# 02: Build the aggregate validation seam

**What to build:** Provide one validation entry point that discovers the entire maintainer-guide document set and proves its reader-visible Markdown, navigation, asset, language, and rendering contracts without relying on a manually maintained per-page command list.

**Blocked by:** 01: Align the authoring contract

**Status:** ready-for-agent

- [ ] One source of truth discovers the guide entry, learning pages, maintainer playbooks, advanced pages, and compact references.
- [ ] Every discovered Markdown document runs through the established Copyparty source checker.
- [ ] Relative links resolve both within the document set and into linked evidence outside it.
- [ ] Every displayed SVG resolves inside the root asset seam, exists, contains a responsive `viewBox`, and contains no active content.
- [ ] Every SVG owned by the document set is displayed by at least one page; orphan assets fail validation.
- [ ] Authored Markdown and SVG text are checked for unintended Korean prose without treating canonical identifiers as prose failures.
- [ ] The validation seam can request every page and displayed SVG through the local Copyparty server.
- [ ] When browser automation is available, rendered images must have nonzero natural dimensions and pages must have no relevant render error.
- [ ] When live-DOM validation is unavailable, the result reports that gate as unavailable instead of passing it implicitly.
- [ ] Existing validation prior art is deepened rather than replaced with unrelated checks.
- [ ] The current guide state remains valid while later pages are introduced.
