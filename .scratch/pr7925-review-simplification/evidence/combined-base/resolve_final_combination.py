from pathlib import Path
import re
root=Path('/home/vimkim/gh/cb/pr7925-simplification-integration')
pattern=re.compile(r'^<<<<<<< HEAD\n(.*?)^\|\|\|\|\|\|\|[^\n]*\n(.*?)^=======\n(.*?)^>>>>>>>[^\n]*\n',re.M|re.S)

def resolve(path,choices):
    s=path.read_text(); blocks=list(pattern.finditer(s)); assert len(blocks)==len(choices),(path,len(blocks),len(choices))
    i=iter(choices)
    def replacement(m):
        choice=next(i)
        return m.group(1) if choice=='dependency' else m.group(3) if choice=='workspace' else choice(m)
    path.write_text(pattern.sub(replacement,s))
resolve(root/'src/loaddb/load_server_loader.cpp',[
 lambda m:m.group(1).replace('NULL, UPDATE_INPLACE_NONE, NULL, has_BU_lock,\n\t\t\t\t\t\t   true, false, false, &m_recdes_collected[i]);','NULL, UPDATE_INPLACE_NONE, NULL, force_flags,\n\t\t\t\t\t\t   false, &m_recdes_collected[i]);')
])
resolve(root/'src/transaction/locator_sr.h',[
 'workspace',
 lambda m:m.group(3).replace('int force_flags = LC_FORCE_FLAG_NONE);','int force_flags = LC_FORCE_FLAG_NONE, bool from_copyarea = false,\n                                 heap_pending_record *pending = nullptr);')
])
resolve(root/'src/transaction/locator_sr.c',[
 lambda m:m.group(1).replace('heap_pending_record *pending = nullptr);','heap_pending_record *pending = nullptr,\n                                 bool from_workspace = false);'),
 lambda m:m.group(1).replace('heap_pending_record *pending = nullptr);','heap_pending_record *pending = nullptr,\n                                bool from_workspace = false);'),
 lambda m:m.group(3).replace('int force_flags)','int force_flags,\n                              bool from_copyarea, heap_pending_record *pending)'),
 lambda m:m.group(1).replace('heap_pending_record * pending)','heap_pending_record * pending, bool from_workspace)'),
 lambda m:m.group(3).replace('LC_FORCE_FLAG_NONE);','LC_FORCE_FLAG_NONE,\n                              from_copyarea, pending);'),
 lambda m:m.group(3).replace('LC_FORCE_FLAG_NONE);','LC_FORCE_FLAG_NONE,\n                              from_copyarea, pending);'),
 lambda m:m.group(1).replace('heap_pending_record * pending)','heap_pending_record * pending, bool from_workspace)'),
 lambda m:m.group(1).replace('from_copyarea, pending);','from_copyarea, pending, from_workspace);'),
 lambda m:m.group(3)+'\t}\n\n'+m.group(1),
 lambda m:m.group(1).replace('NULL, UPDATE_INPLACE_NONE, true, true);','NULL, UPDATE_INPLACE_NONE, true, true, NULL, true);'),
 lambda m:m.group(3).replace('LC_FORCE_FLAG_FROM_WORKSPACE);','LC_FORCE_FLAG_FROM_WORKSPACE, true);'),
 lambda m:m.group(3).replace('UPDATE_INPLACE_NONE, NULL);','UPDATE_INPLACE_NONE, NULL,\n                                  LC_FORCE_FLAG_NONE, false, &pending);'),
 lambda m:m.group(3).replace('UPDATE_INPLACE_OLD_MVCCID, NULL);','UPDATE_INPLACE_OLD_MVCCID, NULL, LC_FORCE_FLAG_NONE, false, &prepared);')
])
p=root/'src/transaction/locator_sr.c';s=p.read_text()
# Both origins are retained. SA workspace conversion keeps its cached-copyarea
# path; server copy-area conversion uses the prerequisite owner as before.
needle='  bool from_workspace = (force_flags & LC_FORCE_FLAG_FROM_WORKSPACE) != 0;\n'
assert s.count(needle)==1
s=s.replace(needle,needle+'''#if defined (SA_MODE)
  if (from_workspace)
    {
      from_copyarea = false;
    }
#endif
''')
start=s.index('\nlocator_update_force (THREAD_ENTRY * thread_p',s.index('locator_move_record (THREAD_ENTRY * thread_p'))
pos=s.index('  /* *INDENT-ON* */\n',start)+len('  /* *INDENT-ON* */\n')
s=s[:pos]+'''#if defined (SA_MODE)
  if (from_workspace)
    {
      from_copyarea = false;
    }
#endif
'''+s[pos:]
# Ordinary client/workspace UPDATE carries both origins; pending SQL/replication
# callers retain their existing owner and default workspace=false.
needle='REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true, true);'
assert s.count(needle)==1
s=s.replace(needle,'REPL_INFO_TYPE_RBR_NORMAL, pruning_type, NULL, NULL, UPDATE_INPLACE_NONE, true, true,\n                                  NULL, true);')
p.write_text(s)
for name in ['src/loaddb/load_server_loader.cpp','src/transaction/locator_sr.h','src/transaction/locator_sr.c']:
    assert not re.search(r'^<<<<<<<|^=======|^>>>>>>>', (root/name).read_text(),re.M)
print('Resolved final-source conflicts while retaining both origin and owner arguments.')
