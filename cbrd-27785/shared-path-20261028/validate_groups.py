"""Check complete values at the local-flag boundary and across OOS chunk pages."""
import json
import os
from pathlib import Path
import measure_shared_reads as probe

root = probe.ROOT / 'group-boundaries'
root.mkdir(exist_ok=False)
install = Path(os.environ['CUBRID']).resolve()
registry = Path(os.environ['CUBRID_DATABASES']) / 'databases.txt'
entries = [line.split()[0] for line in registry.read_text().splitlines()
           if line.strip() and not line.lstrip().startswith('#')]
assert entries == ['oos27785'], entries
assert not probe.instance.servers(install), 'pre-existing benchmark server'
results = {}
try:
    probe.instance.command(['cubrid', 'server', 'start', 'oos27785'], root / 'start', timeout=45)
    assert len(probe.instance.servers(install)) == 1
    for count, size in [(8, 5000), (9, 5000), (2, 32000)]:
        table = f'sp_verify_{count}_{size}'
        columns = ', '.join(f'a{i} BIT VARYING({size * 8})' for i in range(count))
        values = ', '.join(probe.literal(size) for i in range(count))
        sql = (f'CREATE TABLE {table} (id INTEGER, {columns});\n'
               f'INSERT INTO {table} SELECT id, {values} FROM n WHERE id <= 20;\nCOMMIT;\n')
        probe.sql_run(sql, root / (table + '-setup'), install)
        checks = ' + '.join(f'CASE WHEN a{i} = {probe.literal(size)} THEN 1 ELSE 0 END'
                            for i in range(count))
        query = f'SELECT /*+ PARALLEL(0) NO_PARALLEL_HEAP_SCAN */ COUNT(*), SUM({checks}) FROM {table};\n'
        actual = probe.sql_run(query, root / (table + '-values'), install)
        assert actual == [(20, 20 * count)], (table, actual)
        probe.sql_run(f'SHOW HEAP OOS OF {table};\n', root / (table + '-storage'), install)
        row = next(line.split('\t') for line in (root / (table + '-storage.stdout')).read_text().splitlines() if line.strip())
        chunks = int(row[10])
        expected_chunks = 20 * count * (2 if size == 32000 else 1)
        assert chunks == expected_chunks, (table, chunks)
        results[table] = dict(rows=20, matched_values=actual[0][1], oos_chunks=chunks)
    manifest = dict(complete=True, dso_sha256=probe.bench.digest(install / 'lib/libcubrid.so.11.5'), results=results)
    (root / 'summary.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(results, indent=2))
finally:
    probe.instance.command(['cubrid', 'server', 'stop', 'oos27785'], root / 'stop', timeout=45, required=False)
    probe.instance.command(['cubrid', 'service', 'stop'], root / 'service-stop', timeout=45, required=False)
    assert not probe.instance.servers(install)
