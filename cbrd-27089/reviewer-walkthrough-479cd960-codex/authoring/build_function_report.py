from pathlib import Path
import json,re,collections,subprocess
out=Path(__file__).resolve().parents[1];x=json.loads((out/'evidence/functions-ast.json').read_text());idx=json.loads((out/'evidence/callers-index.json').read_text());meta=json.loads((out/'evidence/manifest.json').read_text());coverage=json.loads((out/'evidence/function-hunk-coverage.json').read_text());base=x['base'];head=x['head']
fs=sorted(x['functions'],key=lambda f:(f['path'],(f['head'] or f['base'])['start']))
ids={f['name']:f'F{i:02d}' for i,f in enumerate(fs,1)}
def url(path,line=None,rev=head):return f'https://github.com/CUBRID/cubrid/blob/{rev}/{path}'+(f'#L{line}' if line else '')
def link(name):return f'[{name}](#{ids[name].lower()})' if name in ids else f'`{name}`'
def source(f,rev):return f'[{rev[:8]}:{f["start"]}]({url(f["path"],f["start"],rev)})'
def own_calls(f):return {c['name']:c['line'] for c in (f or {}).get('calls',[]) if re.fullmatch(r'[a-z_]\w*',c['name'])}
def callers(name,rev,path):
 # Production names are globally distinctive. Anonymous test helpers are limited to their TU.
 rows=idx[rev]+x['all_functions'][rev];seen={}
 for r in rows:
  if path.startswith('unit_tests/') and r['path']!=path:continue
  for c in r['calls']:
   if c['name']==name:seen[(r['path'],r['name'],c['line'])]=r
 return seen
