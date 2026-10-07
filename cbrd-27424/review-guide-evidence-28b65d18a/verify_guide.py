#!/usr/bin/env python3
"""Validate the delivered guide against committed code and its recorded receipts."""

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    evidence = Path(__file__).resolve().parent
    ticket = evidence.parent
    guide = ticket / "review-guide-pr7925-28b65d18a-ko.md"

    def git(*command):
        return subprocess.check_output(["git", *command], cwd=args.source)

    def anchors(path):
        return re.findall(r'<a id="([a-z0-9-]+)"></a>', path.read_text())

    guide_anchors = anchors(guide)
    assert len(guide_anchors) == len(set(guide_anchors))
    checked_links = []
    for document in (guide, ticket / "README.md", evidence / "source-map.md"):
        text = document.read_text()
        own_anchors = anchors(document)
        assert len(own_anchors) == len(set(own_anchors))
        for url in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', text):
            if url.startswith(("https://", "http://")):
                continue
            target, _, fragment = url.partition("#")
            target_path = document.parent / unquote(target) if target else document
            assert target_path.is_file() or target_path.resolve() == evidence / "verification.json", (document, url)
            if fragment:
                assert fragment in anchors(target_path), (document, url)
            checked_links.append({"file": str(document.relative_to(ticket)), "target": url})

    refs = json.loads((evidence / "source-references.json").read_text())
    for reference in refs:
        blob = git("show", reference["revision"] + ":" + reference["path"]).decode().splitlines()
        assert blob[reference["line"] - 1] == reference["text"], reference
        assert re.search(reference["pattern"], blob[reference["line"] - 1]), reference

    # Hosted source links in these documents are checked against available Git objects.
    hosted_links = []
    for document in (guide, evidence / "source-map.md"):
        for revision, path, number in re.findall(r'https://github.com/(?:CUBRID|vimkim)/cubrid/blob/([0-9a-f]{40})/([^\s)#]+)#L([0-9]+)', document.read_text()):
            blob = git("show", revision + ":" + path).decode().splitlines()
            assert 0 < int(number) <= len(blob), (revision, path, number)
            hosted_links.append({"revision": revision, "path": path, "line": int(number), "text": blob[int(number) - 1]})

    coverage = json.loads((evidence / "coverage.json").read_text())
    changed = set(git("diff", "--name-only", coverage["base"], coverage["head"]).decode().splitlines())
    assert changed == {entry["path"] for entry in coverage["files"]}
    for entry in coverage["files"]:
        assert set(entry["guide_anchors"]) <= set(guide_anchors)
        assert entry["head_blob"] == git("rev-parse", coverage["head"] + ":" + entry["path"]).decode().strip()
        assert entry["head_sha256"] == hashlib.sha256(git("show", coverage["head"] + ":" + entry["path"])).hexdigest()

    indexed = re.findall(r'^\| \[[^\]]+\]\(([^)]+)\) \|', (ticket / "README.md").read_text(), re.M)
    actual = {str(path.relative_to(ticket)) for path in ticket.rglob("*") if path.is_file()}
    # This validator's output is intentionally indexed before it is written.
    actual.add(str((evidence / "verification.json").relative_to(ticket)))
    assert Counter(indexed) == Counter(actual), (set(indexed) - actual, actual - set(indexed))

    receipt = json.loads((evidence / "integration-receipt.json").read_text())
    assert git("rev-parse", "HEAD").decode().strip() == receipt["integrated_head"]
    assert git("rev-parse", "HEAD^{tree}").decode().strip() == receipt["original_private_tree"]
    assert git("diff", "--ignore-submodules=all", "--name-only").decode().strip() == ""
    assert git("diff", "--cached", "--name-only").decode().strip() == ""
    for name, state in receipt["submodules"].items():
        assert git("rev-parse", "HEAD:" + name).decode().strip() == state["gitlink"]
        for filename, expected in state["modified_files"].items():
            assert hashlib.sha256((args.source / name / filename).read_bytes()).hexdigest() == expected

    results = json.loads((evidence / "ctest-results.json").read_text())
    assert results["source_commit"] == receipt["integrated_head"]
    assert results["gtests_run"] == results["gtests_passed"] == 374
    assert results["ctests"] == results["ctests_passed"] == 38
    assert not (results["failures"] or results["skips"] or results["disabled"])
    by_name = [case["name"] for case in results["cases"]]
    focused = {
        "comparison": [name for name in by_name if name.startswith(("OosWorkspaceBytes.", "EncodingAndVotBoundaries/"))],
        "utility": [name for name in by_name if name.startswith("OosWorkspaceTest.")],
        "dependency": [name for name in by_name if name.startswith(("OosSqlDeferredWrite.", "OosSqlPacking."))],
    }
    assert {key: len(value) for key, value in focused.items()} == {"comparison": 21, "utility": 13, "dependency": 36}

    output = {
        "verified_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "head": receipt["integrated_head"],
        "merge_base": coverage["base"],
        "changed_files_covered": len(changed),
        "source_references_checked": len(refs),
        "hosted_source_links_checked_against_git": len(hosted_links),
        "unique_guide_anchors": len(guide_anchors),
        "local_links_checked": len(checked_links),
        "readme_files_indexed": len(indexed),
        "ctest": {key: results[key] for key in ("ctests", "ctests_passed", "gtests_run", "gtests_passed", "elapsed_seconds")},
        "focused_case_counts": {key: len(value) for key, value in focused.items()},
        "source_and_user_cci_preserved": True,
        "scope_limits": ["Local source HEAD is unpublished; no exact-local-HEAD GitHub CI claim.", "Shared feature integration and partition acceptance remain pending.", "Prior benchmark evidence was inspected; no benchmark rerun.", "No XML collection claim for this run; verbose RUN/OK and binary summaries audited.", "Raw build/CTest logs retain native whitespace."],
        "command": "python3 cbrd-27424/review-guide-evidence-28b65d18a/verify_guide.py --source " + str(args.source),
    }
    (evidence / "verification.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
