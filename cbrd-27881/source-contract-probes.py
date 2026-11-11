#!/usr/bin/env python3
"""Run the two standalone source-contract probes.

Usage: python3 source-contract-probes.py SOURCE_GIT_REPO NEW_OUTPUT_DIR
Requires git, Python 3 and g++. The output directory must not exist and must
be outside the source worktree. This is not an HA reproduction.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REVISION = "50619ce53ef7b0e6bc8b468b2065ae7da4ef592f"
CACHE_HARNESS = r'''#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <cstring>

using HL_HEAPID = unsigned long;
#include "types.inc"
#include "macros.inc"
#include "options.inc"
#include "primes.inc"
#define NO_ERROR 0
#define ER_OUT_OF_VIRTUAL_MEMORY -3
#define ER_ERROR_SEVERITY 1
#define ARG_FILE_LINE __FILE__, __LINE__
#define MAX(a,b) ((a) > (b) ? (a) : (b))
#define free_and_init(p) do { free (p); (p) = NULL; } while (0)

static bool fail_vector = false;
static bool fail_entry = false;
static int vector_attempts = 0;
static int errors = 0;
static void er_set (int, const char *, int, int, int, size_t) { ++errors; }
static HL_HEAPID db_create_fixed_heap (int, int) { return 1; }
static void db_destroy_fixed_heap (HL_HEAPID) { }
static void *db_fixed_alloc (HL_HEAPID, size_t n)
{
  if (fail_entry) { fail_entry = false; return NULL; }
  return malloc (n);
}
static void *vector_malloc (size_t n)
{
  ++vector_attempts;
  if (fail_vector) { fail_vector = false; return NULL; }
  return malloc (n);
}
#include "size.inc"
#include "create.inc"
#define malloc vector_malloc
#include "rehash.inc"
#undef malloc
#include "lru.inc"
#include "get.inc"
#include "put_internal.inc"
#include "put.inc"

struct Owner { int key; int data; };
static unsigned int collide (const void *, unsigned int) { return 0; }
static int equal (const void *a, const void *b)
{
  return *static_cast<const int *> (a) == *static_cast<const int *> (b);
}

static void run (const char *name, bool fail_growth, bool fail_fixed)
{
  fail_vector = fail_growth;
  fail_entry = false;
  vector_attempts = 0;
  errors = 0;
  MHT_TABLE *ht = mht_create ("probe", 2, collide, equal);
  assert (ht && ht->size == 11 && ht->rehash_at == 7);
  Owner owners[8];
  for (int i = 0; i < 7; ++i)
    {
      owners[i] = {i, i + 100};
      assert (mht_put (ht, &owners[i].key, &owners[i].data) == &owners[i].key);
    }
  assert (ht->nentries == 7 && ht->ncollisions == 6 && vector_attempts == 0);
  owners[7] = {7, 107};
  fail_entry = fail_fixed;
  const void *result = mht_put (ht, &owners[7].key, &owners[7].data);
  int equal_key = 7;
  void *found = mht_get (ht, &equal_key);
  bool stored_key = false;
  for (HENTRY_PTR e = ht->table[0]; e; e = e->next)
    if (e->key == &owners[7].key) stored_key = true;
  bool stored_data = found == &owners[7].data;
  std::printf ("%s put=%s get_new_data=%s stored_key_pointer=%s entries=%u size=%u collisions=%u vector_attempts=%d errors=%d\n",
               name, result == NULL ? "NULL" : result == &owners[7].key ? "key" : "other",
               stored_data ? "yes" : found == NULL ? "NULL" : "other", stored_key ? "yes" : "no",
               ht->nentries, ht->size, ht->ncollisions, vector_attempts, errors);
  assert (fail_fixed ? (result == NULL && found == NULL && !stored_key && vector_attempts == 0 && errors == 0 && ht->nentries == 7)
                     : (result == (fail_growth ? NULL : &owners[7].key) && stored_data && stored_key
                        && vector_attempts == 1 && errors == (fail_growth ? 1 : 0) && ht->nentries == 8
                        && (fail_growth ? ht->size == 11 : ht->size > 11)));
  for (HENTRY_PTR e = ht->act_head; e; ) { HENTRY_PTR next = e->act_next; free (e); e = next; }
  free (ht->table);
  free (ht);
}

int main ()
{
  run ("baseline", false, false);
  run ("rehash_allocation_failure", true, false);
  run ("entry_allocation_failure", false, true);
}
'''
BUFFER_HARNESS = r'''#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
using INT16 = std::int16_t;
#include "recdes.inc"
#include "pool.inc"
#include "free-and-init.inc"
LA_RECDES_POOL la_recdes_pool;
#include "assignment.inc"
int main ()
{
  constexpr int capacity = 200;
  constexpr int page_size = 16384;
  RECDES descriptors[capacity] {};
  char area[capacity * page_size] {};
  for (int i = 0; i < capacity; ++i)
    {
      descriptors[i].data = area + i * page_size;
      descriptors[i].area_size = page_size;
    }
  la_recdes_pool = { descriptors, area, 0, page_size, capacity, true };
  RECDES *held = la_assign_recdes_from_pool ();
  std::strcpy (held->data, "first row");
  held->length = std::strlen (held->data);
  for (int i = 1; i < capacity; ++i)
    {
      RECDES *next = la_assign_recdes_from_pool ();
      assert (next != held);
      std::snprintf (next->data, page_size, "row %d", i + 1);
      next->length = std::strlen (next->data);
    }
  std::printf ("after 200 assignments: held length=%d data=%s next_idx=%d\n",
               held->length, held->data, la_recdes_pool.next_idx);
  assert (held->length == 9 && std::strcmp (held->data, "first row") == 0);
  RECDES *assigned_201 = la_assign_recdes_from_pool ();
  std::printf ("assignment 201: aliases_held=%d held_length_before_write=%d\n",
               assigned_201 == held, held->length);
  assert (assigned_201 == held && held->length == 0);
  std::strcpy (assigned_201->data, "heap row 201");
  assigned_201->length = std::strlen (assigned_201->data);
  std::printf ("after assignment 201 write: held length=%d data=%s\n", held->length, held->data);
  assert (std::strcmp (held->data, "heap row 201") == 0);
}
'''
PROBES = {
    "cache": {
        "harness": CACHE_HARNESS,
        "flags": ["-std=c++17", "-O0", "-g", "-Wall", "-Wextra", "-Werror"],
        "ranges": [
            ("types.inc", "src/base/memory_hash.h", 42, 77),
            ("macros.inc", "src/base/memory_alloc.h", 57, 61),
            ("options.inc", "src/base/memory_hash.c", 73, 85),
            ("primes.inc", "src/base/memory_hash.c", 867, 886),
            ("size.inc", "src/base/memory_hash.c", 922, 968),
            ("create.inc", "src/base/memory_hash.c", 1007, 1080),
            ("rehash.inc", "src/base/memory_hash.c", 1155, 1226),
            ("lru.inc", "src/base/memory_hash.c", 1544, 1571),
            ("get.inc", "src/base/memory_hash.c", 1470, 1501),
            ("put_internal.inc", "src/base/memory_hash.c", 1731, 1848),
            ("put.inc", "src/base/memory_hash.c", 1905, 1910),
        ],
    },
    "buffer": {
        "harness": BUFFER_HARNESS,
        "flags": ["-std=c++17", "-O0", "-g", "-Wall", "-Wextra", "-pedantic"],
        "ranges": [
            ("recdes.inc", "src/storage/storage_common.h", 221, 229),
            ("pool.inc", "src/transaction/log_applier.c", 400, 409),
            ("free-and-init.inc", "src/base/memory_alloc.h", 132, 138),
            ("assignment.inc", "src/transaction/log_applier.c", 2430, 2457),
        ],
    },
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    source = Path(sys.argv[1]).resolve(strict=True)
    output = Path(sys.argv[2]).resolve()
    root = Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], cwd=source, text=True).strip()).resolve()
    if output == root or root in output.parents:
        sys.exit("Output directory must be outside the source worktree")
    output.mkdir(parents=True, exist_ok=False)
    version = subprocess.check_output(["g++", "--version"], text=True).splitlines()[0]
    manifest = {"revision": REVISION, "compiler": version, "probes": {}}
    blobs = {}
    for name, spec in PROBES.items():
        directory = output / name
        directory.mkdir()
        ranges = []
        for filename, path, first, last in spec["ranges"]:
            if path not in blobs:
                blobs[path] = subprocess.check_output(
                    ["git", "show", f"{REVISION}:{path}"], cwd=source)
            lines = blobs[path].splitlines(keepends=True)
            if len(lines) < last:
                raise ValueError(f"{path} has fewer than {last} lines")
            chunk = b"".join(lines[first - 1:last])
            (directory / filename).write_bytes(chunk)
            ranges.append({"file": filename, "source": path, "first": first,
                           "last": last, "sha256": digest(chunk)})
        harness = spec["harness"].encode()
        (directory / "probe.cpp").write_bytes(harness)
        command = ["g++", *spec["flags"], "probe.cpp", "-o", "probe"]
        entry = {"command": command, "harness_sha256": digest(harness), "ranges": ranges}
        manifest["probes"][name] = entry
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        compile_result = subprocess.run(command, cwd=directory, capture_output=True)
        (directory / "compile.stdout").write_bytes(compile_result.stdout)
        (directory / "compile.stderr").write_bytes(compile_result.stderr)
        compile_result.check_returncode()
        run = subprocess.run([str(directory / "probe")], cwd=directory, capture_output=True)
        (directory / "output.txt").write_bytes(run.stdout)
        (directory / "run.stderr").write_bytes(run.stderr)
        run.check_returncode()
        entry["output_sha256"] = digest(run.stdout)
        print(f"{name} probe:")
        print(run.stdout.decode(), end="")
    manifest["source_blob_sha256"] = {path: digest(data) for path, data in blobs.items()}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Standalone extracted-code observations with controlled substitutes; not an HA reproduction.")


if __name__ == "__main__":
    main()
