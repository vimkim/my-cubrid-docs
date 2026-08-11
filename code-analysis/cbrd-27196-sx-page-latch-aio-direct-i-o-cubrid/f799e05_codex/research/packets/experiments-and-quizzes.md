# Experiment and Quiz Designer Packet

- **Role**: Experiment and Quiz Designer (read-only source research)
- **Topic**: CUBRID flush와 AIO에서 SX latch가 정말 필요한가 — frame 안정성, `READ` latch, 사본, 전용 I/O freeze 비교
- **Declared Scope digest**: `sha256:db5ba3f0288fbb966ca5a4a832b420e7b5c582b461dc266ceda80a816c410885`
- **CUBRID root / revision**: `/home/vimkim/gh/cb/pgbuf-analysis` / `f799e05d77d5300c6ea5753b4a6cc7caee6d8912`
- **Revision label**: `pgbuf-analysis`, commit title `pgbuf-analysis: add seminar quizzes and single-page event tracer`
- **Packet timestamp (UTC)**: `2026-08-11T04:44:38Z`
- **Contract**: 이 packet은 설계안이다. 실험·Quiz 파일을 만들거나 실행하지 않았고 CUBRID source를 수정하지 않았다. 최종 Claim ID는 main agent가 ledger를 만든 뒤 아래 임시 ID를 치환해야 한다.

## 1. 결론부터: runtime이 증명할 수 있는 것과 없는 것

안전한 baseline 실험의 중심 오라클은 다음 네 가지다.

1. 읽기 전용 negative control은 같은 `csql` transaction histogram에서 `Num_data_page_dirties = 0`이어야 한다.
2. 동일한 hashed SQL runner의 INSERT/UPDATE phase는 `Num_data_page_dirties > 0`과 정확한 row invariant를 남겨야 한다.
3. 실험 전용 DB에서 flush를 동기적으로 유발한 구간은 `Num_data_page_iowrites`의 **양의 delta**와 현재 dirty BCB gauge의 감소를 보여야 한다.
4. cleanup 뒤에는 실험 DB, server process, statdump watcher, backup artifact가 남지 않아야 한다.

이 결과에 pinned source를 결합하면 “실제 workload가 현행 data-page flush 깔때기를 사용했다”는 Claim을 보강할 수 있다. 그러나 SQL/statdump만으로 아래 사실을 runtime-confirmed라고 쓰면 안 된다.

- plain page의 `memcpy`가 실제로 실행된 횟수나 CPU 비중;
- BCB mutex가 풀린 뒤 writer가 같은 frame을 실제로 수정한 interleaving;
- WAL flush가 각 data write보다 먼저 끝났다는 개별 I/O 순서;
- re-dirty 또는 datafile write-error 정리 분기가 특정 run에서 실행됐다는 사실;
- `READ`/범용 `SX`/`IO_WRITE_FREEZE`/copy-AIO의 성능 우열.

이 항목들은 각각 pinned source fact, OS Interface 전제, 아직 구현되지 않은 대안에 대한 inference/unknown으로 분리한다. 특히 이 Report Run의 runtime experiment는 **현재 snapshot-copy baseline의 활동 증거**이지 snapshot copy 자체의 동적 관측 증거가 아니다.

## 2. Source anchors와 임시 Claim 링크

아래 ID는 packet 내부에서만 쓰는 임시 ID다. `evidence/claims.jsonl`과 `report.json.central_behaviors`가 확정되면 main agent가 실제 stable ID로 치환한다. 임시 ID를 `manifest.json`에 그대로 넣지 않는다.

| 임시 ID | behavior | 후보 Claim | 근거/제한 |
|---|---|---|---|
| `CUBRID-SCF-S01` | `snapshot-copy-flush` | plain page는 BCB 소유 frame에서 stack output image로 `IO_PAGESIZE`만큼 복사되고, 그 뒤 BCB mutex를 풀고 WAL/data write로 간다. | `page_buffer.c:10801-10848`; source-only |
| `CUBRID-SCF-S02` | `snapshot-copy-flush` | flush 시작 시 `FLUSHING_TO_DISK`를 set하고 기존 `DIRTY`를 clear하여 flush 중 새 modification을 별도 dirty로 다시 추적한다. | `page_buffer.c:16077-16099`; source-only |
| `CUBRID-SCF-S03` | `snapshot-copy-flush` | data write 실패 시 BCB를 다시 잡아 이전 dirty 상태와 `oldest_unflush_lsa`를 복원하고 flush waiter를 깨운다. | `page_buffer.c:10908-10922`, `16115-16126`; source-only. TDE/DWB 준비 단계의 early return은 별도 검토 필요 |
| `CUBRID-SCF-S04` | `snapshot-copy-flush` | `FLUSHING_TO_DISK`가 선 BCB는 victim 후보가 될 수 없다. | `page_buffer.c:253-262`; source-only |
| `CUBRID-SCF-R01` | `snapshot-copy-flush` | pinned runtime의 전용 DB에서 write workload가 dirty-page activity를 만들고, 동기 volume flush 구간에 data-page I/O가 증가하며 데이터 invariant가 유지됐다. | 아래 `experiment-1`; runtime observation의 정확한 한계 포함 |
| `CUBRID-SFIC-I01` | `stable-frame-io-contract` | live frame zero-copy write에는 buffer 내용 불변과 frame 재사용 금지가 모두 필요하고, AIO에서는 둘을 completion까지 유지해야 한다. | OS Interface 전제 + CUBRID ownership source로부터의 inference; CUBRID AIO 구현 Claim이 아님 |
| `CUBRID-SFIC-I02` | `stable-frame-io-contract` | strict `READ` latch는 thread/fix lifetime 안의 writer 배제에 쓸 수 있지만, 비동기 completion ownership·single flusher·victim 금지까지 혼자 표현하는 완전한 I/O request state는 아니다. | source+design inference; falsifier는 별도 completion-owned pin/state 없이 기존 READ holder가 안전하게 completion까지 승계되는 구현 |
| `CMP-SFIC-A01` | `stable-frame-io-contract` | PostgreSQL `SHARE_EXCLUSIVE`와 InnoDB SX/`io_fix`는 이름보다 “reader 허용, writer/두 번째 flusher/eviction 제어, I/O lifetime 소유” 축에서 CUBRID 후보와 비교해야 한다. | PG/MySQL comparator Claim과 합쳐 `partial analogy` 여부를 정할 것 |

