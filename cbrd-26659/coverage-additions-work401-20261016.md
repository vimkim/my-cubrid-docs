# Work 401: OOS coverage 보강과 남은 증명

작성: 2026-10-16 (Asia/Seoul). 대상: CBRD-26659, engine PR #8128, private TC PR #4365. 이 문서는 새 회귀 테스트 4건과 남은 요구사항을 구분한다. **전체 OOS 동작 완료 또는 병합 준비 완료를 선언하지 않는다.**

## 변경과 독립 oracle

Engine `1ef86a7efa34002e971b1b30bcf5d451e9db441b`, public TC `df8596dd999e825b1ec9812a735bbe01e50ac715`, private TC 시작점 `9a075340f6ee02741f2578117aebf1a5f9aa54bb` 를 재확인했다. 세 PR은 OPEN이며 모두 `feature/oos-merge` 를 대상으로 한다. 새 private TC 커밋은 `2af262014`, `f0336b370`, `5c9d8de1a` 이다. Engine과 public SQL/answer는 변경하지 않았다.

| 새 shell 진입점 | 실제 경로와 oracle | 증명 한계 |
| --- | --- | --- |
| `cbrd_26659_jdbc_storage` | JDBC `PreparedStatement.setBytes` 로 4행을 쓰고 `getBytes` 의 모든 바이트를 입력 모델과 비교한다. 바로 그 행의 JDBC SHOW에서 파일·6청크·57,372 slot bytes를 검사한다. CTAS 복사 후 원본 DROP, 복사본 전체 바이트, CSQL의 같은 heap 상태, diagdb의 원본 owner 제거와 복사본 owner 보존, checkdb를 확인한다. | 이 private JDBC 실행의 직접 관측이다. 기존 public SQL 실행을 소급 관측한 것이 아니며, workspace/loader 전체 경로를 증명하지 않는다. |
| `cbrd_26659_tde_crash_committed` | 기존 acknowledged crash schedule을 AES 테이블에 적용한다. baseline/recovered OOS VFID·class·HFID를 AES file header와 연결하고, 소유 server/master의 실제 SIGKILL 및 REDO, 커밋 후 독립 행 모델, 물리 상태와 checkdb를 요구한다. | 일반 key rotation/backup, ciphertext 검사, 중간 reclaim 장애를 증명하지 않는다. |
| `cbrd_26659_tde_storage` | 독립된 일반/AES sentinel을 multi-chunk VARBIT로 저장하고 전체 값을 검증한다. SHOW의 실제 OOS volume ID를 소유 `_vinf` 의 유일한 파일 경로로 연결한다. NONE/AES owner header 확인 후 데이터-volume 그룹과 active log 각각의 일반 sentinel 발견을 필수로 요구하면서 별도 AES sentinel 부재와 재시작 후 값을 확인한다. | 200바이트 이상 반복 sentinel과 해당 artifact 그룹에 한정된다. 모든 바이트·다른 pattern·DWB·backup·key lifecycle의 일반 보안 감사를 뜻하지 않는다. |
| `cbrd_26659_tde_crash_undo` | 같은 AES schedule에서 INSERT/UPDATE/DELETE를 미커밋으로 유지하고 독립 flush fence 후 SIGKILL한다. REDO와 UNDO의 OOS trace가 양수이며 복구한 pre-image 전체 값과 owner 상태가 맞아야 한다. | vacuum을 비활성화하여 crash recovery와 MVCC reclaim을 분리한다. `RVOOS_DELETE` 자체의 replay를 별도로 증명하지 않는다. |

JDBC fixture의 payload는 3,000/4,207/20,003/33,001바이트이며 각각 세 개의 구별되는 영역으로 구성된다. 300바이트 tag는 inline이다. 마지막 세 payload의 5바이트 VARBIT prefix와 4바이트 slot 정렬로 `4212+20008+33008`, 여섯 개의 24바이트 청크 header로 `+144=57372` 를 독립 계산했다. 첫 payload는 inline이다. 길이만 같은 잘못된 값은 전체 배열 비교를 통과할 수 없다.

JDBC에서 SELECT를 부여받은 일반 사용자의 정확한 값을 확인한다. 같은 복사본에 대한 `SHOW HEAP OOS` 와 `SHOW ALL HEAP OOS` 는 DBA positive control과 CSQL 일반 사용자 negative control로 검사한다. 거부는 nonzero·비timeout 종료, 명시적인 DBA 전용 오류, 결과행 부재를 모두 요구한다. 첫 시도의 JDBC는 의도한 DBA 오류 대신 `No statement to execute` 를 반환했다. 따라서 JDBC의 정확한 오류 코드 mapping은 증명하지 않으며 CSQL의 명시적인 권한 오류를 사용한다.

