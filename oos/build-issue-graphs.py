#!/usr/bin/env python3
"""Render oos/issue-graphs.html from oos/issue-graphs.json with Graphviz dot."""

import html
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "issue-graphs.json"
OUT = HERE / "issue-graphs.html"

STATES = {
    "goal": "병합 목표",
    "decision": "결정 필요",
    "ready": "리뷰 요청 준비",
    "inreview": "리뷰 중",
    "triage": "Triage 대기",
    "wip": "작업 중",
    "todo": "착수 전",
    "deferred": "보류",
    "external": "다른 담당자",
    "done": "완료",
}
OPEN_STATES = ("decision", "ready", "inreview", "triage", "wip", "todo")
STYLES = {"goal": "rounded,filled,bold", "issue": "filled", "pr": "rounded,filled", "decision": "rounded,filled,dashed"}
EDGE_TYPES = {
    "blocks": ("선행 필수", 'penwidth=2.2 arrowsize=0.9'),
    "decision": ("결정 대기", 'penwidth=2.2 arrowsize=0.9'),
    "order": ("계획 순서", 'style=dashed penwidth=1.4 arrowsize=0.8'),
    "conflict": ("함께 검증", 'style=dotted penwidth=2 dir=none constraint=false'),
}
GATING = {"blocks", "decision"}
SANS = "Noto Sans CJK KR"
MONO = "DejaVu Sans Mono"


def fail(msg):
    sys.exit(f"issue-graphs.json: {msg}")


def load():
    data = json.loads(DATA.read_text())
    nodes = data["nodes"]
    for nid, n in nodes.items():
        if n.get("state") not in STATES:
            fail(f"{nid}: unknown state {n.get('state')!r}")
        if n.get("kind") not in STYLES:
            fail(f"{nid}: unknown kind {n.get('kind')!r}")
        for field in ("title", "summary", "next"):
            if not n.get(field):
                fail(f"{nid}: missing {field}")
    seen = set()
    for e in data["edges"]:
        for end in ("from", "to"):
            if e[end] not in nodes:
                fail(f"edge {e['from']} -> {e['to']}: unknown node {e[end]}")
        if e["type"] not in EDGE_TYPES:
            fail(f"edge {e['from']} -> {e['to']}: unknown type {e['type']}")
        if not e.get("why") or not e.get("evidence"):
            fail(f"edge {e['from']} -> {e['to']}: missing why or evidence")
        key = (e["from"], e["to"], e["type"])
        if key in seen:
            fail(f"duplicate edge {key}")
        seen.add(key)
    for view in data["views"]:
        for group in view["groups"]:
            for nid in group["nodes"]:
                if nid not in nodes:
                    fail(f"view {view['id']}: unknown node {nid}")
    return data


def units(ch):
    return 2 if ord(ch) > 0x2E80 else 1


def wrap(text, width=34):
    lines, line, used = [], "", 0
    for word in text.split(" "):
        w = sum(units(c) for c in word)
        if line and used + 1 + w > width:
            lines.append(line)
            line, used = word, w
        else:
            line = f"{line} {word}" if line else word
            used += w + (1 if used else 0)
    lines.append(line)
    return lines


def esc(text):
    return html.escape(text, quote=True)


def node_label(nid, n):
    head = esc(n.get("label", nid))
    slot = f'<FONT FACE="{MONO}" POINT-SIZE="9.5">{esc(n["slot"])}</FONT>' if n.get("slot") else " "
    title = "<BR ALIGN=\"LEFT\"/>".join(esc(x) for x in wrap(n["title"]))
    meta = esc(" · ".join(filter(None, [n.get("prs_label"), STATES[n["state"]]])))
    return (
        '<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="1">'
        f'<TR><TD ALIGN="LEFT"><FONT FACE="{MONO}" POINT-SIZE="10.5"><B>{head}</B></FONT></TD>'
        f'<TD ALIGN="RIGHT">{slot}</TD></TR>'
        f'<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT FACE="{SANS}" POINT-SIZE="11.5">{title}<BR ALIGN="LEFT"/></FONT></TD></TR>'
        f'<TR><TD COLSPAN="2" ALIGN="LEFT"><FONT FACE="{SANS}" POINT-SIZE="9">{meta}</FONT></TD></TR>'
        "</TABLE>>"
    )


def split_view(view, data):
    members = {nid for g in view["groups"] for nid in g["nodes"]}
    edges = [i for i, e in enumerate(data["edges"]) if e["from"] in members and e["to"] in members]
    linked = {data["edges"][i][end] for i in edges for end in ("from", "to")}
    return edges, members - linked


