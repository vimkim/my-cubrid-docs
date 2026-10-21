# CUBRID third-party cache design for Kubernetes CI

Date: 2026-09-22  
CUBRID source inspected: `a0026f9293523bed2af4c52d8c7299c6ce9b14d0`  
`cubridci` source inspected: `b013b23e3688937ec6ed6adda14c3978f40b1e77`

## Recommendation

Use two stages.

1. **Now, without a CUBRID repository change:** mount a small wrapper through the CI pod configuration. Keep `build.sh clean` for first-party output, then restore an immutable, content-addressed snapshot of the complete `build_x86_64_<mode>/3rdparty/` tree into pod-local storage before `build.sh build`. On a miss, build locally and publish the snapshot with a temporary name plus atomic rename. Never let two pods build in one shared writable third-party tree.
2. **Long term:** teach `3rdparty/CMakeLists.txt` one complete `PREBUILT` mode and produce a relocatable, immutable third-party prefix independently of the CUBRID build directory. Put that prefix in a digest-pinned CI image layer (or an OCI/PVC artifact), so every CUBRID build can clean its own build directory and only rebuild CUBRID sources.

The second design is the better end state. The first is a low-risk bridge that preserves today's third-party commands and binary outputs exactly.

## What currently forces the rebuild

The CI entrypoint calls:

```sh
./build.sh -p "$CUBRID" "$@" clean build
```