공용 controller는 첫 실패의 소스 위치, 직전 완료 명령과 종료값, stdout/stderr의 마지막 각 16,000바이트를 cleanup 전에 보존한다. ERR trap은 기존 EXIT cleanup과 독립이다. 세 controller wrapper는 실패 log 내용을 실제 NOK artifact에 포함한다. SHOW oracle은 기대 file/chunk/slot과 실제 전체 상태를 오류에 포함하고, partition case도 SHOW·parser 진단을 NOK에 남긴다. 기존 기대값·발견 규칙·실패 여부는 유지한다.

## 실행 환경과 시도별 결과

원본 설치는 전용 optdebug preset으로 configure/build/install했다. 기존 ready Debug host DB와 registry는 전환하지 않았으며 `.env` 선택도 원래 `debug_gcc` 로 복원했다. 시작부터 있던 dirty `cubrid-cci` 를 보존했다. Engine 소스 수정과 unit hook 추가는 없다.

각 native 시도는 `/home/vimkim/tmp/oos-coverage401/<attempt>/` 에 설치·CTP 복사본, 비어 있는 전용 registry, HOME/TMP, config, 정렬한 expected list, engine/TC revision·patch·입력 SHA-256 manifest, preflight, runner status, result XML/status/feedback/log와 검증 결과를 보존한다. 호스트 DB는 사용하지 않는다. 실행은 `TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c <attempt>/conf/shell.conf` 이며, 실제 결과 디렉터리는 `<attempt>/CTP/result/shell/current_runtime_logs` 이다. `testkit-focused.py verify` 의 exact positive set·zero skip·assertion artifact를 판정 근거로 사용한다. runner exit 0만으로 통과시키지 않는다.

| 시도 | 선택과 결과 | 의미 |
| --- | --- | --- |
| `jdbc01` | JDBC 1건 실패, 관련 없는 macro skip 21건 | 첫 기대 오류 mapping 실패와 선택 집계 문제를 모두 보존한다. |
| `jdbc02` | JDBC 1/1 통과, zero skip; runner 20.847초 | 실제 JDBC 저장/읽기/복사와 CSQL 권한 검증. explicit case selection의 무관한 macro 제외를 해제했다. |
| `tde01` | AES 2건 중 undo 통과, committed 생성 실패; runner 84.945초 | 추가한 committed DB 이름이 17자 미만 제한을 넘었다. 복구 동작 실패로 분류하지 않는다. |
| `tde02` | 수정한 AES committed 1/1 통과; runner 26.794초 | 짧은 case-owned DB 이름을 사용했다. |
| `sentinel01` | plaintext positive control 미발견으로 실패 | OOS가 없는 primary volume만 검사한 첫 시도다. 오검사로 통과시키지 않았다. |
| `sentinel02` | 보정한 mapped OOS-volume/active-log 검사 1/1 통과; runner 22.191초 | actual OOS volume은 primary와 다르다. 두 artifact 그룹의 plain control과 AES sentinel 부재를 확인했다. |
| `sentinel-negative` | disposable scanner의 AES 검색 pattern을 실제 plain pattern으로 바꿔 노출 assertion 실패; runner 19.454초 | 정확히 1 failure/zero skip, `AES sentinel exposed or scanner failed` 를 독립 확인했다. 추적 소스는 변경하지 않았다. |
| `sentinel03` | clean `5c9d8de1a` 의 sentinel 1/1 통과, zero skip; runner 22.605초 | 13개 OK assertion, 두 artifact 그룹의 plain positive/AES negative, exact reopen과 DB/key/config cleanup을 확인했다. |
| `diagnostics01` | 기존 실패 4/4 재현 | 오류를 감추지 않고 실제 실패 단계와 cleanup을 확보했다. |
| `jdbc-negative` | 독립 복사본의 slot 기대값을 57372→57373으로 바꿔 의도한 assertion 실패; runner 28.303초 | 정확히 1 failure/zero skip, `serialized slot-byte model differs` 를 독립 확인했다. 추적 소스는 변경하지 않았다. |
| `final19` | 기존 통과 16건과 새 3건, 직렬 19/19 통과, zero skip; runner 669.915초 | 489개 OK assertion. native verifier와 별도 exact-case/XML/input-byte audit가 모두 통과했다. |
| `diagnostics02` | `2af262014` 의 알려진 실패 4/4, zero skip; runner 159.382초 | 별도 exact-case/XML/status audit로 4건 전부 failure임을 확인했다. 선택 통과에 섞거나 면제하지 않았다. |