research=(out/'authoring/function-research.en.md').read_text()
parts=re.split(r'^## `([^`]+)`[^\n]*\n',research,flags=re.M);notes={parts[i]:parts[i+1].strip() for i in range(1,len(parts),2)}
helpers={
'scoped_sa_server':('Enter server allocation mode for a direct server-interface test call.','Increment db_on_server on construction.','The standalone SQL harness normally acts as a client; these direct calls need server allocation rules.'),
'~scoped_sa_server':('Leave the temporary server allocation mode.','Decrement db_on_server when the scope ends.','Restore the previous mode, including when a fatal test assertion returns early.'),
'get_string_column':('Read a string from a SHOW result column.','Fetch a DB_VALUE, reject a missing string, copy it into std::string and clear the DB_VALUE.','The ownership test must distinguish the root row from p0 and p1 by table name.'),
'unqualified_table_name':('Remove a schema prefix from a reported table name.','Return the part after the last dot, or the whole name when no dot exists.','Ownership assertions should compare table names without depending on qualification.'),
'expect_sql_count':('Check one integer SQL result.','Run fetch_single_int and compare with the expected count under SCOPED_TRACE.','Repeated failure-path tests need a short check for rows that must remain or must not appear.'),
'expect_oos_records':('Check one table’s OOS file and chunk count.','Run SHOW HEAP OOS, inspect the two counts and require exactly one result row.','A successful SQL read alone cannot detect OOS data written for the wrong heap.'),
'failing_codec':('Install controlled codec failures on a private PR_TYPE copy.','The constructor replaces either the read or write callback with a failing lambda.','Test effective-key cleanup without modifying shared cached schema metadata.')}
tests={t['name']:t['en'] for t in meta['tests']}
text='''# PR #7600 — function inventory and direct calls

This is a lookup reference. Start with the [short English guide](start-here.en.md) or [Korean guide](start-here.ko.html) for the one-row example.

## Scope and result

Compare base `'''+base+'` with HEAD `'+head+'''`.

- **68 named definitions/test bodies:** 49 newly created, 19 modified, 0 deleted.
- Of these, **32 are in production source files:** 13 new and 19 modified. One of the 32 is a test-only bridge.
- **36 are in test files:** 29 new TEST_F bodies and 7 new named helpers/constructors/destructors. The 29 bodies comprise 28 SQL tests and one disabled vacuum regression.
- **Two new anonymous callback bodies** are listed separately. They are not included in the 68 named entries.
- Four unchanged functions previously described in the guide are listed after the inventory. They must not be mislabeled as modified.
- All **63 diff hunks** are accounted for in the final appendix, including declarations, comments, includes and the test timeout setting.

“Newly created” describes a new function definition, not necessarily new behavior. For example, the old locator_insert_force implementation becomes locator_insert_force_internal, while locator_insert_force remains as a modified wrapper. No deleted source function was found. Extraction relationships are explained in the entries.

## How to read the calls

**Caller → callee means a direct, explicitly named source call.** Conditional calls are included; an arrow does not mean the call always runs. Added/removed/retained compares call targets, so changed arguments to a retained target remain important in the prose.

Repository searches cover src/ and unit_tests/ at both revisions. Incoming links point to call sites. The expandable call details exclude uppercase macro invocations and member/function-pointer expressions. Constructor/destructor calls may be implicit; callback and GoogleTest dispatch are described separately. This is a source call index, not a compiler-resolved runtime graph or a list of calls observed in a running server. Test SQL reaches engine functions indirectly through SQL execution.

## Suggested first path

Follow locator_attribute_info_force, partition_prune_insert_by_attrinfo, partition_prune_insert_internal, partition_find_partition_for_attrinfo, then heap_attrinfo_get_effective_key. Return to locator_attribute_info_force to follow row construction. These are separate calls from the orchestration function, not one continuous linear call chain.

## Function index

| ID | Function | Status | Source file |
|---|---|---|---|
'''
for f in fs:text+=f'| {ids[f["name"]]} | {link(f["name"])} | {f["status"]} | `{f["path"]}` |\n'
text+='\n## Function explanations\n\n'
for f in fs:
 name=f['name'];fid=ids[name];a=f['base'];b=f['head'];text+=f'<a id="{fid.lower()}"></a>\n\n### {fid} · `{name}` — {f["status"]}\n\n'
 if f['path'].startswith('src/'):
  assert name in notes,name
  text+=notes[name]+'\n\n'
 else:
  if name in helpers:
   purpose,change,why=helpers[name]
  elif name.startswith('OosSqlShow.'):
   case=name.split('.',1)[1];purpose='Verify '+case+'.';change=tests[case];why='Add an executable check for this behavior; the test name alone is not evidence that it passed.'
  else:
   purpose='Reproduce a committed OOS value becoming unreadable after an UPDATE rollback and real vacuum.';change='Add a DISABLED_ test: commit an original value and a separate witness, roll back the replacement, read the original, vacuum the deleted witness, then read the original again.';why='Keep the regression available without pretending that a daemon wakeup proves reclamation or that the disabled test is passing. This is not a partition-specific test.'
  text+=f'**Purpose:** {purpose}\n\n**Change:** {change}\n\n**Reason:** {why}\n\n**Evidence:** {source(b,head)}. This definition is absent from the [base file]({url(f["path"],rev=base)}).\n\n'
  if name.startswith(('OosSqlShow.','OosRealVacuum.')):text+='**Caller:** GoogleTest invokes the macro-generated TestBody through its runner. This is framework dispatch, not a direct routing-function call.\n\n'
  elif name in ('scoped_sa_server','~scoped_sa_server'):text+='**Caller:** Automatic scoped_sa_server objects in the direct-interface SQL tests invoke construction/destruction through C++ lifetime rules. These implicit calls are not in the named-call index.\n\n'
  elif name=='failing_codec':text+='**Caller:** The enclosing EffectiveKeyCodecFailureClearsOutputAndPreservesAssignment test constructs this local type; callbacks run later through codec dispatch.\n\n'
 text+='<details>\n<summary>Direct call sites and base → HEAD call changes</summary>\n\n'
 for rev,label in [(base,'Base callers'),(head,'HEAD callers')]:
  incoming=callers(name,rev,f['path']);text+='**'+label+':** '
  if incoming:text+='; '.join(f'[{n}]({url(path,line,rev)})' for path,n,line in sorted(incoming))+'.\n\n'
  else:text+='No explicitly named call found within the searched source functions. See dispatch/lifetime notes where applicable.\n\n'
 ca=own_calls(a);cb=own_calls(b)
 for label,targets,rev,obj in [('Added targets',cb.keys()-ca.keys(),head,b),('Removed targets',ca.keys()-cb.keys(),base,a),('Retained targets',ca.keys()&cb.keys(),head,b)]:
  text+='**'+label+':** '+('; '.join(f'[{n}]({url(f["path"],(cb if rev==head else ca)[n],rev)})' for n in sorted(targets)) or 'None')+'.\n\n'
 text+='</details>\n\n'
