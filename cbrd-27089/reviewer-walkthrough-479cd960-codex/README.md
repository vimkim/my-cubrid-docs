[Function inventory: statuses, explanations and direct calls](functions.en.md)

[Start here: short English guide](start-here.en.md) · [먼저 읽기: 한국어 안내](start-here.ko.html)

# PR7600 reviewer materials

- [Korean guided walkthrough](index.html): pr-walkthrough, four views, source links and guided tours.
- [Korean visual diff explanation](review.ko.html): visual-explainer, before/after ownership, source walkthrough, 28 new SQL test explanations and all 63 annotated diff hunks.
- [English source Markdown](review.en.md) and [Korean Markdown](review.ko.md).
- [Source and coverage manifest](evidence/manifest.json), [artifact verification](evidence/validation.json), [fact-check](evidence/fact-check.md).

Open the HTML files directly. D3 7.9.0 is embedded from its pinned official distribution; neither page needs a server or network for presentation. GitHub/JIRA evidence links require network. System font fallbacks support Korean; font appearance varies by machine.

The four English view/control labels are retained for the upstream validator; explanation text is Korean. Search, node selection, guided tours, zoom, pan and keyboard controls are available on the map. The reading page supports hunk search, code expansion and exact revision links. All added/deleted lines are retained; related lines are explained as semantic blocks.

The review's source baseline is feat/oos f4299ac0cd and head is 479cd960ec. No engine tests were run for document production. Historical results and disabled tests are labeled explicitly. This is a local artifact, not a merge approval or newly posted PR review.

Rebuild from the original checkout: `python3 .warp/pr-walkthrough/authoring/build.py` (Python Markdown required). Authoring English/Korean briefs and annotation data are retained. The installed skills are not modified. The renderer helper is loaded from the installed pr-walkthrough skill; its version/hash is captured in the installation manifest.
