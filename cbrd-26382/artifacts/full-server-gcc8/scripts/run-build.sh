#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: RUNTIME_CONFIG=/path/to/config.env $0 LABEL WORKTREE" >&2
  exit 2
fi

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=runtime-common.sh
source "$script_dir/runtime-common.sh"

label=$1
worktree=$(realpath "$2")
load_results_root
require_setting BUILD_IMAGE
require_setting BUILD_JDK_HOME

out=$results_root/$label
image=$BUILD_IMAGE
jdk=$BUILD_JDK_HOME
build_jobs=${BUILD_JOBS:-$(nproc)}
gradle_cache=$(realpath -m "${GRADLE_CACHE_ROOT:-$results_root/gradle-cache}")
c_patch_file=$artifact_root/scope-exit-C.patch
d_patch_file=$artifact_root/scope-exit-D.patch

case "$label" in
  qa-2029|A|B|C|D) ;;
  *) echo "unsupported label: $label" >&2; exit 2 ;;
esac

if [ ! -d "$worktree/.git" ] && [ ! -f "$worktree/.git" ]; then
  echo "not a Git worktree: $worktree" >&2
  exit 2
fi

test -f "$c_patch_file"
test "$(sha256sum "$c_patch_file" | cut -d' ' -f1)" = \
  5334c3ac928329e16c891d8ab491e691c549e36cc448d774755dc555c1bace39
test -f "$d_patch_file"
test "$(sha256sum "$d_patch_file" | cut -d' ' -f1)" = \
  b828ab9f2782991fb506abbfadc3cbe97b0c6ded8b482d5e5ffbb56264f47751
if ! [[ "$build_jobs" =~ ^[1-9][0-9]*$ ]]; then
  echo "BUILD_JOBS must be a positive integer: $build_jobs" >&2
  exit 2
fi
image_id=$(podman image inspect --format '{{.Id}}' "$image")
podman run --rm --entrypoint /usr/bin/test "$image" -d "$jdk"
git_common_dir=$(cd "$worktree" && realpath "$(git rev-parse --git-common-dir)")
git_repository_root=$(dirname "$git_common_dir")
git_repository_alias=/$(basename "$git_repository_root")
worktree_alias=/$(basename "$worktree")

mkdir -p "$out" "$gradle_cache"
if find "$out" -mindepth 1 -print -quit | grep -q .; then
  echo "output directory is not empty: $out" >&2
  exit 2
fi

mkdir -p "$out/build/vm" "$out/home" "$out/manifest"
ln -s "$jdk" "$out/build/vm/jdk8"
touch "$out/build/vm/jdk8.tar.gz"

git -C "$worktree" rev-parse HEAD >"$out/manifest/source.sha"
git -C "$worktree" status --short --branch >"$out/manifest/git-status.before.txt"
git -C "$worktree" submodule status >"$out/manifest/submodules.txt"
printf '%s\n' "$image" >"$out/manifest/container-image.txt"
printf '%s\n' "$image_id" >"$out/manifest/container-image-id.txt"
if [ "$label" = C ]; then
  sha256sum "$c_patch_file" >"$out/manifest/patch.sha256"
elif [ "$label" = D ]; then
  sha256sum "$d_patch_file" >"$out/manifest/patch.sha256"
fi

git_mount_args=()
if [ "$git_repository_root" != "$worktree" ]; then
  git_mount_args+=(
    -v "$git_repository_root:$git_repository_root:ro"
    # Linked-worktree submodules use paths such as ../../cubrid/.git/....
    # When the worktree is mounted at /src, that path resolves via /cubrid.
    -v "$git_repository_root:$git_repository_alias:ro"
    -v "$worktree:$worktree:ro"
    # The submodule Git config points back to the worktree using a relative
    # path that resolves from the repository alias (for example /scope-exit-A).
    -v "$worktree:$worktree_alias:ro"
  )
fi

podman --cgroup-manager=cgroupfs run --rm \
  --entrypoint /usr/bin/scl \
  --security-opt label=disable \
  --userns=keep-id \
  "${git_mount_args[@]}" \
  -v "$worktree:/src:rw" \
  -v "$out:/out:rw" \
  -v "$gradle_cache:/gradle-cache:rw" \
  -w /src \
  -e HOME=/out/home \
  -e GRADLE_USER_HOME=/gradle-cache \
  -e 'GRADLE_OPTS=-Dorg.gradle.daemon=false -Dorg.gradle.vfs.watch=false' \
  -e CCACHE_DISABLE=1 \
  -e "MAKEFLAGS=-j$build_jobs" \
  -e CC=gcc \
  -e CXX=g++ \
  "$image" \
  enable devtoolset-8 -- /bin/bash -lc '
    set -euo pipefail
    export PATH='"$jdk"'/bin:$PATH
    {
      cat /etc/rocky-release 2>/dev/null \
        || cat /etc/centos-release 2>/dev/null \
        || cat /etc/os-release
      gcc --version | head -1
      g++ --version | head -1
      java -version
      javac -version
      cmake --version | head -1
      ninja --version
      bison --version | head -1
      ld --version | head -1
    } > /out/manifest/toolchain.txt 2>&1
    ./build.sh -m release -C gcc -g ninja \
      -s /src -b /out/build -p /out/CUBRID -j '"$jdk"' \
      -c "-DWITH_CMSERVER=OFF" build
  ' 2>&1 | tee "$out/build.log"

for binary in CUBRID/bin/cub_server CUBRID/bin/csql CUBRID/lib/libcubrid.so.11.5; do
  test -f "$out/$binary"
done

sha256sum \
  "$out/CUBRID/bin/cub_server" \
  "$out/CUBRID/bin/csql" \
  "$out/CUBRID/lib/libcubrid.so.11.5" \
  >"$out/manifest/binaries.sha256"
file \
  "$out/CUBRID/bin/cub_server" \
  "$out/CUBRID/bin/csql" \
  "$out/CUBRID/lib/libcubrid.so.11.5" \
  >"$out/manifest/binaries.file.txt"
readelf -n "$out/CUBRID/bin/cub_server" >"$out/manifest/cub_server.notes.txt"
readelf -n "$out/CUBRID/lib/libcubrid.so.11.5" >"$out/manifest/libcubrid.notes.txt"
cp "$out/build/CMakeCache.txt" "$out/manifest/CMakeCache.txt"
git -C "$worktree" status --short --branch >"$out/manifest/git-status.after.txt"

echo "completed $label"
