import sys,re,collections
ALLOC=re.compile(r'^(__libc_calloc|calloc|operator_new|operator_delete|cub_calloc|malloc|_int_malloc|free|_int_free|cfree|__libc_free|__libc_malloc|malloc_consolidate|tcache_|_int_free_merge|unlink_chunk|__GI___libc|operator new|operator delete|realloc|_int_realloc|malloc_usable_size|sysmalloc|__malloc|__free)')
GROUPS=[('session_connect (artifact)',r'sysprm_unpack_session_parameters|ssession_'),
 ('log prior list (pre-existing)',r'prior_lsa_|logpb_free_prior_node|logpb_prior_lsa_append|log_prior_inflight|log_get_next_nested_top|log_do_postpone'),
 ('pending record buffer',r'cubmem::standard_|record_descriptor::'),
 ('OOS payload / pending values',r'heap_attrinfo_dbvalue_to_recdes|heap_pending_record::'),
 ('OOS plan/finalize/ref vectors',r'heap_oos_|oos_chain_ref|heap_oos_column_plan|oos_|heap_attrinfo_transform|heap_attrinfo_determine'),
]
tot=0;c=collections.Counter();cur=[];cal=collections.Counter()
def flush():
    global tot
    if not cur: return
    tot+=1
    if ALLOC.match(cur[0]):
        caller=next((f for f in cur if not ALLOC.match(f)),'?')
        for n,rx in GROUPS:
            if re.search(rx,caller): c[n]+=1; break
        else: c['other']+=1; cal[caller]+=1
for line in sys.stdin:
    line=line.rstrip()
    if not line: flush(); cur=[]; continue
    p=line.strip().split(None,1)
    if len(p)==2: cur.append(re.sub(r'\+0x[0-9a-f]+$','',p[1].rsplit(' (',1)[0]))
flush()
print(f"  samples={tot} allocator={sum(c.values())} ({100*sum(c.values())/tot:.2f}%)")
for n,_ in GROUPS+[('other',0)]: print(f"    {n:32} {100*c[n]/tot:5.2f}%")
print("    other callers:", '; '.join(f"{k[:50]} {100*v/tot:.2f}%" for k,v in cal.most_common(4)))
