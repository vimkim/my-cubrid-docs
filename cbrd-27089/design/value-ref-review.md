# PR7927 value-reference redesign review

Reviewed `581a96332` against `fb567a629cdb390fff920542173fa36f454c74a0`; corrections committed as `f578cd0d0078eb026930380144ad503ab81bd040`.

## Standards

The standards reviewer noted that the repository's legacy C memory-RAII prohibition conflicts with use of an owning C++ helper from C-named sources. The confirmed design explicitly calls for a payload owner; these sources compile as C++, already use `record_descriptor` and STL owners, and allocation cleanup remains implemented with `free_and_init` in the C++ OOS module. We retain this small owner so error exits cannot strand pending allocations. This is a deliberate design interpretation, not a claim of literal compliance with that older rule.

A minor duplication remains in the loader's three queue-cleanup sites: clear record descriptors, discard pending payloads, reset byte accounting. A helper was suggested but not added because it would not materially reduce this diff.

## Spec

1. Fixed: pending `record_descriptor::pack` originally used only `assert_release`, which does not stop packing in release builds. It now sets an error and returns before writing any bytes. The regression verifies the error, unchanged packer cursor and untouched transport buffer.
2. Fixed: restored the base's dormant MVCC assignment-reevaluation block instead of carrying over its removal from the old PR. Current callers do not request that branch; its removal unnecessarily enlarged this change.

The spec reviewer rechecked `f578cd0d0` and confirmed both findings resolved. Source review found no further concrete lifetime or rollback defect. Review is distinct from executed test evidence.