def dot_source(view, data):
    nodes = data["nodes"]
    edges, loose = split_view(view, data)
    out = [
        "digraph G {",
        f'graph [rankdir={view.get("rankdir", "LR")} nodesep=0.28 ranksep=0.55 fontname="{SANS}" '
        'fontsize=11 compound=true newrank=true pad=0.1]',
        f'node [fontname="{SANS}" margin="0.12,0.06"]',
        f'edge [fontname="{SANS}"]',
    ]
    for gi, group in enumerate(view["groups"]):
        body = []
        for nid in (x for x in group["nodes"] if x not in loose):
            n = nodes[nid]
            body.append(
                f'"{nid}" [id="n-{nid}" class="node-{n["kind"]} st-{n["state"]}" '
                f'shape=box style="{STYLES[n["kind"]]}" label={node_label(nid, n)} tooltip="{esc(n["title"])}"]'
            )
        if group.get("label") and body:
            out.append(f'subgraph cluster_{gi} {{ id="c-{view["id"]}-{gi}" class="cluster-{group.get("tone", "plain")}" '
                       f'label="{esc(group["label"])}" labeljust=l fontsize=11 style="rounded" margin=12')
            out.extend(body)
            out.append("}")
        else:
            out.extend(body)
    for i in edges:
        e = data["edges"][i]
        out.append(f'"{e["from"]}" -> "{e["to"]}" [id="e-{i}" class="edge-{e["type"]}" '
                   f'{EDGE_TYPES[e["type"]][1]} tooltip="{esc(e["why"])}"]')
    out.append("}")
    return "\n".join(out)


def loose_html(view, data):
    _, loose = split_view(view, data)
    if not loose:
        return ""
    rows = []
    for group in view["groups"]:
        ids = [nid for nid in group["nodes"] if nid in loose]
        if not ids:
            continue
        items = "".join(
            f'<li data-node="{nid}"><button type="button" class="jump" data-node="{nid}">{esc(data["nodes"][nid].get("label", nid))}</button>'
            f'<span>{esc(data["nodes"][nid]["title"])}</span>'
            f'<span class="loose-meta">{esc(" · ".join(filter(None, [data["nodes"][nid].get("slot"), data["nodes"][nid].get("prs_label")])))}</span>'
            f'{chip(data["nodes"][nid]["state"])}</li>' for nid in ids)
        rows.append(f'<div class="loose-group"><h3>{esc(group.get("label", "기타"))}</h3><ul>{items}</ul></div>')
    return (f'<div class="loose"><p class="muted small">이 그래프 안에서 다른 항목과 선후 관계가 없는 항목입니다. '
            f'누르면 상세 패널에 내용을 보여줍니다.</p>{"".join(rows)}</div>')


def render_svg(view, data):
    src = dot_source(view, data)
    run = subprocess.run(["dot", "-Tsvg"], input=src, capture_output=True, text=True)
    if run.returncode:
        fail(f"view {view['id']}: dot failed\n{run.stderr}")
    svg = run.stdout[run.stdout.index("<svg"):]
    svg = re.sub(r"<!--.*?-->\n?", "", svg, flags=re.S)
    svg = re.sub(r'<polygon fill="white" stroke="transparent"[^>]*/>\n', "", svg, count=1)
    m = re.match(r'<svg width="([\d.]+)pt" height="([\d.]+)pt"', svg)
    w, h = (round(float(x) * 4 / 3) for x in m.groups())
    svg = re.sub(r'^<svg width="[\d.]+pt" height="[\d.]+pt"',
                 f'<svg class="graph" data-view="{view["id"]}" width="{w}" height="{h}" role="img" '
                 f'aria-label="{esc(view["title"])}"', svg)
    svg = svg.replace(f'font-family="{MONO}"', 'class="t-mono"').replace(f'font-family="{SANS}"', 'class="t-sans"')
    svg = re.sub(r'<g id="a_[^"]*"><a xlink:title="[^"]*">\n?(.*?)</a>\n?</g>', r"\1", svg, flags=re.S)
    return svg


def relations(data):
    up = {nid: [] for nid in data["nodes"]}
    down = {nid: [] for nid in data["nodes"]}
    for e in data["edges"]:
        up[e["to"]].append(e)
        down[e["from"]].append(e)
    return up, down


def startable(data, up):
    by_state = {s: [] for s in OPEN_STATES}
    for nid, n in data["nodes"].items():
        if n["state"] not in by_state:
            continue
        gates = [e for e in up[nid] if e["type"] in GATING and data["nodes"][e["from"]]["state"] != "done"]
        if not gates:
            by_state[n["state"]].append(nid)
    return {s: ids for s, ids in by_state.items() if ids}


