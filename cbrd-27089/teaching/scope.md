# Analysis Scope

Subject: PR 7600: partition routing and OOS ownership

## Included

Heap/page/slot/record and identifier foundations; root and child classes; OOS ownership; INSERT/UPDATE transforms; increments and LOB state; duplicate-key probes; error exits; every PR hunk.

## Excluded

Full OOS survey, cross-database comparisons, production modifications, live CI monitoring and publication.

## Central Questions

What is a partition heap? Why does transformation before routing fail? How does each changed line repair it? What happens to side effects and errors? What does the regression establish?

## Tracer Scenarios

Range-partition INSERT with a 64-byte FORCE_OUTLINE value; UPDATE changing destination; nonpartitioned and no-demotion writes; REPLACE/ODKU probes; allocation/pruning/serialization errors.
