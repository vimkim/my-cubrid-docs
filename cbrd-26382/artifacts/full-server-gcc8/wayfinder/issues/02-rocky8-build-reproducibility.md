# Rocky 8 Build Reproducibility

Type: research
Status: resolved
Blocked by: none

## Question

How can full CUBRID binaries be compared without path, toolchain, submodule, or
compiler-cache differences dominating the layout?

## Answer

Use the pinned Rocky Linux 8/GCC 8.5 toolchain, historical submodule pins,
sequential clean builds, identical `/src` and `/out` container paths, and no
shared ccache. Retain compiler/linker facts, CMake cache, link commands, build
IDs, unstripped binaries, and hashes. A/B share identical historical submodule
pins; C is B plus a separately hashed uncommitted patch.

[Back to map](../map.md)

