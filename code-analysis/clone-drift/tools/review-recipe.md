# Drifted-clone review recipe (shared by all workers; do not edit)

Goal of the whole audit: find real bugs in CUBRID where duplicated code drifted apart,
meaning a fix (NULL/error check, bounds check, latch/lock release, cleanup on an error path,
type/width change) was applied to one copy but not the other. Reference bug: CBRD-28080,
where broker/cas_execute.c convert_db_value_to_string checks db_get_char()==NULL but the C++
copy method/method_query_util.cpp convert_db_value_to_string dropped the check and builds
std::string(NULL).

Source: /home/vimkim/gh/cb/develop at commit e64a04a79a. READ-ONLY. Do not edit, build,
checkout, stash, or commit anything in that repo. git log / blame / show / grep are fine.

## For each pair in your slice

1. Locate both functions (line numbers in the slice are a hint; confirm with grep).
2. Diff the two bodies (e.g. extract with sed -n and `diff -u -w`, or read side by side).
3. Classify EVERY non-trivial difference into one category:
   NULL/error-check | bounds/size-check | lock/latch-release | error-path-cleanup/free |
   type/width | semantic-other (intended behavior difference) | cosmetic (rename, format, logging).
4. For each non-cosmetic difference, find which side changed later:
   `git log -L <start>,<end>:<file> --format='%h %ad %s' --date=short` (or `git blame -L`) on the
   relevant lines. Record the commit hash, date and subject; note any CBRD-NNNNN or bug words.
   Check whether the other side ever got an equivalent change (git log -S'<snippet>' -- <otherfile>).
5. Decide if the difference is a MISSING FIX: the guarded condition can also occur in the
   unguarded copy. Intended differences (different data types, server vs client semantics,
   one side deliberately simplified) are NOT missing fixes. Say why.
6. For each missing-fix candidate, check reachability in the unguarded copy: who calls it,
   can the bad input/state reach it (trace callers 1-3 levels), is it a release-build issue
   (assert-only guards count as missing in release). Verdict: real | plausible | false-positive.

## Output

Write ONE markdown file at the path given in your brief. Sections:

### Pair table
| # | A (file:line func) | B (file:line func) | diff categories found | later-changed side + commit | missing fix? |

### Candidates
For each candidate: title; guarded side file:line with the guard quoted (<=6 lines);
unguarded side file:line with the corresponding code quoted; the commit that added the guard
(hash, date, subject); reachability trace with file:line for each hop; verdict and 1-2 sentence
reason; confidence. Keep quotes short. Do not pad. If no candidates, say so.

Final message back: a 5-15 line summary (counts + candidate one-liners with verdict). Status
PASS (no candidates) or ISSUES (candidates listed). Every claim must cite file:line.
