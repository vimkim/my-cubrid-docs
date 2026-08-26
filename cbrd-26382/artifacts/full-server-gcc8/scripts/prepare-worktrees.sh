#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 3 ]; then
  echo "usage: $0 CUBRID_REPOSITORY WORKTREE_ROOT ARTIFACT_ROOT" >&2
  exit 2
fi

repository=$(realpath "$1")
worktree_root=$(realpath -m "$2")
artifact_root=$(realpath "$3")
c_patch_file=$artifact_root/scope-exit-C.patch
d_patch_file=$artifact_root/scope-exit-D.patch

declare -A commits=(
  [scope-exit-QA-2029]=000a465c8fcf164d995aae005390a0af49b53a87
  [scope-exit-A]=6146cdb6aaf8708856f4b8e9f336362bb0843b2c
  [scope-exit-B]=8fd3ca03e58b342a494a2f5594be23c72a822479
  [scope-exit-C]=8fd3ca03e58b342a494a2f5594be23c72a822479
  [scope-exit-D]=8fd3ca03e58b342a494a2f5594be23c72a822479
)

if ! git -C "$repository" rev-parse --git-dir >/dev/null 2>&1; then
  echo "not a Git repository: $repository" >&2
  exit 1
fi
test -f "$c_patch_file"
test "$(sha256sum "$c_patch_file" | cut -d' ' -f1)" = \
  5334c3ac928329e16c891d8ab491e691c549e36cc448d774755dc555c1bace39
test -f "$d_patch_file"
test "$(sha256sum "$d_patch_file" | cut -d' ' -f1)" = \
  b828ab9f2782991fb506abbfadc3cbe97b0c6ded8b482d5e5ffbb56264f47751

for commit in "${commits[@]}"; do
  git -C "$repository" cat-file -e "$commit^{commit}" || {
    echo "missing commit $commit; fetch the canonical CUBRID history first" >&2
    exit 1
  }
done

mkdir -p "$worktree_root"
for name in scope-exit-QA-2029 scope-exit-A scope-exit-B scope-exit-C scope-exit-D; do
  destination=$worktree_root/$name
  if [ -e "$destination" ]; then
    echo "refusing to overwrite existing path: $destination" >&2
    exit 1
  fi
  git -C "$repository" worktree add --detach "$destination" "${commits[$name]}"
  git -C "$destination" submodule update --init cubrid-cci cubrid-jdbc
done

git -C "$worktree_root/scope-exit-C" apply "$c_patch_file"
git -C "$worktree_root/scope-exit-D" apply "$d_patch_file"

for name in scope-exit-QA-2029 scope-exit-A scope-exit-B scope-exit-C scope-exit-D; do
  echo "$name $(git -C "$worktree_root/$name" rev-parse HEAD)"
  git -C "$worktree_root/$name" submodule status cubrid-cci cubrid-jdbc
done
git -C "$worktree_root/scope-exit-C" diff --check
git -C "$worktree_root/scope-exit-D" diff --check
