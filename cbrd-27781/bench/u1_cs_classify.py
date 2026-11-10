import sys, re, collections
# classify each context-switch sample by the blocking reason in its user stack
RULES = [
 ('growth lock wait (oos_reclaim_claim_growth)', 'oos_reclaim_claim_growth'),
 ('oos reclaim sweep step', 'oos_reclaim_sweep_step'),
 ('file_alloc (file header latch etc.)', 'file_alloc'),
 ('oos header/bestspace', 'oos_find_best_page|oos_stats_'),
 ('log flush / commit wait', 'logpb_flush|log_commit|logtb_|log_wakeup|logpb_'),
 ('log append', 'log_append|prior_lsa'),
 ('page buffer latch', 'pgbuf_'),
 ('lock manager', 'lock_object|lock_'),
 ('heap', 'heap_'),
 ('btree', 'btree_'),
 ('network recv / worker idle', 'css_|worker_pool|cubthread::worker|epoll|recv'),
 ('daemons', 'cubthread::daemon|vacuum_'),
]
def cat(stack):
    s = '\n'.join(stack)
    for name, pat in RULES:
        if re.search(pat, s):
            return name
    return 'other: ' + next((f for f in stack if not f.startswith('[') and '__futex' not in f and 'pthread' not in f and 'syscall' not in f), '?')
cnt = collections.Counter(); stack = []
def flush():
    if stack: cnt[cat(stack)] += 1
for line in open(sys.argv[1]):
    if not line.startswith('\t') and line.strip():
        flush(); stack = []
    elif line.startswith('\t'):
        parts = line.strip().split(' ', 1)
        stack.append(parts[1] if len(parts) > 1 else '?')
flush()
tot = sum(cnt.values())
for k, v in cnt.most_common(14):
    print(f'{v:8d} {100*v/tot:5.1f}%  {k}')
print(f'{tot:8d} total')