That is explicit in [`docker-entrypoint.sh` lines 39-53](https://github.com/CUBRID/cubridci/blob/b013b23e3688937ec6ed6adda14c3978f40b1e77/docker/ci/docker-entrypoint.sh#L39-L53). `build.sh clean` removes every entry under the selected build directory, rather than asking Ninja to clean individual targets ([`build.sh` lines 162-184](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/build.sh#L162-L184)). The default `all` path also expands to `clean build dist`, but the entrypoint already passes the explicit `clean build` pair ([`build.sh` lines 680-692](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/build.sh#L680-L692)).

CUBRID puts all `ExternalProject` state below `${CMAKE_BINARY_DIR}/3rdparty` by setting `EP_BASE` there ([`3rdparty/CMakeLists.txt` lines 91-104](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/3rdparty/CMakeLists.txt#L91-L104)). CMake defines an `EP_BASE` tree as `Download/`, `Source/`, `Build/`, `Stamp/`, and `Install/`; the stamp directory records completion of each step ([CMake `ExternalProject` directory documentation](https://cmake.org/cmake/help/latest/module/ExternalProject.html#directory-options)). Deleting the build directory therefore deletes both the outputs and the evidence that download/configure/build/install already completed.

The source archives do have SHA-256 values ([`3rdparty/CMakeLists.txt` lines 23-55](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/3rdparty/CMakeLists.txt#L23-L55)). `URL_HASH` lets CMake reuse a matching previously downloaded file without contacting the remote, but only if that download directory still exists ([CMake `URL_HASH` documentation](https://cmake.org/cmake/help/latest/module/ExternalProject.html#url)). `clean` removes it first.

The active GHA Kubernetes workflow already preserves `ccache` on node storage, separately by build mode, and calls `/entrypoint.sh build` afterward ([`gha-ci.yml` lines 677-687 and 790-809](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/.github/workflows/gha-ci.yml#L677-L687)). That accelerates compilations that go through the compiler launcher, but it does not preserve downloads, configure results, link/archive work, installed headers, or ExternalProject stamps.

### Current artifact shape

At the inspected commit, a completed local debug build had this shape:

| Item | Observed size / behavior |
|---|---:|
| Whole `build_preset_debug_gcc/3rdparty` | 363 MiB |
| `Download/` | 58 MiB, including a 53 MiB OpenSSL archive |
| `Source/` | 185 MiB |
| `Build/` | 87 MiB |
| installed `lib/` | 19 MiB |
| installed `include/` | 4.2 MiB |

This is a local measurement, not a stable product guarantee. It shows that copying one local compressed snapshot is a practical bridge and avoids the much more expensive network/configure/compile sequence.

Most compiled dependencies already link statically:

- expat, libedit, OpenSSL, LZ4, RE2, and TBB are named as `.a` outputs ([expat/edit](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/3rdparty/CMakeLists.txt#L221-L305), [LZ4/OpenSSL](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/3rdparty/CMakeLists.txt#L309-L428), [RE2/TBB](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/3rdparty/CMakeLists.txt#L490-L555)). RapidJSON is header-only in this build.
- unixODBC is the exception: it is configured with its defaults and consumed as `libodbc.so` ([`3rdparty/CMakeLists.txt` lines 430-460](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/3rdparty/CMakeLists.txt#L430-L460)); `cub_cas_cgw` links it ([`broker/CMakeLists.txt` lines 293-302](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/broker/CMakeLists.txt#L293-L302)). Changing that one library to static is a product-linkage change, not necessary for caching, and should be verified separately.

## Design 1: deploy-only immutable ExternalProject snapshot

This requires a CI pod-template/ConfigMap change, but no CUBRID source commit and no `cubridci` image rebuild.

### Pod layout

Use three locations:

```text
/cache/cubrid-3rdparty/                 PVC or node seed; immutable archives only
/workspace/cubrid/                      fixed source path
/workspace/cubrid/build_x86_64_<mode>/  pod-local emptyDir; writable build tree
```

Kubernetes persistent volumes outlive individual pods, whereas ephemeral volumes are destroyed with their pod ([Kubernetes volumes](https://kubernetes.io/docs/concepts/storage/volumes/)). Use the persistent location only for completed cache archives. Restore each archive into a pod-local `emptyDir` and let that pod own all writes.

Do **not** mount the PVC directly at `build_x86_64_<mode>/3rdparty`. `rm -rf "$build_dir"/*` can traverse a writable mount and erase its contents, and parallel ExternalProject builds would modify the same `Source/`, `Build/`, and `Stamp/` paths.

### Wrapper sequence

The externally mounted wrapper should implement the following order:

1. Resolve the build mode and exact build directory in the same way as `build.sh`.
2. Run `./build.sh ... clean` alone.
3. Compute the cache key below.
4. If `<cache>/<key>/complete` and the archive checksum are valid, extract the archive so that `build_x86_64_<mode>/3rdparty` is recreated.
5. Run `./build.sh ... build` (without `clean`). Configure regenerates the main Ninja graph; the restored complete stamps and byproducts make the third-party targets no-ops.
6. On a miss, allow the normal build to create the tree, validate every required output and `*-done` stamp, write an archive and manifest under `<key>.tmp.<pod-uid>`, `fsync` if the storage requires it, create `complete` last, then rename the temporary directory to `<key>`.
7. Keep the existing `ccache` setup for CUBRID source files.

The whole subtree is required for this bridge. Copying just `lib/*.a` is insufficient because Ninja's ExternalProject edges depend on the stamps. Generated stamp scripts also contain absolute source/build paths, so both source root and build root must be fixed across producer and consumer pods. Record both paths in the manifest and treat a mismatch as a cache miss.

At this source revision, publication validation should require at least these consumers and all eight matching `Stamp/<target>/<target>-done` files:

```text
lib/libexpat.a                    include/expat/
lib/libedit.a                     include/editline/ and include/histedit.h
Source/lz4/lib/liblz4.a           Source/lz4/lib/*.h
lib/libssl.a, lib/libcrypto.a     include/openssl/
lib/libodbc.so                    include/sql*.h and include/unixODBC/
Source/rapidjson/include/         (header-only)
Source/re2/obj/libre2.a           Source/re2/re2/ and Source/re2/util/
lib/libtbb.a                      Source/libtbb/include/
```

The target names are `libexpat`, `libedit`, `lz4`, `libopenssl`, `libodbc`, `rapidjson`, `re2`, and `libtbb`. This list must be updated in the same review that changes the dependency set.

### Exact cache key

Create a newline-delimited manifest and hash the manifest bytes with SHA-256. Do not key on the CUBRID commit: ordinary engine source changes must hit the same third-party cache.

```text
schema=cubrid-ep-tree-v1
thirdparty_cmake_sha256=<sha256 of 3rdparty/CMakeLists.txt>
image_digest=<resolved sha256 digest, never a movable tag>
os_arch=<uname -s>/<uname -m>
cc=<real compiler path and complete first --version line>
cxx=<real compiler path and complete first --version line>
cmake=<complete first --version line>
generator=Ninja
target=x86_64
build_mode=<release|debug|optdebug>
source_dir=/workspace/cubrid
build_dir=/workspace/cubrid/build_x86_64_<mode>
thirdparty_options=<sorted WITH_LIB*=..., CFLAGS, CXXFLAGS, LDFLAGS inputs>
```

Use `sha256(manifest)` as the directory name and save the manifest beside the archive. Pinning the container by digest is important because an image digest uniquely identifies immutable image content, while a tag can move ([Kubernetes image documentation](https://kubernetes.io/docs/concepts/containers/images/#image-names)).

`build_mode` and absolute paths are bridge-specific invalidators. The current third-party commands mostly force their own optimization settings, but CMake generates configuration-named scripts/stamps, and the cached tree is not relocatable. The long-term prefix design removes those three fields.

### Concurrency and failure rules

- **Never share a live writable tree.** Each pod builds/restores locally.
- **Archives are immutable.** Readers only consume entries with a valid manifest, archive checksum, required-output list, and final `complete` sentinel.
- **Single publication winner.** Use an atomic `mkdir <key>.publish-lock` or a Kubernetes Lease, then rename a completed temporary directory. A losing builder discards its temporary output.
- **Do not rely on PVC access mode for locking.** Kubernetes documents that access modes are used for matching/mount constraints and do not themselves enforce write protection ([PersistentVolume access modes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes)).
- **Do not publish failures.** A terminated download/build leaves only a uniquely named temporary directory, which a later sweeper may remove.
- **PRs should be read-only publishers.** Prefer one trusted `develop`/dependency-seed job as writer. A PR that changes `3rdparty/CMakeLists.txt` may build its new key locally for validation but should not publish it to the shared trusted namespace.

### Invalidation

Invalidate when any manifest field changes. In practice this means:

- third-party URL, SHA-256, configure/build/install command, PIC/static flags, or dependency list changes;
- CI image/toolchain/CMake changes;
- architecture/target or relevant flags change;
- build mode or fixed path changes while using the full-tree bridge.

Do not invalidate for changes elsewhere in CUBRID source. Also do not use a fallback prefix match: a cache hit is exact or it is a miss.

## Design 2: relocatable prebuilt prefix and CI image layer

This is the clean design to implement in `3rdparty/CMakeLists.txt` plus the `cubridci` Dockerfile/entrypoint.

### CMake contract

Add one coherent interface, for example:

```text
-DCUBRID_3RDPARTY_MODE=BUILD|PREBUILT
-DCUBRID_3RDPARTY_ROOT=/opt/cubrid-3rdparty/<key>
```

In `BUILD` mode, a dedicated third-party producer builds and installs a relocatable prefix. In `PREBUILT` mode, the main project creates imported/interface targets from that prefix and creates no `ExternalProject` build targets. Validate the expected headers/libraries and a machine-readable manifest during configure; fail rather than silently falling back to a system library.

The current per-library `SYSTEM` switches are not sufficient as a general solution:

- expat, libedit, and OpenSSL have `SYSTEM` branches;
- unixODBC's non-`EXTERNAL` branch is an error;
- LZ4 does not consult `WITH_LZ4` on Unix;
- RapidJSON is always an ExternalProject;
- RE2 rejects non-`EXTERNAL` values;
- TBB has no complete alternative branch.

Those behaviors are visible in the respective sections of [`3rdparty/CMakeLists.txt`](https://github.com/CUBRID/cubrid/blob/a0026f9293523bed2af4c52d8c7299c6ce9b14d0/3rdparty/CMakeLists.txt#L210-L557). A single prebuilt mode prevents a mixed build in which some libraries are cached and others are silently rebuilt.

### Artifact contents

The prefix should contain only consumer inputs, not ExternalProject working state:

```text
include/                 installed/generated public headers
lib/                     libraries
share/cubrid-3rdparty/manifest.json
share/cubrid-3rdparty/licenses/
```

The manifest should record each upstream URL/hash, build command/options, compiler identity, target triple, libc baseline, CMake version, and a SHA-256 for every installed file. Build it once in a dedicated image stage and copy the prefix into the final `cubridci` build image. Pin that image by digest in Kubernetes.

The key is then:

```text
sha256(
  schema=cubrid-prebuilt-prefix-v1
  + sha256(3rdparty/CMakeLists.txt and any third-party patch files)
  + producer image digest
  + target triple
  + ABI-affecting compiler/linker flags
)
```

It does **not** need CUBRID build mode, source path, build path, or engine commit once the prefix is genuinely relocatable and third-party compilation is deliberately mode-independent.

### Static-link policy

Keep the six existing static libraries static. For unixODBC, choose explicitly:

- **Compatibility-first:** preserve `libodbc.so` in the prebuilt prefix. This makes the cache optimization output-equivalent to today.
- **Static follow-up:** configure unixODBC with `--enable-static --disable-shared --with-pic`, point `LIBUNIXODBC_LIBS` at `libodbc.a`, and express its private link dependencies explicitly. Verify `cub_cas_cgw` functionality and check `readelf -d`/`ldd` to prove it no longer needs `libodbc.so`. Do this as a separate change because it changes the shipped executable's runtime dependency behavior.

### Entrypoint behavior after the redesign

The entrypoint can continue doing a clean first-party build:

```sh
./build.sh -p "$CUBRID" \
  -c "-DCUBRID_3RDPARTY_MODE=PREBUILT -DCUBRID_3RDPARTY_ROOT=/opt/cubrid-3rdparty/$key" \
  "$@" clean build
```

Now `clean` only removes disposable CUBRID build state. The third-party prefix is outside the build directory and immutable. CUBRID source compilation remains accelerated by the existing `ccache`; third-party download/configure/build/install does not occur in job pods at all.

## Acceptance checks

For either design, collect these facts in CI logs:

1. computed key, manifest, cache hit/miss, producer identity, and resolved image digest;
2. network receive delta around the build (a hit should not contact the third-party URLs);
3. no third-party configure/build/install commands on a hit;
4. SHA-256 of every consumed library/header manifest;
5. `file`, `readelf -h`, and compiler/ABI identity checks for archives and shared libraries;
6. `readelf -d`/`ldd` for `cub_server`, `csql`, `cub_cas`, and `cub_cas_cgw` to detect linkage drift;
7. one forced invalidation test by changing a third-party hash or producer-image digest;
8. two simultaneous same-key jobs to prove readers are isolated and publication is atomic;
9. a killed producer to prove no incomplete entry becomes readable;
10. release and optdebug builds plus the normal SQL/medium/shell qualification used by the target CI workflow.

## Decision summary

| Choice | CUBRID commit | First hit | Warm hit | Concurrency safety | Path dependence | Recommendation |
|---|---|---:|---:|---|---|---|
| Shared writable build directory, remove `clean` | No | normal | fastest | poor unless serialized | high | Avoid as a shared multi-pod cache |
| Immutable full `3rdparty/` snapshot restored locally | No | normal | local extract | good with atomic publication | high | Deploy now |
| Relocatable prebuilt prefix in digest-pinned image | Yes | image build only | no job-time work | best; read-only | none | Target architecture |