text+='''## Anonymous callback bodies — newly created

These callbacks are nested inside the new failing_codec constructor (F number above). They are listed separately from named functions.

### A01 · failing_codec read callback

**Change and reason:** Assign f_data_readval a lambda that creates a partially decoded string, clones it into the output, then returns ER_FAILED. This checks that heap_attrinfo_get_effective_key clears partially produced output on a read failure while preserving the original assignment. Direct named calls in this callback are db_make_string and pr_clone_value. The codec invokes it indirectly; the enclosing test does not directly call those operations merely by defining the lambda. [Source](SOURCE1123).

### A02 · failing_codec write callback

**Change and reason:** Assign f_data_writeval a lambda that returns ER_FAILED immediately. This checks the write-failure branch before decoding starts. It contains no direct function call. Invocation is indirect through the codec. [Source](SOURCE1133).

## Unchanged context functions

These functions appeared in the earlier explanation. Their definitions are unchanged between base and HEAD.

- **heap_oos_insert_serialized_values — unchanged.** Takes the supplied class, obtains its heap and OOS file, then directly calls oos_insert_many. The PR changes which class its caller supplies. [Source](SOURCE631).
- **oos_insert_many — unchanged.** Writes the requested values to the supplied OOS file. It does not decide which partition should own the row. [Source](SOURCE2193).
- **locator_move_record — unchanged.** Inserts a moved row at the destination and then deletes it from the source. It is directly called by modified locator_update_force. [Source](SOURCE5402).
- **vacuum_oos_find_vfid_for_heap_record — unchanged.** Looks up the OOS file belonging to the heap being cleaned; this revision explicitly aborts on the missing-file condition. It explains the impact of wrong ownership, but is not a newly added step in the INSERT call path. [Source](SOURCE401).

## Diff-hunk coverage and changes outside definitions

Every hunk in the frozen diff is accounted for below. A declaration and its definition are one function identity, not two functions. Comments and blank separators are outside definition spans. Header signatures, test includes, local class scaffolding and TIMEOUT 300 are recorded here rather than called deleted/new functions. Changed return-type/storage-class lines next to a recovered GNU-style definition belong to that definition's declaration.

'''
for marker,path,line in [('SOURCE1123','unit_tests/oos/sql/test_oos_sql_show.cpp',1123),('SOURCE1133','unit_tests/oos/sql/test_oos_sql_show.cpp',1133),('SOURCE631','src/storage/heap_oos.cpp',631),('SOURCE2193','src/storage/oos_file.cpp',2193),('SOURCE5402','src/transaction/locator_sr.c',5402),('SOURCE401','src/query/vacuum_oos.cpp',401)]:text=text.replace(marker,url(path,line))
for h in coverage:
 text+=f'<details>\n<summary>H{h["id"]:02d} · {h["path"]}</summary>\n\n'
 text+='**Definitions:** '+('; '.join(link(n) for n in h['functions']) or 'No function body changes')+'.\n\n'
 text+='**Hunk explanation:** '+h['non_function_explanation']+'\n\n'
 if h['non_function_changes']:text+='**Outside definition spans:** '+str(len(h['non_function_changes']))+' added/deleted lines; exact side, line and text are recorded in [coverage data](evidence/function-hunk-coverage.json).\n\n'
 text+=f'[Read this hunk](review.ko.html#hunk-{h["id"]:02d}).\n\n</details>\n\n'
text+='''## Method and limits

The background research checked production definitions against source at both commits. An independent syntax extraction compared definitions, collected explicit named calls and mapped changed lines to function spans. GNU-style definition recovery handled preprocessor constructs that the whole-file parser missed. The index was reconciled with the manually reviewed production list. Test macro bodies, named helpers and the two callback lambdas were checked separately.

The call index covers both revision snapshots, including preprocessor-conditional source. It does not resolve dynamic function pointers, all implicit C++ operations, external libraries or build-configuration reachability. Repeated calls to one target are summarized as one target in outgoing lists; incoming links retain individual call sites. These limits do not turn a SQL-submission test into a direct engine caller.

No engine tests or benchmarks were run. New tests are classified by source addition, not execution success. Changes in this report are relative to the fixed commits above, not later PR updates.

Reproducible evidence: [function definitions](evidence/functions-ast.json), [source call index](evidence/callers-index.json), [all hunk mappings](evidence/function-hunk-coverage.json), [frozen diff](evidence/pr.diff). Generator scripts are retained under authoring/.
'''
(out/'functions.en.md').write_text(text)
print('Wrote functions.en.md:',len(fs),'named entries;',len(text.split()),'words')
