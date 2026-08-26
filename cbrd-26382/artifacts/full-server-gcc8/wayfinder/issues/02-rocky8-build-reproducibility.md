# QA-CI Build and Rocky 8 Runtime Reproducibility

Type: research
Status: resolved
Blocked by: none

## Question

How can full CUBRID binaries be compared without path, toolchain, submodule, or
compiler-cache differences dominating the layout?

## Answer

The later QA provenance clarification supersedes the initial Rocky-build assumption. Build all four states in the current
`cubridci/cubridci:develop` image, whose resolved instance is CentOS 6.10 with devtoolset-8 GCC 8.3.1, then run the installed
binaries on Rocky Linux 8. Explicitly invoke repository `./build.sh -m release ... build` and verify `RelWithDebInfo` plus
`-O2 -g -DNDEBUG` from every CMake cache; do not rely on the image entrypoint's default mode.

Keep historical submodule pins, sequential clean builds, identical `/src` and `/out` paths, and `CCACHE_DISABLE=1`. Retain
the resolved mutable-image ID/digest, compiler/linker/userspace facts, CMake cache, build IDs, unstripped binaries, and
hashes. A/B share identical historical submodule pins; C is B plus the separately hashed patch. The unavailable historical
QA image digest and package ELF remain an explicit byte-identity limitation.

[Back to map](../map.md)