### 직접 확인한 관측 함정

- `Num_data_page_dirties`는 unique dirty page 수가 아니다. `pgbuf_set_dirty_buffer_ptr` 호출마다 증가한다 (`page_buffer.c:11656-11675`).
- `Num_data_page_iowrites`는 DWB가 켜지면 DWB file write와 home-volume write를 모두 포함할 수 있다 (`double_write_buffer.cpp:2115`, `:2150`, `:2339`). logical/unique page 수나 copy 수로 해석하지 않는다.
- `Num_data_page_flushed`는 victim-candidate flush 종료부에서만 증가한다 (`page_buffer.c:4167`). checkpoint/backup/all-unfixed flush 전체의 보편 지표가 아니므로 hard oracle에서 제외한다.
- `SHOW PAGE BUFFER STATUS.Num_pages_written`은 현 source에서 non-DWB 분기에서만 증가한다 (`page_buffer.c:10886-10895`). DWB 활성 여부를 모른 채 보편 write counter로 쓰지 않는다.
- `SHOW PAGE BUFFER STATUS.Dirty_pages`와 statdump의 `Num_data_page_dirty`는 순간 gauge다. background daemon과 unlocked/weak snapshot 성격 때문에 정확한 schedule이나 동일 page를 증명하지 않는다.

## 3. Required experiment-1 — owned snapshot-copy flush baseline

### 3.1 Question → Hypothesis

**Question**

전용 CUBRID DB에서 동일한 SQL runner가 dirty pages를 만든 뒤 CUBRID의 동기적인 all-unfixed-volume flush 경로를 실행하면, pinned runtime에서 data-page I/O activity와 데이터 정확성 invariant를 반복 관찰할 수 있는가?

**Hypothesis**

- 같은 runner 안의 read-only control은 `Num_data_page_dirties = 0`이다.
- write phase는 매 run `Num_data_page_dirties > 0`이고 누적 row 수가 run 번호 × batch size와 일치한다.
- write phase 직후 dirty gauge는 양수이며, `backupdb -C` 완료 뒤 감소하거나 bounded idle sampling에서 0에 도달한다.
- watcher가 활성화된 active window에서 `Num_data_page_iowrites(after) > Num_data_page_iowrites(before)`다.
- 3회 반복 뒤 row count/checksum predicate와 restart 후 같은 predicate가 모두 성립한다.

여기서 `backupdb`는 “동기 checkpoint”라고 부르지 않는다. pinned source의 online backup은 각 volume에서 `disk_set_checkpoint` 뒤 `pgbuf_flush_all_unfixed`와 `dwb_synchronize`를 수행한다 (`log_page_buffer.c:7502-7525`). 이는 이 실험에서 재현성 있는 flush trigger지만 checkpoint daemon 자체는 아니다.

### 3.2 Safe names and owned resources

| resource | 제안 이름/위치 | ownership rule |
|---|---|---|
| DB | `ca27196_f799e05` | preflight에서 `databases.txt`의 정확한 첫 field가 없을 때만 생성. 있으면 adopt/delete하지 않고 hard stop |
| data/log root | `<report-dir>/experiments/experiment-1/runtime/` 아래 `data/`, `log/` | root 자체가 없음을 먼저 확인하고 nonce receipt를 만든 뒤 사용 |
| owner object | `ca27196_owner` | scope SHA-256, CUBRID commit, DB name, random run nonce를 단 한 row로 저장 |
| workload object | `ca27196_page_image` | DB 신규 생성 뒤에만 만들며 `DROP TABLE IF EXISTS`를 사용하지 않음 |
| backup dirs | `runtime/backup-r1`, `backup-r2`, `backup-r3`, 필요시 `backup-control` | 각 directory가 없음을 확인하고 nonce file을 둔 뒤 사용 |
| watcher output | `runtime/statdump-watch.out`, `runtime/statdump-watch.log` | exact absolute path. report의 다른 watcher와 공유하지 않음 |
| watcher receipt | `runtime/statdump-watch.receipt` | PID, PGID, `/proc/<pid>/stat` starttime, exact argv, install-root path, DB, nonce 기록 |

고정 DB 이름은 재현성을 위한 것이며 “이미 있으면 내 것”이라는 뜻이 아니다. pre-existing exact name은 언제나 hard stop이다.

### 3.3 Mandatory build/runtime identity gate

main agent는 실험 artifact를 만들기 전에 skill contract대로 다음을 끝내야 한다.

1. pinned root에서 captured `just build` run `runtime-baseline-build`가 exit 0인지 확인한다.
2. `runtime-snapshot --id baseline`으로 absolute `csql`, `cubrid`, non-executed `cub_server`, `cubrid_rel` identity를 seal한다.
3. 모든 argv의 tool path는 snapshot의 absolute path를 사용한다. 현재 shell의 우연한 `PATH` 결과를 manifest에 쓰지 않는다.
4. observation timestamp가 baseline snapshot보다 뒤인지 검증한다.

이 packet은 위 gate를 실행하지 않았다.

### 3.4 Preflight and setup ownership checks

`setup-preflight.sh`를 만들 경우 다음을 모두 nonzero-on-failure로 구현한다.

