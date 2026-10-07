#!/usr/bin/env python3
"""Build revision-pinned reviewer evidence from committed source and saved receipts."""

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path


HEAD = "28b65d18a9302b17d49281e06cb4621b86e9f24d"
BASE = "fb567a629cdb390fff920542173fa36f454c74a0"
DEPENDENCY = "4be72fc209ae9cb8aa1709573d7d0ae7fc06df7c"
PUBLISHED = "1c660d22e4340ee707336ad08c8b4bf4b69744de"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    args = parser.parse_args()
    destination = Path(__file__).resolve().parent

    def git(*command):
        return subprocess.check_output(["git", *command], cwd=args.source)

    def read(revision, path):
        return git("show", revision + ":" + path).decode()

    def save(name, value):
        (destination / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    locator = "src/transaction/locator_sr.c"
    heap = "src/storage/heap_file.c"
    oos = "src/storage/heap_oos.cpp"
    comparison = "unit_tests/oos/sql/test_oos_sql_workspace_bytes.cpp"
    utility = "unit_tests/oos/test_oos_workspace.cpp"
    loader = "src/loaddb/load_server_loader.cpp"
    query = "src/query/query_executor.c"
    locations = {
        "locator-finalize": [(locator, r"^locator_finalize_oos_record \(")],
        "force-flags": [("src/transaction/locator_sr.h", r"^  LC_FORCE_FLAG_NONE")],
        "workspace-force": [(locator, r"^xlocator_force \("), (locator, r"^locator_force_for_multi_update \(")],
        "pending-owner": [("src/storage/heap_pending_record.hpp", r"^class heap_pending_record"), ("src/storage/heap_pending_record.cpp", r"^heap_pending_record::~")],
        "inline-preservation": [(locator, r"^      if \(from_workspace && pending == nullptr")],
        "heap-finalize": [(oos, r"^heap_oos_finalize_record \(")],
        "record-buffer-release": [("src/storage/record_descriptor.cpp", r"^record_descriptor::set_external_buffer \(char")],
        "insert-force": [(locator, r"^locator_insert_force \(")],
        "update-force": [(locator, r"^locator_update_force \("), (locator, r"^locator_move_record \(")],
        "comparison-capture": [(comparison, r"^    void capture \(")],
        "comparison-check": [(comparison, r"^    void check \(")],
        "comparison-storage": [(comparison, r"^    void expect_storage \(")],
        "comparison-values": [(comparison, r"^    void compare \(")],
        "comparison-schema": [(comparison, r"^TEST_F \(OosWorkspaceBytes, OldDiskRepresentation")],
        "comparison-cases": [(comparison, r"^TEST_F \(OosWorkspaceBytes, TinyNull"), (comparison, r"^TEST_P \(OosWorkspaceSizeBoundary")],
        "utility-run": [(utility, r"^    std::string run \(")],
        "utility-seed": [(utility, r"^    void seed_workspace \("), (utility, r"^TEST_F \(OosWorkspaceTest, WorkspaceUpdateRollback")],
        "test-registration": [("unit_tests/oos/CMakeLists.txt", r"^add_test\(NAME test_oos_workspace"), ("unit_tests/oos/sql/CMakeLists.txt", r"^add_test\(NAME test_oos_sql_workspace_bytes")],
        "value-reference": [(oos, r"^heap_oos_value_ref::encode_pending"), (oos, r"^heap_oos_value_ref::decode_stub"), (oos, r"^heap_oos_value_ref::read_into")],
        "attribute-readers": [(heap, r"^heap_attrinfo_read_dbvalues \("), (oos, r"^heap_oos_read_grouped_payloads \("), (heap, r"^heap_midxkey_get_oos_extra_size \(")],
        "heap-prepare": [(heap, r"^heap_attrinfo_prepare_record \("), (heap, r"^heap_prepare_oos_record \("), (heap, r"^heap_attrinfo_transform_variable_to_disk \(")],
        "loader-queue": [("src/loaddb/load_server_loader.hpp", r"^      std::vector<heap_pending_record>"), (loader, r"^  server_object_loader::process_line \(")],
        "loader-flush": [(loader, r"^  server_object_loader::flush_records \("), (loader, r"^  server_class_installer::install_class \(string_type")],
        "bulk-finalize": [(locator, r"^locator_multi_insert_force \(")],
        "partition-routing": [("src/query/partition.c", r"^partition_find_partition_for_record \("), ("src/query/partition_sr.h", r"^extern int partition_prune_insert")],
        "duplicate-probes": [(query, r"^qexec_remove_duplicates_for_replace \("), (query, r"^qexec_oid_of_duplicate_key_update \(")],
        "sql-and-redistribution": [(locator, r"^locator_attribute_info_force \("), (locator, r"^redistribute_partition_data \(")],
        "storage-validation": [(oos, r"^heap_oos_validate_disk_record \("), (heap, r"^heap_insert_logical \("), (heap, r"^heap_update_logical \(")],
        "fetch-export": [(locator, r"^locator_copyarea_add_fetch \("), (heap, r"^heap_prefetch \(")],
        "replication-topop": [(locator, r"^xlocator_repl_force \(")],
    }
    source_refs = []
    markdown = ["# 커밋 고정 소스 찾아보기", "", "새 구현은 로컬 전용이다. 아래 lookup은 working tree의 수정 여부와 관계없이 기록한 Git object를 읽는다.", "", "HEAD: `" + HEAD + "`; merge-base: `" + BASE + "`.", ""]
    for anchor, queries in locations.items():
        markdown.extend(['<a id="' + anchor + '"></a>', "## " + anchor, ""])
        for path, pattern in queries:
            for revision, label in ((HEAD, "현재 로컬 구현"), (BASE, "merge-base 구현")):
                result = subprocess.run(["git", "show", revision + ":" + path], cwd=args.source, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                if result.returncode:
                    continue
                lines = result.stdout.decode().splitlines()
                matches = [(i + 1, line) for i, line in enumerate(lines) if re.search(pattern, line)]
                if revision == HEAD:
                    assert matches, (anchor, path, pattern)
                for number, line in matches:
                    source_refs.append({"anchor": anchor, "revision": revision, "path": path, "line": number, "text": line, "pattern": pattern})
                    markdown.extend([f"{label}: `{revision}:{path}:{number}`", "", "```cpp", "\n".join(lines[number - 1:number + 2]), "```", "", "```sh", f"git show {revision}:{path} | sed -n '{number},{min(number + 80, len(lines))}p'", "```", ""])
                    if revision == BASE:
                        markdown.extend([f"[게시된 merge-base의 같은 위치](https://github.com/CUBRID/cubrid/blob/{revision}/{path}#L{number})", ""])
    (destination / "source-map.md").write_text("\n".join(markdown))
    save("source-references.json", source_refs)

    groups = {
        "cubrid/CMakeLists.txt": ["dependency-callers"],
        "sa/CMakeLists.txt": ["dependency-callers"],
        "src/loaddb/load_server_loader.cpp": ["force-origin", "dependency-loader"],
        "src/loaddb/load_server_loader.hpp": ["dependency-loader"],
        "src/query/partition.c": ["dependency-loader"],
        "src/query/partition_sr.h": ["dependency-loader"],
        "src/query/query_executor.c": ["dependency-duplicates"],
        "src/storage/heap_file.c": ["prepare-finalize-contract", "pending-reference-contract", "dependency-publication"],
        "src/storage/heap_file.h": ["prepare-finalize-contract", "pending-reference-contract", "dependency-publication"],
        "src/storage/heap_oos.cpp": ["pending-reference-contract", "prepare-finalize-contract", "dependency-publication"],
        "src/storage/heap_oos.hpp": ["pending-reference-contract", "prepare-finalize-contract"],
        "src/storage/heap_pending_record.cpp": ["pending-owner-contract"],
        "src/storage/heap_pending_record.hpp": ["pending-owner-contract"],
        "src/transaction/locator.h": ["dependency-publication"],
        "src/transaction/locator_sr.c": ["force-origin", "received-owner", "inline-publication", "force-routing", "dependency-duplicates", "dependency-publication"],
        "src/transaction/locator_sr.h": ["force-origin", "dependency-duplicates"],
        "unit_tests/oos/CMakeLists.txt": ["utility-tests"],
        "unit_tests/oos/scripts/benchmark_workspace_oos.sh": ["performance-evidence"],
        "unit_tests/oos/sql/CMakeLists.txt": ["utility-tests"],
        "unit_tests/oos/sql/test_oos_sql_deferred_write.cpp": ["dependency-callers", "verification"],
        "unit_tests/oos/sql/test_oos_sql_heap_fixture.hpp": ["dependency-callers"],
        "unit_tests/oos/sql/test_oos_sql_show.cpp": ["dependency-callers"],
        comparison: ["stored-row-comparison", "comparison-contract"],
        "unit_tests/oos/test_oos_eager_diagnostics.cpp": ["dependency-callers"],
        "unit_tests/oos/test_oos_real_vacuum_server.cpp": ["dependency-callers"],
        "unit_tests/oos/test_oos_server.cpp": ["dependency-callers", "dependency-publication"],
        utility: ["utility-tests", "utility-timeout"],
    }
    paths = git("diff", "--name-only", BASE, HEAD).decode().splitlines()
    task_paths = set(git("diff", "--name-only", DEPENDENCY, "1932b3ec").decode().splitlines())
    assert set(paths) == set(groups)
    coverage = []
    for path in paths:
        patch = git("diff", "--unified=0", BASE, HEAD, "--", path).decode()
        coverage.append({"path": path, "guide_anchors": groups[path], "pr7925_task_file": path in task_paths, "head_blob": git("rev-parse", HEAD + ":" + path).decode().strip(), "head_sha256": hashlib.sha256(git("show", HEAD + ":" + path)).hexdigest(), "hunks": re.findall(r"^@@.*$", patch, re.M)})
    save("coverage.json", {"base": BASE, "head": HEAD, "files": coverage, "file_count": len(coverage), "task_file_count": len(task_paths)})

    streams = {}
    for name in ("inline", "reviews", "discussion"):
        pages = json.loads((args.receipts / (name + "-pages.json")).read_text())
        items = [item for page in pages for item in page]
        streams[name] = {"pages": len(pages), "item_count": len(items), "items": [{key: item.get(key) for key in ("id", "html_url", "body", "created_at", "submitted_at", "commit_id", "path", "line", "original_line", "in_reply_to_id", "state")} | {"author": (item.get("user") or {}).get("login")} for item in items if item.get("state") != "PENDING"]}
    save("context.json", {"collected_at": json.loads((args.receipts / "integration-receipt.json").read_text())["observed_at"], "pr": json.loads((args.receipts / "pr.json").read_text()), "checks": json.loads((args.receipts / "pr-checks.json").read_text()), "comments": streams, "jira_live_query": "cubrid-jira search CBRD-27424", "jira_status": "Develop", "jira_resolution": "Unresolved", "metadata_is_snapshot": True, "local_head": HEAD, "merge_base": git("merge-base", BASE, HEAD).decode().strip()})

    log = (args.receipts / "rebased-ctest.log").read_text(errors="replace")
    run = re.findall(r"^([0-9]+): \[ RUN\s+\] (.+)$", log, re.M)
    passed = re.findall(r"^([0-9]+): \[\s+OK\s+\] (.+?) \([0-9]+ ms\)$", log, re.M)
    summaries = re.findall(r"^([0-9]+): \[==========\] ([0-9]+) tests? from .+ ran\.", log, re.M)
    failed = re.findall(r"^\d+: \[\s+FAILED\s+\].*$", log, re.M)
    skipped = re.findall(r"^\d+: \[\s+SKIPPED\s+\].*$", log, re.M)
    disabled = re.findall(r"^\d+:.*DISABLED TEST.*$", log, re.M)
    assert Counter(run) == Counter(passed)
    assert len(run) == 374 and len(summaries) == 32
    assert not (failed or skipped or disabled)
    assert (args.receipts / "rebased-ctest.exit").read_text().strip() == "0"
    save("ctest-results.json", {"source_commit": HEAD, "ctest_command": "ctest --test-dir build_preset_debug_gcc --output-on-failure --verbose", "local_entry_command": "direnv exec . just ctest", "ctests": 38, "ctests_passed": 38, "gtest_binaries": len(summaries), "gtests_run": len(run), "gtests_passed": len(passed), "failures": failed, "skips": skipped, "disabled": disabled, "elapsed_seconds": 384.47, "count_method": "All RUN/OK identities and final binary summaries parsed from this invocation's verbose log; no new XML claim.", "cases": [{"ctest_number": int(number), "name": name} for number, name in run]})
    for name in ("integration-receipt.json", "rebased-build.log", "rebased-ctest.log", "cleanup-doctor.log"):
        (destination / name).write_bytes((args.receipts / name).read_bytes())
    print(json.dumps({"files_covered": len(coverage), "source_references": len(source_refs), "source_anchors": len(locations), "gtests_passed": len(passed)}))


if __name__ == "__main__":
    main()