최종 통과 선택은 **서로 다른 두 native invocation의 19+1건**이다. 20건 전체를 한 번에 실행한 기록으로 바꾸지 않는다. `final19` 의 기록된 TC HEAD는 `2af262014456c1b6e7bec1ec523bc6797f2ba14d`, `sentinel03` 은 `5c9d8de1a916ae0acbddc8409770b51fd31da13b` 이다. 모든 선택 fixture/helper 입력 SHA-256은 최종 clean TC와 일치한다. 이 검사는 `independent-pass-audit.json` 에, 알려진 실패 및 두 negative control의 exact-case/명시적인 assertion/zero-skip 대조는 `independent-failure-audit.json` 에 보존했다. 두 통과 실행에서 각 testcase(설정·정리 포함)의 시간 합은 각각 667.135초와 19.894초, 준비 시간은 0.754초와 1.076초로 runner 시간과 분리한다.

669.915초는 약 10분의 informal guide를 넘는다. 관측한 가장 긴 항목은 DML transitions 약 116초, schema SA 약 114초, utility CS 약 60초였다. 비용 때문에 coverage를 제거하지 않았다. 이 측정에는 현재 host 조건과 다른 contained 시도의 동시 실행이 포함되며, 과거 305초대 receipt와의 통제된 성능 비교가 아니다. 새 public SQL/answer 변경이 없어 public SQL을 다시 실행하지 않았고 기존 exact-engine/TC 회사 receipt를 역사적 근거로 유지한다.

JUnit의 `classname` hyperlink는 복사한 기본 설정의 `develop` 문자열을 포함하지만 `testcase_update_yn=false` 이며 testcase checkout을 갱신하지 않았다. 실제 revision/입력은 `private.head`, `inputs.json`, 정렬한 절대 expected list와 XML의 `file` 필드를 기준으로 대조했다.

Raw 실행/빌드 로그와 disposable runner script는 repository에 추가하지 않는다. Build receipt는 `/mnt/nvme/data-5/tmp/work401-{configure,build}.log` 이다. 초기 host preflight는 `CUBRID_DATABASES` 미선택으로 거부됐으며 `/mnt/nvme/data-5/tmp/work401-shell-preflight.log` 를 보존했다. 이후 각 시도의 명시적인 disposable 환경에서 source/install 일치를 검증했고 mismatch 예외를 사용하지 않았다. Native runner의 SHA-256은 `31be3b1e542b05d1ac7581d47f785319ce61421f4b5d94681a9c558d71445f5a`, source/install identity는 `1ef86a7` 로 일치한다. 각 시도의 config·fixture·dependency fingerprint는 해당 manifest를 기준으로 한다. CTP는 자산 dependency이며 별도 legacy CTP 실행이나 company CI를 수행하지 않았다.

## 기존 실패의 새로운 관측

`diagnostics01` 에서 partition 14개 물리/owner assertion은 실패했고 논리 값과 cleanup은 유지됐다. Snapshot/reclaim은 `snapshot_controller.sh:229` 의 `snapshot no positive page reclamation` 에 도달했다. SA physical은 `loaded.physical`, observer status 5에서 실패했다. Abort/vacuum은 `rollback_vacuum_reached` 이후 `abort_after_vacuum_values` 의 CSQL이 40초 제한에 걸려 exit 124였다. 이 관측을 과거 로컬의 corruption 결과와 동일한 원인으로 확정하지 않는다. `diagnostics02` 도 같은 실패 단계에 도달했다. Partition root에는 OOS가 있으나 목적지 child에는 없었고, SA-loaded heap은 기대 `[1,4,37316]` 대비 실제 file/chunk/slot이 모두 0이었다. Timeout 전후의 원인 확정을 위해서는 새 engine revision에서 실제 server wait/stack과 retained controller 문맥을 함께 조사해야 한다.

## Matrix의 누락·부분·실패 29개 항목 처분

