# 커밋 고정 소스 찾아보기

새 구현은 로컬 전용이다. 아래 lookup은 working tree의 수정 여부와 관계없이 기록한 Git object를 읽는다.

HEAD: `28b65d18a9302b17d49281e06cb4621b86e9f24d`; merge-base: `fb567a629cdb390fff920542173fa36f454c74a0`.

<a id="locator-finalize"></a>
## locator-finalize

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:4953`

```cpp
locator_finalize_oos_record (THREAD_ENTRY *thread_p, const OID *class_oid, RECDES **record,
                            bool from_copyarea, bool from_workspace, heap_pending_record *pending,
                            heap_pending_record *received, RECDES *converted)
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '4953,5033p'
```

<a id="force-flags"></a>
## force-flags

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.h:140`

```cpp
  LC_FORCE_FLAG_NONE = 0x00,	/* default force behavior */
  LC_FORCE_FLAG_HAS_BU_LOCK = 0x01,	/* the transaction inserts under BU_LOCK (bulk insert) */
  LC_FORCE_FLAG_DONT_CHECK_FK = 0x02,	/* skip foreign key constraint checking */
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.h | sed -n '140,172p'
```

<a id="workspace-force"></a>
## workspace-force

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:7387`

```cpp
xlocator_force (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area, int num_ignore_error, int *ignore_error_list)
{
  LC_COPYAREA_MANYOBJS *mobjs;	/* Describe multiple objects in area */
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '7387,7467p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:7254`

```cpp
xlocator_force (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area, int num_ignore_error, int *ignore_error_list)
{
  LC_COPYAREA_MANYOBJS *mobjs;	/* Describe multiple objects in area */
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '7254,7334p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7254)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:6737`

```cpp
locator_force_for_multi_update (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area)
{
  LC_COPYAREA_MANYOBJS *mobjs;	/* Describe multiple objects in area */
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '6737,6817p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:6634`

```cpp
locator_force_for_multi_update (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area)
{
  LC_COPYAREA_MANYOBJS *mobjs;	/* Describe multiple objects in area */
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '6634,6714p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L6634)

<a id="pending-owner"></a>
## pending-owner

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_pending_record.hpp:32`

```cpp
class heap_pending_record
{
  public:
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_pending_record.hpp | sed -n '32,85p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_pending_record.cpp:51`

```cpp
heap_pending_record::~heap_pending_record ()
{
  for (auto &value : m_values)
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_pending_record.cpp | sed -n '51,92p'
```

<a id="inline-preservation"></a>
## inline-preservation

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:4967`

```cpp
      if (from_workspace && pending == nullptr && !OR_RECORD_HAS_OOS ((*record)->data)
          && !OR_RECORD_HAS_OOS (converted->data) && or_rep_id (*record) == or_rep_id (converted))
        {
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '4967,5047p'
```

<a id="heap-finalize"></a>
## heap-finalize

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp:208`

```cpp
heap_oos_finalize_record (THREAD_ENTRY *thread_p, const OID *destination, RECDES *record,
			  heap_pending_record *pending)
{
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp | sed -n '208,288p'
```

<a id="record-buffer-release"></a>
## record-buffer-release

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/record_descriptor.cpp:245`

```cpp
record_descriptor::set_external_buffer (char *buf, std::size_t buf_size)
{
  m_own_data.freemem ();
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/record_descriptor.cpp | sed -n '245,325p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/storage/record_descriptor.cpp:245`

```cpp
record_descriptor::set_external_buffer (char *buf, std::size_t buf_size)
{
  m_own_data.freemem ();
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/storage/record_descriptor.cpp | sed -n '245,325p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/record_descriptor.cpp#L245)

<a id="insert-force"></a>
## insert-force

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:5018`

```cpp
locator_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * recdes, int has_index,
		      int op_type, HEAP_SCANCACHE * scan_cache, int *force_count, int pruning_type,
		      PRUNING_CONTEXT * pcontext, FUNC_PRED_UNPACK_INFO * func_preds,
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '5018,5098p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:4952`

```cpp
locator_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * recdes, int has_index,
		      int op_type, HEAP_SCANCACHE * scan_cache, int *force_count, int pruning_type,
		      PRUNING_CONTEXT * pcontext, FUNC_PRED_UNPACK_INFO * func_preds,
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '4952,5032p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L4952)

<a id="update-force"></a>
## update-force

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:5554`

```cpp
locator_update_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * oldrecdes,
		      RECDES * recdes, int has_index, ATTR_ID * att_id, int n_att_id, int op_type,
		      HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk, REPL_INFO_TYPE repl_info_type,
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '5554,5634p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:5465`

```cpp
locator_update_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid, OID * oid, RECDES * oldrecdes,
		      RECDES * recdes, int has_index, ATTR_ID * att_id, int n_att_id, int op_type,
		      HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk, REPL_INFO_TYPE repl_info_type,
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '5465,5545p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5465)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:5449`

```cpp
locator_move_record (THREAD_ENTRY * thread_p, HFID * old_hfid, OID * old_class_oid, OID * obj_oid, OID * new_class_oid,
		     HFID * new_class_hfid, RECDES * recdes, HEAP_SCANCACHE * scan_cache, int op_type, int has_index,
		     int *force_count, PRUNING_CONTEXT * context, MVCC_REEV_DATA * mvcc_reev_data, bool need_locking,
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '5449,5529p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:5365`

```cpp
locator_move_record (THREAD_ENTRY * thread_p, HFID * old_hfid, OID * old_class_oid, OID * obj_oid, OID * new_class_oid,
		     HFID * new_class_hfid, RECDES * recdes, HEAP_SCANCACHE * scan_cache, int op_type, int has_index,
		     int *force_count, PRUNING_CONTEXT * context, MVCC_REEV_DATA * mvcc_reev_data, bool need_locking)
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '5365,5445p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L5365)

<a id="comparison-capture"></a>
## comparison-capture

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:54`

```cpp
    void capture (const OID &oid, OID class_oid, const HFID &hfid,
		  std::vector<char> &bytes, RECDES &record)
    {
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp | sed -n '54,134p'
```

<a id="comparison-check"></a>
## comparison-check

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:196`

```cpp
    void check (const std::string &columns, const std::string &values, const std::string &predicate,
		const storage_expectation &expected)
    {
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp | sed -n '196,276p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:202`

```cpp
    void check (const std::string &columns, const std::string &values, const std::string &predicate,
		const storage_expectation &current, const char *alter, const storage_expectation &old)
    {
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp | sed -n '202,282p'
```

<a id="comparison-storage"></a>
## comparison-storage

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:75`

```cpp
    void expect_storage (const RECDES &record, const OID &class_oid, const storage_expectation &expected)
    {
      int cache_index = -1;
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp | sed -n '75,155p'
```

<a id="comparison-values"></a>
## comparison-values

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:127`

```cpp
    void compare (const RECDES &a, const RECDES &b, const std::vector<const TP_DOMAIN *> &domains)
    {
      auto *thread = thread_get_thread_entry_info ();
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp | sed -n '127,207p'
```

<a id="comparison-schema"></a>
## comparison-schema

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:355`

```cpp
TEST_F (OosWorkspaceBytes, OldDiskRepresentationIsConvertedBeforeWorkspaceSerialization)
{
  const storage_expectation sql_row = {{true}, OR_BYTE_SIZE, 5008};
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp | sed -n '355,398p'
```

<a id="comparison-cases"></a>
## comparison-cases

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:291`

```cpp
TEST_F (OosWorkspaceBytes, TinyNullAndEmptyValues)
{
  check ("id INT, a BIT VARYING, b VARCHAR, c BIT VARYING", "1, NULL, '', X''",
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp | sed -n '291,371p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp:368`

```cpp
TEST_P (OosWorkspaceSizeBoundary, SerializedSizesMatchValueSizes)
{
  const std::string size = std::to_string (GetParam ());
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp | sed -n '368,398p'
```

<a id="utility-run"></a>
## utility-run

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/test_oos_workspace.cpp:69`

```cpp
    std::string run (std::vector<std::string> args, const std::string &input = "",
		     const std::string &expected_error = "")
    {
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/test_oos_workspace.cpp | sed -n '69,149p'
```

<a id="utility-seed"></a>
## utility-seed

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/test_oos_workspace.cpp:176`

```cpp
    void seed_workspace ()
    {
      sql ("CREATE TABLE t_sql(id INTEGER PRIMARY KEY, v BIT VARYING); COMMIT;\n"
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/test_oos_workspace.cpp | sed -n '176,256p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/test_oos_workspace.cpp:304`

```cpp
TEST_F (OosWorkspaceTest, WorkspaceUpdateRollbackCommitAndDelete)
{
  seed_references ();
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/test_oos_workspace.cpp | sed -n '304,384p'
```

<a id="test-registration"></a>
## test-registration

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/CMakeLists.txt:206`

```cpp
add_test(NAME test_oos_workspace COMMAND test_oos_workspace)
set_tests_properties(test_oos_workspace PROPERTIES RUN_SERIAL TRUE TIMEOUT 240)
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/CMakeLists.txt | sed -n '206,207p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/CMakeLists.txt:50`

```cpp
add_test(NAME test_oos_sql_workspace_bytes COMMAND test_oos_sql_workspace_bytes)

set_tests_properties(
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:unit_tests/oos/sql/CMakeLists.txt | sed -n '50,76p'
```

<a id="value-reference"></a>
## value-reference

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp:57`

```cpp
heap_oos_value_ref::encode_pending (char *stub, DB_BIGINT length, int index)
{
  OR_BUF buf;
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp | sed -n '57,137p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp:76`

```cpp
heap_oos_value_ref::decode_stub (const RECDES &record, char *stub, heap_oos_value_ref &ref,
				 const heap_pending_record *pending)
{
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp | sed -n '76,156p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp:127`

```cpp
heap_oos_value_ref::read_into (THREAD_ENTRY *thread_p, oos_buffer destination) const
{
  if (destination.size () != m_length || destination.data () == nullptr)
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp | sed -n '127,207p'
```

<a id="attribute-readers"></a>
## attribute-readers

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c:11600`

```cpp
heap_attrinfo_read_dbvalues (THREAD_ENTRY * thread_p, const OID * inst_oid, RECDES * recdes,
			     HEAP_CACHE_ATTRINFO * attr_info, const heap_pending_record * pending)
{
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c | sed -n '11600,11680p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c:11569`

```cpp
heap_attrinfo_read_dbvalues (THREAD_ENTRY * thread_p, const OID * inst_oid, RECDES * recdes,
			     HEAP_CACHE_ATTRINFO * attr_info)
{
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c | sed -n '11569,11649p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L11569)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp:792`

```cpp
heap_oos_read_grouped_payloads (THREAD_ENTRY *thread_p, RECDES *recdes, HEAP_CACHE_ATTRINFO *attr_info,
				std::vector<RECDES> &oos_payloads, bool *grouped_applied,
				const heap_pending_record *pending)
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp | sed -n '792,872p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_oos.cpp:515`

```cpp
heap_oos_read_grouped_payloads (THREAD_ENTRY *thread_p, RECDES *recdes, HEAP_CACHE_ATTRINFO *attr_info,
				std::vector<RECDES> &oos_payloads, bool *grouped_applied)
{
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_oos.cpp | sed -n '515,595p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_oos.cpp#L515)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c:11549`

```cpp
heap_midxkey_get_oos_extra_size (RECDES * recdes, OR_ATTRIBUTE * att, const heap_pending_record * pending)
{
  /* Only variable attributes can be OOS */
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c | sed -n '11549,11629p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c:11514`

```cpp
heap_midxkey_get_oos_extra_size (RECDES * recdes, OR_ATTRIBUTE * att)
{
  /* Only variable attributes can be OOS */
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c | sed -n '11514,11594p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L11514)

<a id="heap-prepare"></a>
## heap-prepare

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c:13279`

```cpp
heap_attrinfo_prepare_record (THREAD_ENTRY *thread_p, HEAP_CACHE_ATTRINFO *attr_info, RECDES *old_recdes,
                             heap_pending_record *pending, bool copy_lobs)
{
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c | sed -n '13279,13359p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c:13316`

```cpp
heap_prepare_oos_record (THREAD_ENTRY *thread_p, const OID *source_class, RECDES *source,
                         heap_pending_record *pending)
{
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c | sed -n '13316,13396p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c:13593`

```cpp
heap_attrinfo_transform_variable_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, OR_BUF * buf,
					  char **ptr_varvals, heap_oos_column_plan * oos_plan, int index,
					  int offset_size, int header_size, int lob_create_flag)
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c | sed -n '13593,13673p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c:13481`

```cpp
heap_attrinfo_transform_variable_to_disk (THREAD_ENTRY * thread_p, HEAP_CACHE_ATTRINFO * attr_info, OR_BUF * buf,
					  char **ptr_varvals, heap_oos_column_plan * oos_plan, int index,
					  int offset_size, int header_size, int lob_create_flag)
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c | sed -n '13481,13561p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L13481)

<a id="loader-queue"></a>
## loader-queue

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/loaddb/load_server_loader.hpp:116`

```cpp
      std::vector<heap_pending_record> m_recdes_collected;
      std::size_t m_retained_bytes;
      int m_pruning_type;
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/loaddb/load_server_loader.hpp | sed -n '116,127p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/loaddb/load_server_loader.cpp:668`

```cpp
  server_object_loader::process_line (constant_type *cons)
  {
    if (m_session.is_failed ())
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/loaddb/load_server_loader.cpp | sed -n '668,748p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/loaddb/load_server_loader.cpp:635`

```cpp
  server_object_loader::process_line (constant_type *cons)
  {
    if (m_session.is_failed ())
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/loaddb/load_server_loader.cpp | sed -n '635,715p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/loaddb/load_server_loader.cpp#L635)

<a id="loader-flush"></a>
## loader-flush

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/loaddb/load_server_loader.cpp:776`

```cpp
  server_object_loader::flush_records ()
  {
    int force_count = 0;
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/loaddb/load_server_loader.cpp | sed -n '776,856p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/loaddb/load_server_loader.cpp:737`

```cpp
  server_object_loader::flush_records ()
  {
    int force_count = 0;
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/loaddb/load_server_loader.cpp | sed -n '737,817p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/loaddb/load_server_loader.cpp#L737)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/loaddb/load_server_loader.cpp:102`

```cpp
  server_class_installer::install_class (string_type *class_name, class_command_spec_type *cmd_spec)
  {
    if (class_name == NULL || class_name->val == NULL)
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/loaddb/load_server_loader.cpp | sed -n '102,182p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/loaddb/load_server_loader.cpp:100`

```cpp
  server_class_installer::install_class (string_type *class_name, class_command_spec_type *cmd_spec)
  {
    if (class_name == NULL || class_name->val == NULL)
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/loaddb/load_server_loader.cpp | sed -n '100,180p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/loaddb/load_server_loader.cpp#L100)

<a id="bulk-finalize"></a>
## bulk-finalize

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:14192`

```cpp
locator_multi_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid,
			    std::vector<heap_pending_record> &recdes, int has_index, int op_type,
			    HEAP_SCANCACHE * scan_cache, int *force_count, int pruning_type, PRUNING_CONTEXT * pcontext,
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '14192,14272p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:14027`

```cpp
locator_multi_insert_force (THREAD_ENTRY * thread_p, HFID * hfid, OID * class_oid,
			    const std::vector<record_descriptor> &recdes, int has_index, int op_type,
			    HEAP_SCANCACHE * scan_cache, int *force_count, int pruning_type, PRUNING_CONTEXT * pcontext,
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '14027,14107p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L14027)

<a id="partition-routing"></a>
## partition-routing

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/query/partition.c:3468`

```cpp
partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_oid, RECDES * recdes,
				     OID * partition_oid, HFID * partition_hfid, const heap_pending_record * pending)
{
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/query/partition.c | sed -n '3468,3548p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/query/partition.c:3467`

```cpp
partition_find_partition_for_record (PRUNING_CONTEXT * pinfo, const OID * class_oid, RECDES * recdes,
				     OID * partition_oid, HFID * partition_hfid)
{
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/query/partition.c | sed -n '3467,3547p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/partition.c#L3467)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/query/partition_sr.h:115`

```cpp
extern int partition_prune_insert (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes,
				   HEAP_SCANCACHE * scan_cache, PRUNING_CONTEXT * pcontext, int op_type,
				   OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid,
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/query/partition_sr.h | sed -n '115,144p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/query/partition_sr.h:114`

```cpp
extern int partition_prune_insert (THREAD_ENTRY * thread_p, const OID * class_oid, RECDES * recdes,
				   HEAP_SCANCACHE * scan_cache, PRUNING_CONTEXT * pcontext, int op_type,
				   OID * pruned_class_oid, HFID * pruned_hfid, OID * superclass_oid);
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/query/partition_sr.h | sed -n '114,140p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/partition_sr.h#L114)

<a id="duplicate-probes"></a>
## duplicate-probes

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/query/query_executor.c:12045`

```cpp
qexec_remove_duplicates_for_replace (THREAD_ENTRY * thread_p, HEAP_SCANCACHE * scan_cache,
				     HEAP_CACHE_ATTRINFO * attr_info, HEAP_CACHE_ATTRINFO * index_attr_info,
				     const HEAP_IDX_ELEMENTS_INFO * idx_info, int op_type, int pruning_type,
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/query/query_executor.c | sed -n '12045,12125p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/query/query_executor.c:12044`

```cpp
qexec_remove_duplicates_for_replace (THREAD_ENTRY * thread_p, HEAP_SCANCACHE * scan_cache,
				     HEAP_CACHE_ATTRINFO * attr_info, HEAP_CACHE_ATTRINFO * index_attr_info,
				     const HEAP_IDX_ELEMENTS_INFO * idx_info, int op_type, int pruning_type,
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/query/query_executor.c | sed -n '12044,12124p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/query_executor.c#L12044)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/query/query_executor.c:12265`

```cpp
qexec_oid_of_duplicate_key_update (THREAD_ENTRY * thread_p, HEAP_SCANCACHE ** pruned_partition_scan_cache,
				   HEAP_SCANCACHE * scan_cache, HEAP_CACHE_ATTRINFO * attr_info,
				   HEAP_CACHE_ATTRINFO * index_attr_info, const HEAP_IDX_ELEMENTS_INFO * idx_info,
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/query/query_executor.c | sed -n '12265,12345p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/query/query_executor.c:12276`

```cpp
qexec_oid_of_duplicate_key_update (THREAD_ENTRY * thread_p, HEAP_SCANCACHE ** pruned_partition_scan_cache,
				   HEAP_SCANCACHE * scan_cache, HEAP_CACHE_ATTRINFO * attr_info,
				   HEAP_CACHE_ATTRINFO * index_attr_info, const HEAP_IDX_ELEMENTS_INFO * idx_info,
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/query/query_executor.c | sed -n '12276,12356p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/query/query_executor.c#L12276)

<a id="sql-and-redistribution"></a>
## sql-and-redistribution

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:7734`

```cpp
locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID * oid, HEAP_CACHE_ATTRINFO * attr_info,
			      ATTR_ID * att_id, int n_att_id, LC_COPYAREA_OPERATION operation, int op_type,
			      HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk,
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '7734,7814p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:7586`

```cpp
locator_attribute_info_force (THREAD_ENTRY * thread_p, const HFID * hfid, OID * oid, HEAP_CACHE_ATTRINFO * attr_info,
			      ATTR_ID * att_id, int n_att_id, LC_COPYAREA_OPERATION operation, int op_type,
			      HEAP_SCANCACHE * scan_cache, int *force_count, bool not_check_fk,
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '7586,7666p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7586)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:13052`

```cpp
redistribute_partition_data (THREAD_ENTRY * thread_p, OID * class_oid, int no_oids, OID * oid_list)
{
  int error = NO_ERROR;
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '13052,13132p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:12907`

```cpp
redistribute_partition_data (THREAD_ENTRY * thread_p, OID * class_oid, int no_oids, OID * oid_list)
{
  int error = NO_ERROR;
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '12907,12987p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L12907)

<a id="storage-validation"></a>
## storage-validation

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp:146`

```cpp
heap_oos_validate_disk_record (THREAD_ENTRY *thread_p, const OID *class_oid, const RECDES *record)
{
  if (OID_IS_ROOTOID (class_oid) || (record != nullptr && record->type == REC_ASSIGN_ADDRESS))
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_oos.cpp | sed -n '146,226p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c:25161`

```cpp
heap_insert_logical (THREAD_ENTRY * thread_p, HEAP_OPERATION_CONTEXT * context, PGBUF_WATCHER * home_hint_p)
{
  bool is_mvcc_op;
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c | sed -n '25161,25241p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c:25003`

```cpp
heap_insert_logical (THREAD_ENTRY * thread_p, HEAP_OPERATION_CONTEXT * context, PGBUF_WATCHER * home_hint_p)
{
  bool is_mvcc_op;
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c | sed -n '25003,25083p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L25003)

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c:25593`

```cpp
heap_update_logical (THREAD_ENTRY * thread_p, HEAP_OPERATION_CONTEXT * context)
{
  bool is_mvcc_op;
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c | sed -n '25593,25673p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c:25418`

```cpp
heap_update_logical (THREAD_ENTRY * thread_p, HEAP_OPERATION_CONTEXT * context)
{
  bool is_mvcc_op;
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c | sed -n '25418,25498p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L25418)

<a id="fetch-export"></a>
## fetch-export

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:2184`

```cpp
locator_copyarea_add_fetch (const OID * class_oid, const OID * oid, const RECDES * recdes, int offset,
			    LC_COPYAREA_MANYOBJS * mobjs, LC_COPYAREA_ONEOBJ * obj)
{
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '2184,2264p'
```

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c:15900`

```cpp
heap_prefetch (THREAD_ENTRY * thread_p, OID * class_oid, const OID * oid, LC_COPYAREA_DESC * prefetch)
{
  VPID vpid;
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/storage/heap_file.c | sed -n '15900,15980p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c:15749`

```cpp
heap_prefetch (THREAD_ENTRY * thread_p, OID * class_oid, const OID * oid, LC_COPYAREA_DESC * prefetch)
{
  VPID vpid;
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/storage/heap_file.c | sed -n '15749,15829p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/storage/heap_file.c#L15749)

<a id="replication-topop"></a>
## replication-topop

현재 로컬 구현: `28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c:7127`

```cpp
xlocator_repl_force (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area, LC_COPYAREA ** reply_area)
{
  LC_COPYAREA_MANYOBJS *mobjs;	/* Describe multiple objects in area */
```

```sh
git show 28b65d18a9302b17d49281e06cb4621b86e9f24d:src/transaction/locator_sr.c | sed -n '7127,7207p'
```

merge-base 구현: `fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c:7021`

```cpp
xlocator_repl_force (THREAD_ENTRY * thread_p, LC_COPYAREA * force_area, LC_COPYAREA ** reply_area)
{
  LC_COPYAREA_MANYOBJS *mobjs;	/* Describe multiple objects in area */
```

```sh
git show fb567a629cdb390fff920542173fa36f454c74a0:src/transaction/locator_sr.c | sed -n '7021,7101p'
```

[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/fb567a629cdb390fff920542173fa36f454c74a0/src/transaction/locator_sr.c#L7021)