1. `$CUBRID_DATABASES`가 absolute이고 runtime snapshot의 sealed environment와 같은지 확인한다.
2. `$CUBRID_DATABASES/databases.txt`를 첫 field exact equality로 검사한다. substring `grep`만 쓰지 않는다.
3. DB가 이미 등록됐거나 `runtime/` 또는 backup directory가 이미 있으면 중단한다.
4. 같은 exact DB의 `cub_server`와 같은 nonce/path를 쓰는 watcher가 없음을 확인한다.
5. `runtime/`를 만든 뒤 random nonce, scope hash, commit, 생성 timestamp를 receipt에 기록한다.
6. `createdb` 뒤 registry의 exact line을 저장하고 data/log realpath가 모두 이 owned root 안인지 확인한다.
7. owner table row를 넣은 뒤 `csql`로 정확히 한 row가 exact nonce/commit/scope와 일치함을 확인한다.

제안 createdb argv 형태:

```text
["<snapshot cubrid>", "createdb",
 "--db-volume-size=64M", "--log-volume-size=64M",
 "--file-path", "<absolute owned data dir>",
 "--log-path", "<absolute owned log dir>",
 "ca27196_f799e05", "en_US.utf8"]
```

서버는 exact DB만 시작한다. 전역 `cubrid service stop/start`는 금지한다.

### 3.5 One hashed csql runner with internal negative/positive controls

manifest의 `runner`는 하나의 `scenario.sql`로 유지한다. SQL 내용의 구조는 다음과 같이 한다.

1. `communication_histogram=yes`, `.hist on`.
2. exact owner nonce를 read-only로 조회하고 section marker를 출력한다.
3. `;.x_hist`로 read-only phase의 histogram을 출력하고 clear한다.
4. `ca27196_page_image`에 fixed batch(예: 10,000 rows)를 INSERT하고 COMMIT한다. PK는 `AUTO_INCREMENT`를 써 동일 runner를 그대로 반복할 수 있게 한다.
5. total row count, payload 길이 위반 row 수, generation 값 위반 row 수를 출력한다.
6. `SHOW PAGE BUFFER STATUS`를 출력해 `Dirty_pages`, page size, 현재 pool context를 남긴다.
7. `;.dump_hist`로 positive phase histogram을 출력한다.

runner 안에 `DROP`, shell escape, checkpoint/backup command, 정답을 암시하는 comment를 넣지 않는다. schema creation은 별도의 captured setup SQL이다.

runtime snapshot을 만든 뒤 manifest에 넣을 exact argv 형태:

```text
["<snapshot absolute csql>",
 "-u", "dba",
 "ca27196_f799e05",
 "-i", "scenario.sql"]
```

`--sysadm`은 이 runner에 필요하지 않다. CSQL 순서가 해당 build에서 달라질 가능성은 setup smoke run으로 확인하되, 최종 manifest/run receipt는 실제 성공한 exact argv와 같아야 한다.

제안 observation run IDs:

- `exp1-scenario-r1`
- `exp1-scenario-r2`
- `exp1-scenario-r3`

각 run은 experiment directory를 cwd로 하고 `reportctl.py record --runtime-tools-snapshot evidence/runtime-tools-baseline.json -- <exact csql argv>`로 직접 실행한다. wrapper가 csql을 자식으로 호출하는 형태는 mandatory observation으로 인정하지 않는다.

### 3.6 Action sequence

setup/cleanup utility command도 모두 별도 run ID로 capture한다.

1. `exp1-preflight`: absence/ownership preflight.
2. `exp1-createdb`: owned paths로 DB 생성.
3. `exp1-server-start`: exact DB 시작 후 bounded csql readiness poll.
4. `exp1-schema`: owner/workload table 생성 및 nonce row 삽입. 이 단계도 absolute csql direct argv를 쓴다.
5. `exp1-drain-setup`: setup activity를 workload에서 분리하기 위해 initial all-unfixed flush를 수행하고, 끝난 뒤 quiescent sample을 남긴다. backup destination은 `backup-control`이고 `-r`을 쓰지 않는다.
6. `exp1-watcher-start`: persistent global-stat watcher를 own process group으로 시작한다.
7. 각 `r=1..3`에 대해:
   - one-shot cumulative statdump `before-r`;
   - mandatory `scenario.sql` csql run `exp1-scenario-r`;
   - one-shot statdump와 `SHOW PAGE BUFFER STATUS` context `pre-flush-r`;
   - exact empty owned directory `backup-r`에 `cubrid backupdb -C -D <dir> -l 0 ca27196_f799e05`; **`-r` 없음**;
   - one-shot statdump `after-r`와 CSQL row-invariant verifier;
   - dirty gauge가 안정될 때까지 bounded sampling. timeout이면 raw state를 보존하고 실험 실패로 처리한다.
8. `exp1-restart-check`: exact DB만 정상 stop/start한 뒤 같은 row invariant verifier를 다시 실행한다. crash/recovery 증거라고 부르지 않는다.
9. watcher process group cleanup.
10. ownership marker를 마지막으로 재검증한 뒤 exact DB stop/delete와 backup cleanup.
11. registry/process/path absence verification.

제안 backup argv:

```text
["<snapshot absolute cubrid>", "backupdb", "-C",
 "-D", "<absolute owned backup-rN>",
 "-l", "0", "ca27196_f799e05"]
```

`backupdb -r`의 `-r`은 `remove-archive`이므로 사용하지 않는다. backup write 자체는 `fileio_write_backup` 계열이다. page-buffer I/O counter와 backup archive bytes를 같은 것으로 해석하지 않는다.

### 3.7 Watcher lifecycle — wrapper PID 문제를 피하는 exact ownership

`cubrid statdump` wrapper PID만 저장하면 실제 child statdump가 남을 수 있다. 다음 방식으로 process-group ownership을 만든다.

