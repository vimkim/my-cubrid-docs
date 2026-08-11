# Expected Oracle

- 각 `csql` run은 exit 0이고 `inserted_rows = 20000`을 출력한다.
- 각 run의 histogram에서 `Num_data_page_dirties`가 0보다 크다.
- 세 workload·background activity·online-backup trigger를 포함한 active observation window에서 `Num_data_page_iowrites(after) > Num_data_page_iowrites(before)`다. 이 증가는 exact caller에 귀속하지 않는다.
- DWB 경로의 집계 때문에 증가량을 unique/logical page 수로 해석하지 않는다.
- `Num_data_page_flushed`는 모든 flush를 세는 믿을 만한 대체 지표가 아니므로 oracle로 쓰지 않는다.
- cleanup 뒤 `sxaio_codex` DB와 이 실험의 statdump watcher가 남지 않는다.

이 oracle은 현재 flush 경로가 workload에서 실행됨을 뒷받침하지만, snapshot copy 자체나 대안 설계의
성능 우열을 runtime으로 증명하지 않는다.
