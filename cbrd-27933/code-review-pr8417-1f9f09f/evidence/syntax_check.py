import json, sys, subprocess, shlex
build, = sys.argv[1:2]
want = sys.argv[2:]
db = json.load(open(build + "/compile_commands.json"))
rc_all = 0
for e in db:
    f = e["file"]
    if not any(f.endswith(w[0]) and w[1] in e.get("output", e["command"] if "command" in e else "") for w in [x.split(":") for x in want]):
        continue
    cmd = e.get("command") or " ".join(map(shlex.quote, e["arguments"]))
    args = shlex.split(cmd)
    # drop -o X and -c, add -fsyntax-only
    out = []
    skip = False
    for a in args:
        if skip: skip = False; continue
        if a == "-o": skip = True; continue
        if a == "-c": continue
        out.append(a)
    out.append("-fsyntax-only")
    r = subprocess.run(out, cwd=e["directory"], capture_output=True, text=True)
    print(f"{r.returncode} {build} {e.get('output','')} {f}")
    if r.stderr.strip(): print(r.stderr[-2000:])
    rc_all |= r.returncode
sys.exit(rc_all)