- `setsid`로 watcher command만 새 session/process group에서 시작한다.
- group leader PID와 PGID가 같은지, `/proc/<pid>/stat` starttime이 receipt와 같은지 확인한다.
- group 내 모든 process의 executable/argv가 sealed CUBRID install root, exact DB, exact owned output path를 가리키는지 확인한다.
- cleanup 전에 PID 재사용 방지를 위해 starttime과 PGID를 다시 검사한다.
- 한 process라도 receipt와 맞지 않으면 kill하지 않고 hard stop한다.
- 검증에 성공한 경우에만 exact negative PGID에 TERM을 보내고 bounded wait한다. 전체 user process를 훑는 broad `pgrep -f ... | kill`은 쓰지 않는다.
- 끝에 group이 비었고 watcher count가 내려갔는지 확인한다.

watcher argv idea:

```text
setsid <snapshot cubrid> statdump -i 1 -c
  -o <absolute owned statdump-watch.out> ca27196_f799e05
```

실제 process launch shell은 별도 setup artifact다. manifest의 mandatory runner는 계속 direct csql이다.

### 3.8 Observable counters and hard oracle

| 관측 | hard oracle 여부 | 판정 |
|---|---|---|
| owner nonce/commit/scope query | yes | 매 csql run에서 exact 1 row |
| inserted row total | yes | run `r` 종료 시 `r × batch_size` |
| payload/generation violation count | yes | 0 |
| read-only phase `Num_data_page_dirties` | yes | 0; 다르면 raw output 보존 후 runner/control 설계 재검토 |
| write phase `Num_data_page_dirties` | yes | `> 0`; unique dirty page 수로 해석 금지 |
| `Num_data_page_iowrites` active-window delta | yes | 각 반복에서 `> 0`; logical page 수/사본 수/정확한 flush page 수로 해석 금지 |
| `Num_data_page_dirty` 또는 `Dirty_pages` | yes, 방향만 | pre-flush가 양수이고 backup 완료/idle 뒤 감소. exact 0은 background state에 따라 보조 기준 |
| `Num_data_page_flushed` | no | 기록은 하되 victim-only counter임을 설명. 0/양수 어느 쪽도 전체 flush 부재/존재 오라클이 아님 |
| `Num_DWB_flush_block`, DWB config | context | DWB 활성 여부와 iowrites 배수를 설명하는 데만 사용 |
| `Num_log_wals` | context | WAL activity이지 개별 WAL-before-data 순서 증명이 아님 |
| elapsed time/throughput | no | debug build, backup, watcher observer effect가 커서 정책 비교 수치로 쓰지 않음 |
| restart 후 row invariant | yes | pre-restart와 동일. crash recovery나 backup restore 증거라고 부르지 않음 |
| cleanup receipt | yes | DB registry exact entry 0, owned server/watcher 0, backup artifact 0 |

`repetitions=3`은 동일 build/DB에서의 procedural reproducibility다. 통계적 독립 sample은 아니다. 성능 분포를 주장하려면 매 run DB를 새로 만들고 hardware/warm state까지 고정하는 별도 benchmark가 필요하지만 이 scope에서는 하지 않는다.

### 3.9 Positive and negative controls

**Negative controls**

- 같은 runner/DB/user의 owner-row SELECT만 수행한 histogram에서 dirty call이 0인지 본다.
- setup을 모두 drain한 뒤 quiescent statdump interval을 별도 기록한다. background write가 나타날 수 있으므로 “반드시 I/O 0”을 hard oracle로 삼지 않는다.
- `Num_data_page_flushed`가 0이어도 `Num_data_page_iowrites`/dirty gauge가 움직일 수 있음을 관측 context로 남긴다. 이는 counter 이름 해석의 negative control이지 flush 자체의 음성 대조가 아니다.

**Positive controls**

- fixed batch INSERT + COMMIT이 정확한 row count와 positive dirty histogram을 만든다.
- all-unfixed flush 뒤 positive I/O delta와 보존된 row predicate를 확인한다.
- restart 뒤 같은 predicate로 durable readable state를 확인한다.

### 3.10 Alternative explanations and how to bound them

| 관찰 | alternative explanation | 대응/남는 한계 |
|---|---|---|
| iowrites 증가 | DWB가 같은 logical page를 두 번 집계했다. | 맞을 수 있다. 그래서 delta의 부호만 사용하고 DWB config/`Num_DWB_flush_block`을 함께 기록한다. |
| iowrites 증가 | backup archive file write를 센 것이다. | source상 backup image는 별도 file-I/O path이고 PB counter 증가 지점과 다르다. 다만 volume-header/system page flush도 PB delta에 포함되므로 quiescent control과 dirty gauge를 함께 본다. |
| iowrites 증가 | autonomous page flush daemon이 workload 중 먼저 썼다. | 전용 DB로 외부 activity를 제거하고 phase snapshot을 나눈다. 그래도 backup과 daemon 기여를 완전히 분해하지 못하므로 “active window의 flush activity”로만 해석한다. |
| dirty 감소 | background daemon이 줄였고 backup 때문이 아니다. | backup 전/후 bounded snapshots와 quiescent control을 둔다. trigger attribution은 source reachability와 결합한 inference로 표시한다. |
| row invariant 유지 | snapshot copy가 아니라 어떤 flush 방식이어도 유지될 수 있다. | 정확하다. runtime은 current build의 correctness case만 보며 copy의 필요성/대안 우열을 입증하지 않는다. |
| read-only dirty=0 | 단순 query라 우연히 page modification이 없었다. | 음성 대조 목적에는 충분하다. 모든 read-only CUBRID query가 절대 dirty하지 않는다는 일반 Claim으로 확장하지 않는다. |
| restart 성공 | crash recovery와 WAL ordering까지 증명했다. | 아니다. 정상 stop/start이므로 clean restart readability만 증명한다. |

### 3.11 Cleanup transaction

cleanup은 다음 순서를 지키며, 불확실하면 삭제보다 hard stop을 택한다.

