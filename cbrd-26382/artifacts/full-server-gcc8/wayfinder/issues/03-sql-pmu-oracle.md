# SQL and PMU Oracle

Type: research
Status: resolved
Blocked by: none

## Question

What measurement distinguishes a real scope-exit-induced regression from query
data, plan, run-order, CPU-placement, or random layout noise?

## Answer

Reconstruct the trace-off five-run QA mean, then run independent randomized
blocks with fixed database contents, verified cardinality/result/plan, server
and client CPU pinning, warmups, and 60 measured samples per A/B/C variant.
Capture core timing and server PMU counters; collect cache/front-end events in
separate passes when hardware scheduling requires it. Require at least a 5%
median effect, paired confidence interval excluding 1.0, low dispersion, and
repeatable direction before declaring regression or improvement.

[Back to map](../map.md)