기준은 완료된 coverage visualization의 `coverage-data` 51개 row 중 `coverage != yes` 또는 `result == fail` 인 29개다. 나머지 22개는 기존 날짜·revision의 제한된 근거를 유지한다. [기존 behavior ledger](ci-replan/coverage.md) 및 [개발자 delivery 합의](ci-replan/spec.md)가 범위를 정한다. Matrix의 일반적인 성능·운영 질문을 새 acceptance requirement로 바꾸지 않는다.

| Matrix row | 이번 근거 또는 명시적 후속 |
| --- | --- |
| `contract-1` | correctness delivery 범위. 워크로드 편익 benchmark는 별도 성능 qualification이며 미측정이다. |
| `contract-3` | engine `heap_file.c:12840,12873` 은 여전히 `DB_PAGESIZE/4` 를 사용한다. 기존 4060/4064 정답 reproducer를 유지하며 CBRD-27057 통합이 필요하다. unfill/page-size 경계 통과 credit은 없다. |
| `representation-3` | 기존 모듈 실행과 SQL many-attribute 값을 재사용한다. persisted VOT/stub 바이트·grow-and-retry의 제품 경로 증명은 기존 product observer로 분리할 수 없어 capability gap으로 유지한다. |
| `representation-4` | 기존 identity/retry 모듈 receipt를 유지한다. deterministic 같은-slot 재사용/latch-loss 제품 schedule은 없다. Work400의 ownerless reset seam과 혼동하거나 중복하지 않는다. |
| `writes-3` | 기존 constraint/trigger 논리 검증을 유지한다. trigger의 workspace 저장 배치/거부 후 chain ownership은 PR7925/7927 경로와 연관된 별도 물리 증명 공백이다. 정상 CRUD로 대체하지 않는다. |
| `reads-2` | 기존 dispatch 모듈·read/utility receipt를 재사용한다. 미사용 attribute의 실제 OOS I/O 부재와 전체 raw consumer census는 제품 수준 counter/제어가 없어 별도 proof gap이다. |
| `reads-3` | 새 실제 JDBC prepared-write/SHOW/전체 값/copy oracle을 추가했다. public SQL의 소급 배치와 모든 client/workspace 경로는 주장하지 않는다. SA loader는 Work393/397, PR7925/7927 의존성이다. |
| `transactions-3` | 기존 rollback/vacuum 정답은 실패로 유지한다. 새 receipt는 도달 단계와 제한시간 종료를 식별한다. 원인 확정과 engine 수리는 별도이며 즉시 rollback 통과로 닫지 않는다. |
| `transactions-4` | 기존 real snapshot receipt만 유지한다. 광범위한 multi-writer/deadlock/restart-under-load qualification은 이번 compact correctness delivery의 추가 요구가 아니다. |
| `lifecycle-3` | page-return 정답과 downstream churn을 유지한다. 현 engine에서 page 감소 prerequisite이 실패한다. 청크 제거/값 보존만 통과한 것으로 한정하며 CBRD-26786 요구를 충족하는 engine 수리/통합과 실제 growth/restart 검증이 필요하다. |
| `lifecycle-4` | CBRD-27230 accepted chain-reuse/commit notification이 미완이다. `recovery.c:905` 는 reserved no-op dispatch다. unassigned stub identity, commit-only emit, abort와 replica-local fixup은 engine 선행 의존성이다. |
| `schema-4` | 기존 destination-owner 테스트를 보존하고 실제 SHOW/parser 출력을 추가했다. 정상 값만으로 owner 통과를 선언하지 않는다. PR7927 및 Work393의 실제 통합·partition acceptance가 후속이다. |
| `recovery-3` | 새 AES crash redo/undo subset을 추가했다. typed `RVOOS_DELETE` replay 및 mid-reclaim crash의 deterministic barrier는 없으며 미검증이다. no-logging utility 논리 pass에 durability credit을 주지 않는다. |
| `recovery-4` | 기존 내부 fault/bounds 모듈과 외부 invalid-DML atomicity를 유지한다. 결정적인 제품 allocation/I/O fault control 없이 주입 coverage를 만들지 않는다. |
| `utilities-3` | 기존 SA physical 정답은 실제 loaded observer에서 실패한다. 새 진단으로 기대와 실제 배치를 보존한다. PR7925/7927·Work393/397 의존성이다. |
| `utilities-4` | 기존 engine-volume/log의 destructive full restore receipt를 유지한다. 외부 LOB payload disaster recovery나 incremental/PITR은 이 OOS delivery에서 약속한 범위가 아니며 보존된 payload를 복원 성공으로 세지 않는다. |
| `replication-1` | ADR0001의 합의된 별도 HA topology/transport 후속이다. 두 node를 준비하지 않았으며 exact replica bytes/OOS-local reference credit이 없다. |
| `replication-2` | 기본 transport 이후 failover/promotion/rejoin qualification 후속이다. 단일 DB crash로 대체하지 않는다. |
| `replication-3` | ADR0005의 deferred CDC/flashback history. 기존 cbrd_27064/27075를 비활성화하거나 기대값을 바꾸지 않는다. |
| `security-2` | 기존 OOS file의 NONE→AES 적용은 accepted 요구로 유지한다. manual `3b6ae97b`, `en/security.rst:374` 는 기존 table의 TDE ALTER를 지원하지 않는다고 명시한다. SQL/utility 제어가 없는 제품 proof gap이며 lazy AES/coexisting NONE로 대체하지 않는다. |
| `security-3` | 실제 AES crash committed/undo, owner header와 exact bytes 및 mapped OOS-volume/active-log의 bounded plaintext sentinel 검사를 보강했다. 일반적인 전체 plaintext/ciphertext 감사와 key rotation/independent restore는 여전히 미검증이다. 전체 row를 완전으로 올리지 않는다. |
| `operations-2` | granted ordinary reader의 값과 DBA-only SHOW 거부를 새로 검증한다. 첫 실패 출력도 보강한다. busy-page conditional-latch undercount는 별도 internal/product scheduling gap이다. |
| `operations-3` | product/operator runbook 전체는 기존 delivery 합의에 포함되지 않은 운영 문서 후속이다. 기존 utility 검증 절차와 backup 경계는 유지한다. |
| `performance-1` | inline baseline 대비 projection/cache benchmark 미실행. testcase runtime이나 unit counter를 성능 수치로 바꾸지 않는다. |
| `performance-2` | throughput/tail latency/peak memory/WAL amplification은 별도 benchmark다. 본 delivery에서 새 성능 acceptance를 만들지 않는다. |
| `performance-3` | 실제 page-return 실패가 반복 churn/재시작 plateau의 선행 의존성이다. 작은 unit churn으로 제품 soak를 대체하지 않는다. |
| `performance-4` | 현 Linux/16KiB/optdebug 결과만 주장한다. 지원 조합 정의와 release qualification matrix는 별도 후속이다. |
| `delivery-1` | 11.5 disk compatibility와 unreleased artifact 재생성 정책을 유지한다. 지원되지 않는 pre-release migration promise를 만들지 않는다. |
| `delivery-3` | testcase 추가와 정확한 실패 기록까지의 로컬 결과다. 엔진 결함·capability gap·TC human acceptance·통합/게시 승인과 Work371의 실제 병합 준비는 미완이다. |

