from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
from collections import Counter
from datetime import date as calendar_date
import hashlib
import json
import re


parser = argparse.ArgumentParser(description="Check the CBRD-27881 candidate catalog and its document links.")
parser.add_argument("--jira-file", type=Path, help="Also check a local copy of the JIRA index.")
args = parser.parse_args()
root = Path(__file__).resolve().parent
catalog_path = root / "refactoring-candidates.md"
catalog = catalog_path.read_text()
historical = root / "CBRD-27881-oos-refactoring-candidates_dcbf09e_claude.md"
snapshot = root / "survey-2026-11-11.md"
structural = root / "structure-survey.md"
original_ids = set(re.findall(r"\bR-\d+\b", historical.read_text()))
new_ids = set(re.findall(r"\bN-20261111-\d+\b", snapshot.read_text()))
assert len(original_ids) == 68 and len(new_ids) == 2, "Source candidate inventory changed."
structural_ids = set(re.findall(r"^### (N-\d{8}-\d+)\.", structural.read_text(), re.MULTILINE))
assert structural_ids == {"N-20261111-03"}, "Structural survey candidate inventory changed."
expected = original_ids | new_ids | structural_ids
headings = re.findall(r"^### \[(\d{4}-\d{2}-\d{2})\] (R-\d+|N-\d{8}-\d+) (.+)$", catalog, re.MULTILINE)
counts = Counter(ident for date, ident, title in headings)
assert expected == set(counts) and all(count == 1 for count in counts.values()), "Candidate headings differ from source inventories or a heading is repeated."
for date, ident, title in headings:
    calendar_date.fromisoformat(date)
    if ident in expected:
        expected_date = "2026-11-03" if ident in original_ids else "2026-11-11"
        assert date == expected_date, (ident, "First-recorded date differs from the source report.")
    assert catalog.count(f'<a id="{ident.lower()}"></a>') == 1, (ident, "Stable anchor is missing or repeated.")
    assert catalog.count(f"| [{ident}](#{ident.lower()}) |") == 1, (ident, "Index row is missing or repeated.")
    assert title.strip(), (ident, "Candidate title is empty.")
index_ids = re.findall(r"^\| \[(R-\d+|N-\d{8}-\d+)\]\(#", catalog, re.MULTILINE)
assert Counter(index_ids) == counts, "Index entries differ from candidate headings."

preserved_body = snapshot.read_text().split("## 보존한 조사 본문\n", 1)[1]
assert hashlib.sha256(preserved_body.encode()).hexdigest() == "564378eab7f12410fdf3f6b1426d54eabef570da54fd07897bb41c13cd0a478f", "The preserved JIRA analysis changed."
assert "최초 기록일" in catalog and "실제 최초 발견 시각" in catalog, "Date provenance is missing."

documents = [catalog_path, snapshot, structural, root / "README.md"]
if args.jira_file:
    documents.append(args.jira_file.resolve())
checked_links = 0
for document in documents:
    text = document.read_text()
    assert "dev2.baboon-rudd.ts.net" not in text.lower(), (document, "Personal viewer URL in shared material.")
    assert len(re.findall(r"^# ", text, re.MULTILINE)) == 1, (document, "Expected one document title.")
    for link in re.findall(r"\]\(([^\s)]+)\)", text):
        parsed = urlsplit(link)
        if parsed.netloc == "github.com" and parsed.path.startswith("/vimkim/my-cubrid-docs/blob/main/cbrd-27881/"):
            relative = parsed.path.split("/cbrd-27881/", 1)[1]
            destination = root / unquote(relative)
        elif parsed.scheme or parsed.netloc:
            continue
        else:
            destination = document.parent / unquote(parsed.path) if parsed.path else document
        destination = destination.resolve()
        assert destination.is_file(), (document, link, "Missing destination.")
        if parsed.fragment:
            body = destination.read_text()
            anchors = set(re.findall(r'<a (?:id|name)="([^"]+)"', body))
            headings_in_target = re.findall(r"^#{1,6} (.+)$", body, re.MULTILINE)
            for heading in headings_in_target:
                anchor = re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")
                anchors.add(anchor)
            assert unquote(parsed.fragment) in anchors, (document, link, "Missing anchor.")
        checked_links += 1

print(json.dumps({"status": "PASS", "candidate_count": len(counts), "dated_titles": len(headings), "checked_links": checked_links, "preserved_analysis_sha256": hashlib.sha256(preserved_body.encode()).hexdigest()}))
