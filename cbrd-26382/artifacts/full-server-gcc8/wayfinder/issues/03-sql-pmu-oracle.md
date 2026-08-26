# SQL and PMU Oracle

Type: research
Status: resolved
Blocked by: none

## Question

What measurement distinguishes a real scope-exit-induced regression from query
data, plan, run-order, CPU-placement, or random layout noise?

## Answer

Reconstruct the trace-off QA comparison, then use ordered and reversed blocks with fixed database contents and verified
cardinality/result/plan. QA did not pin a single CPU, so the final hybrid-host protocol constrains server and client to all
P-cores while allowing migration inside that set. Record server migrations, context switches, physical I/O, page faults,
and CPU ticks beside latency.

Capture core timing and server PMU counters; collect cache/front-end events in separate passes to avoid excessive counter
multiplexing. Require at least a 5% median effect, paired confidence interval excluding 1.0, low dispersion, and repeatable
direction before declaring the entire causal regression or improvement reproduced. A smaller confidence-separated effect
may be described only as directional reproduction, with the unmet magnitude gate stated explicitly.

[Back to map](../map.md)