1. owner table의 nonce/scope/commit exact match를 csql로 재검증한다.
2. watcher receipt의 PID/PGID/starttime/argv/install-root를 검증한 뒤 exact process group만 종료한다.
3. registry exact entry와 data/log realpath가 preflight receipt와 같은지 확인한다.
4. exact DB만 `cubrid server stop ca27196_f799e05`로 내린다. 전체 service는 중지하지 않는다.
5. server process가 사라진 것을 확인한다.
6. exact DB에 대해 `cubrid deletedb --delete-backup ca27196_f799e05` 또는 이 build가 지원하는 동등한 exact option을 사용한다. 최종 argv는 help/source와 dry validation 후 기록한다.
7. backup directory를 지울 필요가 있으면 receipt에 열거된 exact files만 대상으로 하고, path containment와 nonce를 재확인한다. broad glob 또는 `rm -rf`는 쓰지 않는다. 빈 directory는 `rmdir`만 사용한다.
8. `databases.txt` exact entry, DB server, watcher PGID, backup files가 모두 0인지 검증한다.
9. 일부 setup만 성공한 경우에도 “name이 같으니 삭제”하지 않는다. preflight absence receipt + owned realpath를 모두 증명할 때만 rollback cleanup한다.

## 4. Optional experiment-2 — concurrent write/flush liveness, not exact re-dirty proof

이 실험은 교육적으로 유용하지만 central Claim의 필수 runtime proof로 과장하지 않는다. scheduler와 page selection을 SQL에서 고정할 수 없으므로, 성공해도 “같은 BCB가 `FLUSHING_TO_DISK` 동안 re-dirty됐다”를 직접 증명하지 않는다.

### Question and hypothesis

writer가 fixed batch를 여러 번 갱신하는 동안 checkpoint request 또는 all-unfixed flush activity가 겹쳐도, 모든 committed generation과 row count가 보존되고 workload가 bounded time 안에 끝나는가?

### Runner ideas

- `writer.sql`: 동일한 target rows의 `generation=generation+1`을 fixed iteration만큼 실행하며 각 iteration을 COMMIT하고 짧은 `SLEEP(ms)`를 둔다.
- `checkpoint-request.sql`: `;checkpoint`를 포함하며 `--sysadm` csql로 직접 실행한다. 이 command는 checkpoint daemon을 wakeup할 뿐 synchronous completion이 아니므로 statdump의 `Num_log_end_checkpoints` 증가를 bounded poll한다.
- `verify.sql`: target/non-target별 generation predicate 위반 수, total row count, payload predicate 위반 수를 출력한다.

exact argv ideas:

```text
["<snapshot csql>", "-u", "dba", "ca27196_f799e05", "-i", "writer.sql"]
["<snapshot csql>", "--sysadm", "-u", "dba", "ca27196_f799e05", "-i", "checkpoint-request.sql"]
["<snapshot csql>", "-u", "dba", "ca27196_f799e05", "-i", "verify.sql"]
```

동시 실행이 필요하면 orchestration script가 `reportctl record ... -- <absolute csql> ...` 자체를 background로 시작하고 각 resulting run receipt가 direct csql argv를 보존하게 한다. wrapper만 기록하고 내부에서 csql을 부르는 방식은 쓰지 않는다.

### Controls, repetitions, oracle

- serial control: writer 완료 후 flush request.
- concurrency case: writer interval 안에 checkpoint start/end가 적어도 하나 들어왔음을 timestamp와 global counters로 확인.
- rollback control: 별도 runner가 update 후 rollback하고 final predicate가 변하지 않는지 확인. 이는 datafile write-error control이 아니다.
- 5회 반복, exact schedule/order는 oracle에서 제외.
- hard oracle: 모든 direct csql run exit 0, final generation/row predicates exact, bounded completion, cleanup exact.
- soft observation: checkpoint and writer intervals overlap; dirty/iowrite counters move.

### Interpretation limit

이 실험은 concurrent flush pressure에서 current build의 liveness/data integrity 사례를 보강한다. 같은 page, `FLUSHING_TO_DISK` interval, snapshot bytes, re-dirty branch 실행을 직접 식별하지 못한다. 따라서 `CUBRID-SCF-S02`는 계속 source-confirmed이고, 이 run은 별도 좁은 runtime Claim에만 연결한다.

### Existing committed tracer를 필수 증거로 쓰지 않는 이유

pinned branch에는 `CUBRID_PGBUF_TRACE_VPID` 기반 `pgbuf_quiz_trace`가 이미 commit되어 있고 `SET_DIRTY`, `FLUSHED_TO_DISK` 등을 기록한다 (`page_buffer.c:850-897`, `:10954`, `:16039`). source mutation 없이 켤 수 있지만 다음 한계가 있다.

- `FLUSH_START`/`mark_is_flushing`, thread ID, LSA, frame address, snapshot address를 기록하지 않는다.
- event마다 file open/append를 하므로 observer effect가 크다.
- 같은 page의 두 `SET_DIRTY`와 `FLUSHED_TO_DISK` 순서만으로 exact overlap을 단정하기 어렵다.
- server restart와 environment propagation, trace file ownership 검증이 추가로 필요하다.

따라서 main experiment의 statdump+data invariant를 대체하지 않는다. 사용한다면 optional teaching evidence로만 두고 exact owned trace path, VPID discovery receipt, observer effect를 공개한다.

## 5. Error-path experiment boundary

이 scope와 안전 계약 안에서 실제 datafile write error를 SQL만으로 결정적으로 주입하는 방법은 확인하지 못했다. 다음은 **하지 않는다**.

- user-owned filesystem을 가득 채우기;
- live DB volume permission 변경/rename/unmount;
- server process 강제 kill을 write timing에 맞추기;
- `backupdb` destination을 unwritable하게 만들어 datafile flush error라고 주장하기;
- source fault injection/assertion 추가.