## 검토와 통합 경계

Standards/Spec를 고정 시작점 `9a075340f` → `2af262014` 에 대해 독립 agent로 검토했으며 양쪽 모두 지적 사항이 없었다. Sentinel delta `2af262014` → `f0336b370` 도 양쪽 지적 사항이 없었다. 후속 `5c9d8de1a` 는 범위 주석 정정과 검사 artifact hash의 stdout 보존만 추가했으며 clean revision에서 `sentinel03` 을 통과했다. Bash syntax, warning-level shellcheck, `git diff --check`, 29개 disposition set 및 문서 local link/index 점검을 완료했다. 2026-10-16 사용자는 이 문서 topic branch를 현재 local `main` 에 rebase/merge하고 `main` 을 push하는 것을 승인했다. 이 승인은 GHA trigger, JIRA 갱신, 엔진/TC merge·push 또는 배포로 확대하지 않는다. TC PR의 merge/close는 기존 합의대로 사람이 수행한다.

Work401은 실행 가능한 보강과 이 검증을 커밋했지만, 남은 required engine behavior의 검증을 완료로 표시하지 않는다. 다음 진행 조건은 Work393/397·PR7925/7927 등 실제 engine 통합/수리 revision이다. 그 입력에서 네 보존 회귀, 4060/4064 target 및 accepted reuse/notification proof를 다시 다뤄야 한다. unavailable product controls와 HA topology는 각각 명시적인 후속이며 broader readiness Work371과 구분한다. 문서 통합 승인이 이 engine 의존성을 해소하지 않는다.