def ready_html(data, ready):
    rows = []
    for state, ids in ready.items():
        buttons = " ".join(
            f'<button type="button" class="jump" data-node="{nid}" title="{esc(data["nodes"][nid]["title"])}">'
            f'{esc(data["nodes"][nid].get("label", nid))}</button>' for nid in ids)
        rows.append(f"<li>{chip(state)}<span class=\"jumps\">{buttons}</span></li>")
    return "".join(rows)


def link(n, nid):
    url = n.get("url")
    text = esc(n.get("label", nid))
    return f'<a href="{esc(url)}">{text}</a>' if url else text


def chip(state):
    return f'<span class="chip st-{state}">{STATES[state]}</span>'


def rel_list(edges, end, data):
    if not edges:
        return '<span class="muted">없음</span>'
    items = []
    for e in edges:
        other = data["nodes"][e[end]]
        items.append(f'<li><span class="et et-{e["type"]}">{EDGE_TYPES[e["type"]][0]}</span> '
                     f'<button type="button" class="jump" data-node="{e[end]}">{esc(other.get("label", e[end]))}</button></li>')
    return '<ul class="rel">' + "".join(items) + "</ul>"


def table_rows(data, up, down):
    order = list(STATES)
    rows = []
    for nid, n in sorted(data["nodes"].items(), key=lambda kv: (order.index(kv[1]["state"]), kv[1].get("sort", ""), kv[0])):
        rows.append(
            f'<tr id="row-{nid}" data-node="{nid}"><td class="mono">{link(n, nid)}</td>'
            f'<td><strong>{esc(n["title"])}</strong><br><span class="muted">{esc(n["summary"])}</span></td>'
            f'<td>{chip(n["state"])}<br><span class="muted small">{esc(n.get("jira", ""))}</span></td>'
            f'<td>{esc(n["next"])}</td>'
            f'<td>{rel_list(up[nid], "from", data)}</td>'
            f'<td>{rel_list(down[nid], "to", data)}</td></tr>'
        )
    return "\n".join(rows)


def legend(data):
    used = {n["state"] for n in data["nodes"].values()}
    states = "".join(f'<li>{chip(s)}</li>' for s in STATES if s in used)
    edges = "".join(
        f'<li><svg width="46" height="12" aria-hidden="true"><line class="lg-{t}" x1="2" y1="6" x2="44" y2="6"/></svg>'
        f'{label}</li>' for t, (label, _) in EDGE_TYPES.items())
    return f'<ul class="legend">{states}</ul><ul class="legend">{edges}</ul>'


def main():
    data = load()
    up, down = relations(data)
    ready = startable(data, up)
    views = []
    for view in data["views"]:
        views.append(
            f'<section class="view" id="{view["id"]}"><header class="view-head"><h2>{esc(view["title"])}</h2>'
            f'<p>{esc(view["summary"])}</p></header>'
            f'<div class="canvas-wrap"><div class="canvas-col"><div class="canvas">{render_svg(view, data)}</div>{loose_html(view, data)}</div>'
            f'<aside class="panel" data-view="{view["id"]}" aria-live="polite"><p class="muted">노드를 누르면 선행 이슈와 풀리는 이슈를 표시합니다.</p></aside></div></section>'
        )
    client = {
        "nodes": data["nodes"],
        "edges": data["edges"],
        "states": STATES,
        "edgeTypes": {k: v[0] for k, v in EDGE_TYPES.items()},
    }
    template = (HERE / "issue-graphs.template.html").read_text()
    page = (template
            .replace("{{AS_OF}}", esc(data["as_of"]))
            .replace("{{INTRO}}", data["intro_html"])
            .replace("{{SOURCES}}", "".join(f"<li>{s}</li>" for s in data["sources_html"]))
            .replace("{{READY}}", ready_html(data, ready))
            .replace("{{LEGEND}}", legend(data))
            .replace("{{VIEWS}}", "\n".join(views))
            .replace("{{ROWS}}", table_rows(data, up, down))
            .replace("{{DATA}}", json.dumps(client, ensure_ascii=False).replace("</", "<\\/")))
    OUT.write_text(page)
    print(f"wrote {OUT.relative_to(HERE.parent)}: {len(data['nodes'])} nodes, {len(data['edges'])} edges, "
          f"{len(views)} views, {sum(map(len, ready.values()))} startable")


if __name__ == "__main__":
    main()