unwritable backup destination은 backup-output error일 뿐 `pgbuf_bcb_flush_with_wal`의 home-volume `fileio_write` 실패 분기를 증명하지 않는다. 그러므로 정상 data-write 실패의 dirty/LSA 복원은 source Claim과 static Quiz reasoning으로 다루고 runtime-verified라고 쓰지 않는다. TDE encryption과 `dwb_set_data_on_next_slot` 준비 단계 early return도 normal data-write error cleanup과 분리해서 설명해야 한다.

## 6. Old report experiment-2 audit

검토 입력:

- `f799e05_claude/experiments/experiment-2/experiment.md`
- `manifest.json`, `expected-oracle.md`, `flush_workload.sql`
- `start_watcher.sh`, `stop_watcher.sh`, `kill_stray_watchers.sh`

좋은 설계 입력은 “per-transaction dirty histogram과 global watcher를 분리한 점”, “DWB counter 대안을 소스로 검토한 점”, “SQL/statdump가 copy 자체를 관측하지 못한다는 방향”이다. 그대로 재사용하면 안 되는 결함은 다음과 같다.

1. **trigger 오명명**: `backupdb -C`를 “동기 checkpoint”라고 썼다. source상 online backup은 checkpoint가 끝나기를 기다리거나 막은 뒤 각 volume의 header checkpoint 값을 set하고 `pgbuf_flush_all_unfixed`/`dwb_synchronize`를 한다. checkpoint daemon 실행과 동일하지 않다.
2. **불필요한 `-r`**: `backupdb -r`은 remove-archive다. flush 관측에 필요 없고 DB recovery resource를 변경한다.
3. **비독립 ownership**: experiment-1의 `sx_latch_lab`을 재사용하고 “모든 실험/Quiz가 끝난 뒤” 삭제했다. experiment-2 자체만 보고 ownership/cleanup을 검증할 수 없다.
4. **파괴적 collision 가능성**: fixed DB에서 `DROP TABLE IF EXISTS sx_flush_t`를 실행한다. DB name collision이 있으면 user object를 지울 수 있다.
5. **watcher leak이 실제 발생**: wrapper PID만 종료해 child statdump가 남았고 사후 corrective script가 필요했다. 이는 cleanup 설계 실패의 증거다.
6. **broad process matching**: corrective `pgrep -f`는 DB/output 문자열을 좁혔지만 PID starttime/process-group/owner nonce를 검증하지 않는다. 우연히 같은 argv를 쓰는 다른 process를 죽일 수 있다.
7. **negative control 부재**: before가 이미 `iowrites=229`였고 “watcher가 없으면 수집되지 않는다”는 현상은 mechanism negative control이 아니다. prior activity가 섞인 baseline이다.
8. **repetition 의미 과장**: SQL runner 2회는 반복됐지만 forced flush/counter before-after는 두 run을 합쳐 한 번만 측정했다. flush experiment 2회 재현이 아니다.
9. **`Num_data_page_flushed=0`을 hard oracle로 사용**: victim flush가 workload 중 발생하면 양수가 될 수 있다. 이 counter가 victim-only라는 source Claim은 맞더라도 매 run 0은 안정적인 invariant가 아니다.
10. **iowrites를 page 수로 읽을 위험**: DWB가 켜지면 DWB file/home write가 모두 집계될 수 있다. `+934`를 934 unique pages로 읽으면 안 된다.
11. **dirty count 의미**: 약 102,000은 10,000 rows가 만든 unique dirty pages가 아니라 dirty-mark API call 수다.
12. **snapshot runtime 과장 위험**: iowrites delta는 `memcpy`, frame-writer overlap, WAL ordering을 관측하지 않는다. source와 runtime의 Claim kind를 분리해야 한다.
13. **backup/system-page 기여**: PB iowrites delta에는 workload data page뿐 아니라 backup이 먼저 수정한 volume header/system page flush가 포함될 수 있다. quiescent control과 dirty gauge가 필요하다.
14. **cleanup self-attestation**: manifest의 `cleanup_verified=true`만으로 registry exact entry, process group, owned paths가 증명되지 않는다. captured cleanup receipt가 필요하다.
15. **observer/warm-state 혼재**: watcher, prior dry run, two accumulated workloads, background daemon, DWB queue state를 한 delta에 합쳤다. exact 숫자를 재현 목표로 삼을 수 없다.

## 7. Korean static Quiz plan (answers separated; no answer leakage)

두 central behavior 모두 최소 한 Quiz에 연결하되, 전체 set에서 normal/re-dirty/error/concurrency/policy/cross-DB/reimplementation을 모두 다룬다. 아래 4개 Quiz를 contiguous `quiz-1`…`quiz-4`로 제안한다.

### quiz-1 — baseline 관찰: 어떤 관측이 무엇을 말하는가

- **Behavior/Claim links**: `snapshot-copy-flush`; `CUBRID-SCF-R01`, `CUBRID-SCF-S01`.
- **Learning goal**: runtime observation과 source fact를 분리하고 counter 단위를 올바르게 해석한다.
- **Prerequisite / time**: Experiment chapter와 observability table, 25–35분.
- **Runnable artifact**: experiment와 같은 안전한 owned DB 또는 Quiz 전용 DB에서 실행하는 `scenario.sql`. main experiment output을 그대로 답으로 포함하지 않고 learner가 새 run을 만든다.
- **Prediction prompts (Korean, answer 미노출)**:
  1. read-only phase와 write phase에서 세 counter가 어떤 관계를 보일지 먼저 표에 예측하라.
  2. 세 번의 run에서 변해도 되는 값과 반드시 지켜져야 하는 invariant를 구분하라.
  3. 관찰만으로 확정할 수 있는 Claim과 source를 추가로 열어야 하는 Claim을 각각 고르라.
