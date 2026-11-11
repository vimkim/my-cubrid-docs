#!/usr/bin/env bash
set -u
repo=${1:?Pass the path to a local cubrid-testcases-private-ex checkout}
head=0f42c42b96fe2ebc9f496f03c3ca5c34f812dc50
case_path=shell/_06_issues/_26_2h/cbrd_27780/cases/cbrd_27780.sh
run_dir=${TMPDIR:-/tmp}
scratch=$(mktemp -d "$run_dir/scanner-replay.XXXXXX")
cd "$scratch" || exit 1
db=db27780
mkdir "$db"
printf 'S0PLAIN' > "$db/$db"
printf 'S1HEAP' > "$db/${db}_x001"
chmod 000 "$db/${db}_x001"
write_ok() { printf 'OK %s\n' "$*"; }
write_nok() { printf 'NOK %s\n' "$*"; }
git -C "$repo" show "$head:$case_path" | sed -n '116,138p' > pinned-functions.sh
source ./pinned-functions.sh
printf 'control hits: %s\n' "$(count_plain S0PLAIN)"
check_no_plain 'scan encrypted marker' S1HEAP
chmod 600 "$db/${db}_x001"
printf 'actual extension content: '
cat "$db/${db}_x001"
printf '\n'
