#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "usage: $0 LABEL WORKTREE" >&2
  exit 2
fi

label=$1
worktree=$2
results_root=/home/vimkim/gh/cb/cbrd-26382-results
out=$results_root/$label
image=localhost/cbrd26382-rocky8-gcc8:build-ready
image_id=c4da6a0898ef11f67c3c45703e4d78d4f52446e6b225004da212a0d587806cbf
jdk=/usr/lib/jvm/java-1.8.0-openjdk-1.8.0.504.b01-1.1.el8_10.x86_64
gradle_cache=/home/vimkim/gh/cb/cbrd-26382-gradle-cache

case "$label" in
  qa-2029|A|B|C) ;;
  *) echo "unsupported label: $label" >&2; exit 2 ;;
esac

if [ ! -d "$worktree/.git" ] && [ ! -f "$worktree/.git" ]; then
  echo "not a Git worktree: $worktree" >&2
  exit 2
fi

mkdir -p "$out"
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
  sha256sum "$results_root/manifests/scope-exit-C.patch" >"$out/manifest/patch.sha256"
fi

podman --cgroup-manager=cgroupfs run --rm \
  --security-opt label=disable \
  --userns=keep-id \
  -v /home/vimkim/gh/cb:/home/vimkim/gh/cb:ro \
  -v "$worktree:/src:rw" \
  -v "$out:/out:rw" \
  -v "$gradle_cache:/gradle-cache:rw" \
  -w /src \
  -e HOME=/out/home \
  -e GRADLE_USER_HOME=/gradle-cache \
  -e 'GRADLE_OPTS=-Dorg.gradle.daemon=false -Dorg.gradle.vfs.watch=false' \
  -e CCACHE_DISABLE=1 \
  -e MAKEFLAGS=-j40 \
  -e CC=gcc \
  -e CXX=g++ \
  "$image" \
  bash -lc '
    set -euo pipefail
    {
      cat /etc/rocky-release
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