- **Observe**: owner marker, row invariant, per-transaction histogram, before/after `Num_data_page_iowrites`, dirty gauge, DWB context.
- **Teach-back**: “이 run이 snapshot copy를 직접 보았는가?”에 대해 evidence class와 falsifier를 포함해 설명하게 한다.
- **Cleanup**: Quiz-owned DB exact nonce/path를 확인한 뒤 exact DB만 삭제.
- **Do not leak**: filename/comment에 `copy`, `zero`, `victim-only`, 예상 부호/수치를 넣지 않는다. expected output을 `expected-positive.txt`처럼 이름 짓지 않는다.

### quiz-2 — 상태 전이: success, re-dirty, error, concurrency

- **Behavior/Claim links**: `snapshot-copy-flush`; `CUBRID-SCF-S02`, `CUBRID-SCF-S03`, `CUBRID-SCF-S04`.
- **Learning goal**: `DIRTY`, `FLUSHING_TO_DISK`, saved `oldest_unflush_lsa`, output image, waiter의 상태를 interleaving별로 추론한다.
- **Prerequisite / time**: lifecycle/concurrency/error chapter, 35–45분.
- **Runnable artifacts**: `scenario.sql`(정상 update/commit과 row verifier), optional `session-a.sql`, `session-b.sql`(동시 update/checkpoint request). artifact는 CUBRID만 요구한다.
- **Question structure**:
  1. 제공된 세 event trace의 각 step에서 frame/image owner와 flag를 빈 표에 채우라.
  2. writer가 어느 경계 전/후에 들어온 두 경우를 비교하고, flush 성공 뒤 다음 flush가 필요한 조건을 서술하라.
  3. data write가 error를 반환한 trace에서 retry에 필요한 state와 waiter action을 정하라.
  4. 두 flusher와 victimizer가 동시에 접근하는 trace에서 허용/금지 interleaving을 판정하라.
- **Runtime observation boundary**: optional two-session run은 final row/data integrity와 liveness만 본다. exact same-page re-dirty/error branch가 실행됐다고 문제 본문이나 script comment에서 말하지 않는다.
- **Answer authoring requirements**: causal state table, common misconception(“flush 성공이면 무조건 clean”, “failure면 새 dirty를 버림”, “FLUSHING flag가 writer도 막음”)을 별도 설명하되 `answer.md`에만 둔다.

### quiz-3 — 정책 선택과 cross-DB mapping

- **Behavior/Claim links**: `stable-frame-io-contract`; `CUBRID-SFIC-I01`, `CUBRID-SFIC-I02`, `CMP-SFIC-A01` + actual PG/MySQL Claim IDs.
- **Learning goal**: 이름이 아니라 buffer owner/lifetime과 compatibility matrix로 copy, strict READ, broad SX, `IO_WRITE_FREEZE`, WRITE를 비교한다.
- **Prerequisite / time**: policy + PG + MySQL chapters, 40–50분.
- **Runnable artifact**: CUBRID-only `scenario.sql`로 `Page_size`, dirty/write context, read/write workload의 baseline을 관찰한다. PostgreSQL/MySQL server는 요구하지 않는다.
- **Question structure**:
  1. buffered sync, `O_DIRECT` sync, copy-AIO, live-frame AIO 네 경우에 대해 “어느 memory를 언제까지 누가 소유하는가”를 채우라.
  2. reader/writer/second flusher/victimizer compatibility를 각 후보 정책에 대해 채우라.
  3. TDE와 DWB가 켜진 경우 같은 선택을 유지할지, 남는 copy와 lifetime을 근거로 재판정하라.
  4. report에 포함된 PG/MySQL source evidence만으로 각 mapping을 `equivalent`/`partial analogy`/`no equivalent` 중 하나로 분류하고 차이를 설명하라.
  5. 아직 측정하지 않은 값 때문에 결론을 보류해야 하는 cell을 표시하라.
- **No answer leakage**: 정책 표의 compatibility cell은 빈칸으로 제공한다. 후보 이름에 `best`, `required`, `slow` 같은 평가어를 넣지 않는다.

### quiz-4 — reimplementation capstone: completion-owned freeze 설계

- **Behavior/Claim links**: `stable-frame-io-contract`; `CUBRID-SFIC-I01`, `CUBRID-SFIC-I02`, `CUBRID-SCF-S02`~`S04`, comparison Claim set.
- **Learning goal**: 공개 page latch를 무조건 늘리지 않고도 flush 전용 Interface/state를 재구현 가능한 수준으로 설계하고 conformance tests를 만든다.
- **Prerequisite / time**: blueprint chapter 전체, 60–90분.
- **Runnable artifact**: CUBRID-only baseline `scenario.sql`/two-session scripts. learner implementation은 요구하지 않고 current behavior oracle을 수집한다.
- **Design prompts**:
  1. `prepare`, `submit`, `complete_success`, `complete_error`, `cancel`, `shutdown_drain` Interface의 pre/postcondition과 owner를 정의하라.
  2. immutable-content와 no-reuse invariant를 각각 어느 state/field가 보장하는지 명시하라.
  3. reader, writer, second flusher, victimizer의 wait/nowait 규칙과 wakeup order를 작성하라.
  4. re-dirty, error, stuck completion, queue pressure, TDE, DWB 분기를 빠짐없이 포함한 total state machine을 작성하라.
  5. copy baseline, broad SX, dedicated freeze를 구별할 black-box/white-box conformance test를 설계하라.
  6. PG/MySQL과 달라야 하는 CUBRID seam을 한 가지 이상 정당화하라.
- **Required output from learner**: pseudocode, state table, compatibility matrix, failure matrix, 최소 test list. 답안은 `answer.md`에서 하나의 acceptable design과 허용 가능한 variation을 설명한다.
- **No answer leakage**: starter pseudocode는 함수 이름/입력만 제공하고 transition, lock order, cleanup body는 빈칸으로 둔다.

### Quiz-wide safety and reproducibility checklist

