# CBRD-27014 — OOS 발표자료 (PPT A)

Presentation deliverables for JIRA [CBRD-27014] "[OOS] [M2] [Survey] 김박사님
미팅 + 워크샵 발표자료 작성" (parent epic: CBRD-26583, OOS M2).

**PPT A** = technical design-review deck for the 김박사님 (DB expert) meeting on
**2026-07-13**: slide deck covering OOS problem definition, TOAST/InnoDB survey,
storage model, record format (incl. VOT entry detail), largest-first demotion,
read path, lifecycle/vacuum/bestspace, performance scenarios S1–S7, risks, and
feedback questions. Korean prose with English technical terms. No slide-count
constraint — add slides freely when content needs them.

**PPT B** (company-wide workshop deck, 2026-07-17) is a separate deliverable,
not in this directory yet.

## Code Base

/home/vimkim/gh/cb/oos-storage

Above is the src path to CUBRID feat/oos branch. You can search there for actual implementation.

## Files

| File | Role |
|------|------|
| `pptA-oos-review.html` | **Source of truth.** Slide markup (`<section class="slide">` blocks); links deck.css/deck.js. Presentable in a browser (HTTP server or file://): arrow keys / click to navigate; `?flat=1&slide=N` renders one slide at exact 1280×720 for screenshots. |
| `deck.css` | Deck styling, linked from pptA-oos-review.html. |
| `deck.js` | Navigation, fit-to-window scaling, and flat-mode JS, linked from pptA-oos-review.html. |
| `cubrid-logo.svg`, `cubrid-logo-dark.svg` | CUBRID logo (Wikimedia Commons) and its white-wordmark variant for dark slides (used on the title and closing slides). |
| `pptA-oos-review.pptx` | Generated 16:9 PPTX for submission — each slide is a full-bleed 2× PNG render (not text-editable). |
| `export_pptx.sh` | Regenerates the PPTX by screenshotting pptA-oos-review.html. Uses Playwright's cached headless Chromium + `uv run --with python-pptx`. |
| `justfile` | `just pptx` (regenerate), `just open` (view HTML deck). |
| `my-review-*.md` | The author's review feedback rounds, applied to the deck in numbered order. |

## Workflow rules

- Edit `pptA-oos-review.html`, `deck.css`, `deck.js`; never hand-edit the
  generated `pptA-oos-review.pptx`. No build step for the HTML — edit and
  refresh the browser.
- **Do NOT regenerate the PPTX yourself** — the owner runs `just pptx` when they
  want to. Just report which slides changed.
- Review loop: feedback arrives as `my-review-N.md`; apply each item, then note
  anything intentionally skipped.

## Content accuracy guardrails

- Present the **current** feat/oos spec only: `DB_PAGESIZE/4` record gate,
  `OR_OOS_INLINE_SIZE` (16B) column floor, largest-first demotion + early stop,
  16B OOS OID (volid/pageid/slotid/full_length). Never cite the old
  `DB_PAGESIZE/8` / 512B M1 policy as current.
- Performance numbers are **TBD placeholders** (the performance-results slide) —
  the owner measures and supplies real values; never invent them.
- Do not describe unimplemented features as existing (no compression, no OOS
  OID reuse on UPDATE, no PEEK mode). One OOS OID is referenced by exactly one
  record — never imply sharing.
- Display label is "Record Header" (not "MVCC Header"); keep code identifiers
  like `OR_MVCC_FLAG_HAS_OOS` verbatim.
- Knowledge base: `/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md` is the
  spec/terminology reference for all slide content.
