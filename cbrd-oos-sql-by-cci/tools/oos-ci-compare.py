#!/usr/bin/env python3
"""Compare the failed cases of a feature/oos-merge gha-ci run against develop runs.

usage: oos-ci-compare.py OOS_RUN BASE_RUN [BASE_RUN ...] [--suites shell,sql,sql_by_cci,medium]

For each suite it reads <server>/runs/<run>/<suite>/collect/failed.list, then the
JUnit XML of every shard that failed. A failed OOS case is
  same      - a develop run fails the same case with the same diff
              (sets of +/- lines, whitespace collapsed; shell xtrace lines ignored),
  differs   - a develop run fails the case, but with another diff,
  oos-only  - no develop run fails the case.
Only 'differs' and 'oos-only' need a look. Exit status 1 when any exists.
"""
import re, sys, urllib.request, xml.etree.ElementTree as ET

SERVER = "http://192.168.1.48:30080"

def get(url):
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read()
    except Exception:
        return None

def failed(run, suite):
    body = get(f"{SERVER}/runs/{run}/{suite}/collect/failed.list")
    if body is None:
        return None
    out = {}
    for line in body.decode().splitlines():
        if "\t" in line:
            shard, case = line.split("\t", 1)
            out.setdefault(case, set()).add(shard)
    return out

def keyline(l):
    return re.sub(r"\s+", " ", l[1:]).strip()

def signatures(run, suite, shards):
    sigs = {}
    for shard in sorted(shards):
        base = f"{SERVER}/runs/{run}/{suite}/shard/{shard}/test-results/"
        index = get(base)
        if index is None:
            continue
        for name in re.findall(r'href="([^"]+\.xml)"', index.decode()):
            data = get(base + name)
            if data is None:
                continue
            for tc in ET.fromstring(data).iter("testcase"):
                f = tc.find("failure")
                if f is None:
                    f = tc.find("error")
                if f is None:
                    continue
                case = re.sub(r"^.*?/((sql|shell|medium)/)", r"\1", tc.get("name") or "")
                text = (f.text or "") + "\n" + (f.get("message") or "")
                lines = text.splitlines()
                if suite == "shell":
                    sig = frozenset(re.sub(r"\.c:\d+:", ".c:N:", l.strip())
                                    for l in lines if re.search(r"-\d+ : NOK", l))
                else:
                    sig = frozenset(("+" if l[0] in "+>" else "-") + keyline(l) for l in lines
                                    if l[:1] and l[0] in "+-<>" and not l.startswith(("+++", "---", "+ ")))
                sigs.setdefault(case, set()).add(sig)
    return sigs

def main():
    args = sys.argv[1:]
    suites = ["shell", "sql", "sql_by_cci", "medium"]
    if "--suites" in args:
        i = args.index("--suites"); suites = args[i + 1].split(","); del args[i:i + 2]
    if len(args) < 2:
        sys.exit(__doc__)
    oos, bases = args[0], args[1:]
    bad = False
    for suite in suites:
        mine = failed(oos, suite)
        if mine is None:
            print(f"== {suite}: no failed.list for run {oos} (suite not run?)"); continue
        base_lists = {b: failed(b, suite) for b in bases}
        used = [b for b, l in base_lists.items() if l is not None]
        print(f"== {suite}: {len(mine)} failed; baselines with this suite: {' '.join(used) or 'none'}")
        if not mine:
            continue
        my_sigs = signatures(oos, suite, set().union(*mine.values()))
        base_sigs = {}
        for b in used:
            shards = set().union(*[s for c, s in base_lists[b].items() if c in mine] or [set()])
            for c, s in signatures(b, suite, shards).items():
                base_sigs.setdefault(c, set()).update(s)
        for case in sorted(mine):
            if case not in base_sigs and not any(case in base_lists[b] for b in used):
                verdict = "oos-only"
            elif my_sigs.get(case, set()) & base_sigs.get(case, set()):
                verdict = "same"
            else:
                verdict = "differs"
            bad |= verdict != "same"
            print(f"  {verdict:8} {case}")
    sys.exit(1 if bad else 0)

if __name__ == "__main__":
    main()