각 `quiz-N`은 다음을 만족해야 한다.

- `quiz.md`와 `answer.md`는 분리하고 Korean prose를 쓴다.
- 적어도 하나의 `.sql`/`.sh` artifact가 CUBRID만 요구한다.
- exact unique DB/object name과 pre-existence refusal을 사용한다.
- script는 partial failure에도 own resource만 정리하고 failure를 nonzero로 돌려준다.
- concurrency Quiz는 scheduler 순서를 예상값으로 삼지 않고 final invariant/liveness를 본다.
- cross-DB Quiz는 included pinned evidence로 reasoning하며 PG/MySQL runtime을 요구하지 않는다.
- `quiz.md`, script comment, filename에 답/예상 수치/정책 우열을 넣지 않는다.
- `answer.md`는 관찰하지 못한 것을 분명히 쓰고 report chapter/Claim IDs를 연결한다.
- main agent가 최소 1회 실행해 answer와 맞는지 확인하기 전에는 publish하지 않는다.

## 8. Proposed teaching/claim map

| category | central behavior | Experiment | Quiz | coverage links |
|---|---|---|---|---|
| normal flush activity | `snapshot-copy-flush` | required experiment-1 | quiz-1 | core-workflows, experimental-validation, performance-observability |
| re-dirty/success/error | `snapshot-copy-flush` | optional experiment-2는 liveness만 | quiz-2 | lifecycle-state-machines, storage-durability-recovery, errors-resource-pressure |
| concurrency ownership | both | optional experiment-2 | quiz-2, quiz-4 | concurrency, data-ownership-lifetime |
| copy/READ/SX/freeze policy | `stable-frame-io-contract` | experiment-1은 current baseline only | quiz-3 | policies-algorithms, performance-observability |
| cross-DB responsibility | `stable-frame-io-contract` | CUBRID runtime only; 타 DB 실행 없음 | quiz-3 | postgresql-analysis, mysql-analysis, cross-database-comparison |
| reimplementation | both | baseline oracle 재사용 | quiz-4 | scope-interface-seams, reimplementation-blueprint, teaching-map |

## 9. Manifest integration notes

required experiment-1의 manifest는 다음 방향으로 작성한다.

- `behavior_ids`: frozen scope의 두 behavior를 모두 연결할 수 있지만 runtime Claim은 current baseline에만 한정한다. `stable-frame-io-contract` 연결 사유는 “현재 copy baseline의 관찰 가능한 기준선”이지 대안 구현 validation이 아니다.
- `claim_ids`: ledger 확정 후 `CUBRID-SCF-R01`에 대응하는 실제 CUBRID runtime/source+runtime Claim만 넣는다. source-only copy/error/inference Claim을 runtime manifest가 직접 소비했다고 가장하지 않는다.
- `runner`: `scenario.sql` 하나.
- `runner_argv`: sealed absolute csql + exact relative SQL path.
- `run_ids`: 3개의 direct csql observation receipt만. backup/statdump/setup/cleanup run IDs는 experiment prose/evidence index에서 별도로 참조한다.
- `oracle_ko`: exact row predicates, negative/positive dirty histogram, positive I/O delta, cleanup absence를 쓴다. exact counter 수치나 `Num_data_page_flushed=0`을 쓰지 않는다.
- `controls_ko`: 같은-run read-only control, quiescent interval, data-integrity/restart control.
- `alternative_explanations_ko`: DWB double count, backup system-page writes, autonomous daemon, runtime이 copy를 직접 보지 못함을 포함한다.
- `repetitions`: `3`.
- `cubrid_runtime_only`: `true`.
- `cleanup_verified`: captured cleanup receipt가 실제 성공한 뒤에만 `true`.

## 10. Unknowns / hard boundaries for the Book

- current CUBRID에는 scope의 broad SX/`IO_WRITE_FREEZE`/write AIO implementation이 없으므로 대안 성능·공정성·completion cancellation은 runtime unknown이다.
- SQL-only test로 exact `FLUSHING_TO_DISK` interval이나 frame address stability를 식별하지 못한다.
- safe datafile write-error injection을 설계하지 못했으므로 error branch는 runtime-confirmed가 아니다.
- DWB/TDE output-image copy count와 lifetime은 source tracer/other packets의 exact ownership 분석에 의존한다.
- buffered sync write와 synchronous `O_DIRECT`는 “sync vs async”와 “page cache bypass”를 별도 축으로 설명해야 한다. `O_DIRECT`라는 이유만으로 completion이 submitter lifetime을 넘는다고 쓰지 않는다.
- broad SX가 유일한 해답이라는 결론은 이 실험에서 나오지 않는다. 필요한 것은 exact frame/content/eviction/completion contract이고, 어느 representation이 CUBRID workload에 맞는지는 prototype measurement 전까지 unknown이다.

## 2026-08-11 addendum — overflow OID는 새 runtime behavior가 아님

overflow OID 사례는 frozen scope의 “범용 SX와 flush 전용 상태의 경계”를 설명하는 bounded policy example로
추가한다. 새 central behavior나 새 runtime Experiment를 만들지 않는다. 기존 experiment-1에는 low-cardinality
index가 없고 overflow traversal/SX 이득을 검증하지 않는다.

Quiz 2에는 source reasoning checkpoint를 추가한다. H1~H3 first-fit에서 (1) max one overflow latch와 leaf W,
(2) found page W-held/no recheck, (3) head insertion 때문에 매 insert O(K)가 아닌 이유, (4) SX reader/second
inserter, (5) conditional eventual SX→WRITE, (6) 없어지는 충돌과 남는 O(K)/fix/leaf gate를 구분하게 한다.

향후 runtime은 bulk-built chain, runtime-only append, fragmentation을 나누고 visited pages/insert, leaf wait,
overflow wait, SX→WRITE wait, reader latency와 insert tail latency를 함께 계측해야 한다.
