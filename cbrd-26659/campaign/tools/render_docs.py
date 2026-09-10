#!/usr/bin/env python3
"""Render the generated blocks of the ticket 12 Markdown documents from the JSON sources.

The catalogue document and the schemas document each contain blocks delimited by
``<!-- BEGIN GENERATED: <name> -->`` and ``<!-- END GENERATED: <name> -->``. This script
replaces the content between the markers from catalogue/requirements.json,
catalogue/scenario-map.json and schemas/*.schema.json so the prose and the data never
drift. ``--check`` exits 1 when a document is stale instead of rewriting it.

Usage: python3 tools/render_docs.py [--check]   (from cbrd-26659/campaign/)
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from minischema import resolve_ref  # noqa: E402

CAMPAIGN = Path(__file__).resolve().parent.parent
CATALOGUE_DOC = CAMPAIGN / "CBRD-26659-requirement-catalogue_f4299ac_claude.md"
SCHEMAS_DOC = CAMPAIGN / "CBRD-26659-traceability-schemas_f4299ac_claude.md"
FAMILIES = ["Representation", "SQL operations", "Read paths", "Schema and utilities",
            "Concurrent lifetime", "Durability", "Operational features", "Resource pressure"]
STATUSES = ["assertable", "observation-only", "UNSUPPORTED", "BLOCKED"]


def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


# --- catalogue document blocks ------------------------------------------------------------
def block_summary(cat):
    reqs = cat["requirements"]
    def tally(subset):
        return [sum(1 for r in subset if r["status"] == status) for status in STATUSES]

    rows = []
    for fam in FAMILIES:
        fam_reqs = [r for r in reqs if r["family"] == fam]
        rows.append([fam, len(fam_reqs)] + tally(fam_reqs))
    rows.append(["**Total**", len(reqs)] + tally(reqs))
    return table(["Family", "Requirements"] + STATUSES, rows)


def block_requirements(cat):
    parts = []
    for fam in FAMILIES:
        fam_reqs = [r for r in cat["requirements"] if r["family"] == fam]
        parts.append(f"#### {fam}\n")
        parts.append(table(["ID", "Title", "Status", "Policy", "Seam", "Citation"],
                           [[f"`{r['id']}`", r["title"], r["status"], r["authority"]["policy"], r["seam"],
                             f"{r['citation']['kind']}: {r['citation']['source']}"] for r in fam_reqs]))
        parts.append("")
        for r in fam_reqs:
            parts.append(f"**`{r['id']}` — {r['title']}** ({r['status']}, {r['authority']['policy']})  ")
            parts.append(r["statement"] + "\n")
            parts.append(f"- Authority: {r['authority']['note']}")
            if r["authority_question"]:
                parts.append(f"- Authority question: {r['authority_question']}")
            if r["accepted_design"]:
                parts.append(f"- Accepted design absent at the pin: {r['accepted_design']}")
            if r["pinned_observation"]:
                parts.append(f"- Pinned observation (ticket 11): {r['pinned_observation']}")
            if r["configuration_scope"]:
                parts.append(f"- Configuration scope: {r['configuration_scope']}")
            if r["attack_dimensions"]:
                parts.append("- Attack dimensions: " + "; ".join(r["attack_dimensions"]))
            if r["expected_engine_findings"]:
                parts.append("- Expected engine findings: " + ", ".join(r["expected_engine_findings"]))
            if r["related"]:
                parts.append("- Related: " + ", ".join(f"`{x}`" for x in r["related"]))
            parts.append("")
    return "\n".join(parts).rstrip()


def block_unimplemented(cat):
    rows = [[f"`{r['id']}`", r["title"], r["status"], r["accepted_design"], r["pinned_observation"] or "—"]
            for r in cat["requirements"] if r["status"] == "UNSUPPORTED"]
    return table(["ID", "Title", "Status", "Accepted design", "Pinned observation"], rows)


def block_spec_gaps(cat):
    rows = [[f"`{r['id']}`", r["title"], r["specification_gap_topic"], r["authority_question"]]
            for r in cat["requirements"] if r["status"] == "BLOCKED"]
    return table(["ID", "Title", "Topic", "Authority question"], rows)


def block_policy(cat):
    rows = []
    for policy in ["assert", "assert-after-eligibility", "observe", "withhold"]:
        ids = [f"`{r['id']}`" for r in cat["requirements"] if r["authority"]["policy"] == policy]
        rows.append([policy, len(ids), ", ".join(ids)])
    return table(["Policy", "Count", "Requirements"], rows)


def block_scenarios(smap):
    rows = [[s["scenario"], s["title"], ", ".join(f"`{x}`" for x in s["requirements"]) or "—",
             (s["exclusion"] or {}).get("reason", "—"), s["note"] or ""]
            for s in smap["scenarios"]]
    return table(["§6 scenario", "Title", "Requirement IDs", "Exclusion", "Note"], rows)


# --- schemas document blocks --------------------------------------------------------------
def resolve(schema, root, _depth=0):
    """Inline same-document $refs, letting sibling keywords override the target."""
    while "$ref" in schema:
        if _depth > 20:
            raise SystemExit(f"$ref chain too deep at {schema['$ref']!r}")
        merged = dict(resolve_ref(root, schema["$ref"]))
        merged.update({k: v for k, v in schema.items() if k != "$ref"})
        schema, _depth = merged, _depth + 1
    return schema


def type_of(schema, root):
    schema = resolve(schema, root)
    if "enum" in schema:
        return "enum: " + ", ".join("null" if v is None else f"`{v}`" for v in schema["enum"])
    if "const" in schema:
        return f"const `{schema['const']}`"
    if "anyOf" in schema:
        return " or ".join(type_of(s, root) for s in schema["anyOf"])
    t = schema.get("type", "any")
    if isinstance(t, list):
        t = "/".join(t)
    if t == "array" and "items" in schema:
        return f"array of {type_of(schema['items'], root)}"
    if "pattern" in schema:
        return f"{t} `{schema['pattern']}`"
    return t


def walk(schema, root, prefix, rows):
    """Append one table row per property, descending into objects and array items.

    Conditional requirements (allOf / if / then) are deliberately not walked; the
    Required column shows only unconditional `required` membership, and the
    schemas document lists the conditional rules in prose.
    """
    schema = resolve(schema, root)
    props = schema.get("properties", {})
    required = set(schema.get("required", []))
    for key, sub in props.items():
        path = f"{prefix}.{key}" if prefix else key
        sub_r = resolve(sub, root)
        description = sub.get("description") or sub_r.get("description") or ""
        rows.append([f"`{path}`", type_of(sub, root),
                     "yes" if key in required else "no", description])
        target = sub_r
        if "anyOf" in sub_r:
            branches = [resolve(branch, root) for branch in sub_r["anyOf"]]
            objs = [b for b in branches if b.get("type") == "object" or "properties" in b]
            target = objs[0] if objs else {}
        if target.get("type") == "array" and "items" in target:
            items = resolve(target["items"], root)
            if "properties" in items:
                walk(items, root, path + "[]", rows)
        elif "properties" in target:
            walk(target, root, path, rows)
        if "additionalProperties" in sub_r and isinstance(sub_r["additionalProperties"], dict):
            rows.append([f"`{path}.*`", type_of(sub_r["additionalProperties"], root), "no", "keyed entries"])


def block_schema(name):
    root = load(CAMPAIGN / "schemas" / f"{name}.schema.json")
    rows = []
    walk(root, root, "", rows)
    head = f"**{root['title']}** — {root['description']}\n\n"
    return head + table(["Field", "Type", "Required", "Meaning"], rows)


def blocks():
    cat = load(CAMPAIGN / "catalogue" / "requirements.json")
    smap = load(CAMPAIGN / "catalogue" / "scenario-map.json")
    return {
        CATALOGUE_DOC: {
            "summary": block_summary(cat),
            "policy": block_policy(cat),
            "requirements": block_requirements(cat),
            "unimplemented": block_unimplemented(cat),
            "spec-gaps": block_spec_gaps(cat),
            "scenarios": block_scenarios(smap),
        },
        SCHEMAS_DOC: {
            "schema-manifest": block_schema("manifest"),
            "schema-matrix": block_schema("matrix"),
            "schema-attempt-record": block_schema("attempt-record"),
            "schema-replay-bundle": block_schema("replay-bundle"),
            "schema-requirement": block_schema("requirement"),
            "schema-scenario-map": block_schema("scenario-map"),
        },
    }


def apply(text, name, content):
    marker = re.escape(name)
    pattern = re.compile(rf"(<!-- BEGIN GENERATED: {marker} -->\n).*?(\n<!-- END GENERATED: {marker} -->)",
                         re.S)
    if not pattern.search(text):
        raise SystemExit(f"marker block {name!r} not found")
    return pattern.sub(lambda m: m.group(1) + content + m.group(2), text)


def render(check_only=False):
    stale = []
    for doc, named in blocks().items():
        original = doc.read_text(encoding="utf-8")
        updated = original
        for name, content in named.items():
            updated = apply(updated, name, content)
        if updated != original:
            if check_only:
                stale.append(doc.name)
            else:
                doc.write_text(updated, encoding="utf-8")
                print(f"rendered {doc.name}")
    return stale


if __name__ == "__main__":
    if "--check" in sys.argv:
        stale = render(check_only=True)
        if stale:
            print("STALE: " + ", ".join(stale))
            sys.exit(1)
        print("fresh")
    else:
        render()
