# CBRD-27791: OOS batch read 상세 분석과 재측정

작성: 2026-10-28, Asia/Seoul. 독자: OOS 성능·storage·scan 구현 담당자.
Work Item 537. 대상은 [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791)이며,
후속 설계는 [구현·검증 계획](CBRD-27791-oos-batch-read-plan_dcbf09e_codex.md)에 정리한다.

## 질문과 결론

기존 [전체 실측](../CBRD-27788/CBRD-27788-oos-select-performance_dcbf09e_codex.md)과
[읽기 패턴 진단](../CBRD-27788/CBRD-27788-oos-cold-read-diagnosis_dcbf09e_codex.md)을 독립적으로 검토하고,
전체 미래 주소를 모르는 batch에서도 검토할 가치가 있는 효과가 남는지 조사했다.

파일 캐시 해제 요청 후 overflow Q4는 최초 재확인 3회에서 기준 2.38초, OOS 5.72초로 약 2.4배 느렸다.
읽기 순서·요청 방식의 영향은 재현됐다. 제한된 **64 heap-page batch를 가정한 offline 정렬**도 원래 재생 4.413초를 3.449초로 줄였다.
그러나 같은 범위의 인접 병합은 3.974초로 정렬만 한 경우보다 느렸다. gap 병합은 1.965초지만 요청 바이트가 72.4% 늘었다.

따라서 bounded batch를 엔진에서 검증할 근거는 있으며, “병합을 추가하면 항상 개선된다”거나 “읽기 바이트가 줄면 빨라진다”는 정책은 근거가 없다.
현재 `oos_read_many`만 호출하도록 바꿔서는 Q4의 여러 행 읽기가 batch I/O로 바뀌지 않는다.
이번 작업은 **미수정 엔진의 native 재측정과 offline 대조**다. 개선 후 SQL, MVCC·latch를 수행하는 새 batch 구현, native 첫 행 지연·peak memory를 측정한 결과는 아니다.

## 비교 identity와 환경

| 역할 | CUBRID/cubrid full SHA |
| --- | --- |
| base | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| OOS / 재조회한 PR #7990 head | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |

두 보존된 detached checkout·설치·DB를 사용했다. source tracked diff 없음, 서버·CSQL·libcubrid hash와 원래 설정의 byte 일치를 확인했다.
출발 checkout `feature/oos-merge`의 `1a8cbefa4`에는 별도 CPU 개선과 하네스가 포함돼 있으므로 이를 측정 엔진으로 부르지 않았다.
새 엔진 수정·빌드·DB 재적재·배치 변경은 하지 않았다.

GCC 11.5.0, RelWithDebInfo, `-O2 -ggdb3 -DNDEBUG -finline-functions`, 테스트 계측 없음 조건을 유지했다.
DB/log page 16KiB, DB buffer 512MiB, query cache 0, `data_file_os_advise=0`이다.
Linux 5.14 EL9 backport 커널, XFS/NVMe, 공유 호스트다. server CPU 16–19, CSQL 12, 관측 13, replay 16을 사용했다.
source·CSQL·DSO·정답·직렬 TABLE SCAN은 각 native 표본에서 검사했다.

입력은 기존 100,000행의 heap/overflow 두 layout이다. [fixture.sql](fixture.sql)은 최초 측정 입력과 byte 단위로 같다.
기준 heap 입력 평균 record 길이는 14,480B, overflow는 22,016B다.
OOS heap은 각각 4,012B/4,040B이며 큰 값은 속성별 chain에 있다.
이번 Q4 입력의 큰 값은 한 chunk에 들어간다. multi-chunk의 주소 의존성은 소스로 분석했으며 새 runtime 성능 축으로 측정하지 않았다.

## 기존 근거의 독립 감사

별도 파서로 strace의 unfinished/resumed 호출을 재조립했다. FD map 전후 전체 일치, volume read의 완전한 반환,
쿼리 worker의 선택, 기록 순서와 `requests.tsv`의 완전 일치를 확인했다.
기준 200,089개/OOS 133,341개 요청을 재구성했고, 이전과 새 trace의 주소 패턴도 같다.
보존된 기존 진단 script 3개의 hash는 게시된 기계 요약과 일치했다.

요청을 16KiB page occurrence로 펼쳐 **중복 횟수까지** 비교했다. 기존 입력에 중복 page occurrence는 없었다.
정렬과 인접 병합은 selected page multiset과 요청 바이트를 보존했다.
기존 global gap 병합은 96,875 page occurrence와 약 1,513.67MiB를 추가했다.
기존 `call_multiset_sha256`은 병합 전 입력의 canonical hash이므로 gap 추가 여부를 증명하지 못한다.
새 결과에는 실제 발행 요청 hash, 발행 page multiset hash, 추가 page occurrence와 요청 바이트를 별도로 기록했다.

새 head trace는 `PAGE_OOS` 100,000회, `PAGE_HEAP` 33,339회와 소량의 BTREE/FTAB 읽기로 분류됐다.
분류는 정지 DB에서 각 선택 page의 file-I/O header를 읽어 수행했다.
이 revision의 `LOG_LSA` 8B와 header layout에 따라 pageid offset 8, ptype offset 14를 사용하고,
모든 pageid가 파일 offset/16KiB와 맞는지 검사했다.
[layout](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_io.h#L165)과
[page type](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/storage_common.h#L150)에 고정된 관측이다.

## Native SQL 재측정

각 행은 엔진별 3회 중앙값이다. Q4 파일 캐시 해제 행은 최초 재확인 묶음이며, 종료 재확인은 별도로 남겼다.
매 반복마다 엔진 순서를 교대했다. warm은 매 표본 서버를 시작한 뒤 같은 SQL을 한 번 실행하고 측정했다.
512MiB보다 compact heap 자체가 조금 크므로 warm을 전체 DB가 메모리에 있는 조건으로 해석하지 않는다.

| layout / SQL | cache 조건 | base / OOS 초 | 해석 |
| --- | --- | ---: | --- |
| overflow Q4 | 작업 파일 캐시 해제 요청 | 2.38 / 5.72 | 읽기 대기 증상 재현 |
| overflow Q1 | 작업 파일 캐시 해제 요청 | 1.88 / 0.82 | 작은 컬럼 이득 유지 |
| overflow Q5 | 작업 파일 캐시 해제 요청 | 3.46 / 4.12 | 다중 큰 값은 다른 요청 집합 |
| heap Q4 | 작업 파일 캐시 해제 요청 | 1.29 / 1.73 | 일반 heap 대비 비용도 유지 |
| heap Q1 | 작업 파일 캐시 해제 요청 | 0.91 / 0.83 | engine read 감소를 장치 byte 감소로 일반화하지 않음 |
| overflow Q4 | restart-only | 1.80 / 1.50 | OOS 범위 1.48–4.08초, OS cache 상태 혼재 |
| overflow Q1 | restart-only | 1.43 / 0.37 | 첫 표본에 실제 OS 읽기가 남음 |
| overflow Q4 | warm | 1.23 / 1.00 | 파일 캐시 해제 조건과 반대 방향 |
| overflow Q1 | warm | 0.76 / 0.09 | compact heap의 이득 |

최초 Q4의 base/OOS CPU task-clock은 2,333.30/2,266.97ms, instructions:u는 약 79.46/80.64억이었다.
engine ioread는 200,087/133,339회, OS read_bytes는 3,146.12/2,793.78MiB다.
계산량·읽기 횟수가 더 많아서 약 3.34초 느리다는 설명과 맞지 않는다.
CPU 증가가 주원인이 아니라는 기존 판정을 지지하지만, 장치 내부 cache·queue·SSD 동작의 기여율을 분리한 것은 아니다.

restart-only는 OS cache를 해제하지 않는다. 첫 실행에 읽기가 남은 사실을 숨기지 않고 중앙값과 범위를 함께 보존했다.
작업 파일 해제 조건에서는 정지한 등록 permanent volume만 `fsync`/`POSIX_FADV_DONTNEED`로 처리하고 `fincore`로 residency를 확인했다.
전역 drop_caches나 장치 cache 초기화는 하지 않았다. tracer를 붙인 2개 실행의 시간은 위 표에서 제외했다.

## Bounded offline 대조

새 trace의 volume 읽기를 서버 정지 상태에서 `os.pread`로 재생했다. 각 조건을 3회 실행하고 순서를 반전·회전했다.
각 pass 끝에 base 원래 순서 대조도 실행했다. max syscall 크기는 1MiB이며 단순 정렬은 계속 16KiB 요청이다.
모든 재생 전 정지한 작업 volume에만 cache 해제를 요청하고 residency를 확인했다.

대조 방식은 다음과 같이 다르다.

- **request window**: trace의 연속된 32/128/512/2,048개 요청을 각각 정렬한다. 그 window의 미래 주소는 미리 알고 있다.
- **heap-page batch**: 16/64개의 `PAGE_HEAP` 읽기 단위로 trace를 나눈다. 각 batch의 non-OOS 읽기를 원래 순서로 먼저 실행한 뒤 OOS 요청을 주소순으로 읽는다.
- **OOS run**: 연속된 OOS 요청 구간만 정렬·인접 병합한다. 다른 종류의 읽기를 넘어 수집하지 않는다.
- **global**: 전체 요청을 사후 정렬하는 기존 대조다. 엔진이 즉시 사용할 수 있는 정책이 아니다.

heap-page batch는 collector의 가능성을 살피는 **offline 모델**이다. 실제 가시성 판단·predicate·buffer hit·수명 비용을 수행하지 않으며,
trace의 요청 경계가 실제 row batch와 같다는 증거도 아니다. 이 fixture에서는 heap page당 대략 3행이지만 이를 일반 row 상한으로 쓰지 않는다.

| OOS 재생 방식 | 초 중앙값 | 발행 요청 | 요청 MiB | OS read_bytes MiB |
| --- | ---: | ---: | ---: | ---: |
| 원래 순서 | 4.413 | 133,341 | 2,083.45 | 2,793.11 |
| OOS run만 인접 병합 | 4.409 | 133,337 | 2,083.45 | 2,793.11 |
| 32 request 정렬 | 3.014 | 133,341 | 2,083.45 | 3,198.80 |
| 128 request 정렬 | 2.707 | 133,341 | 2,083.45 | 3,194.91 |
| 512 request 정렬 | 2.069 | 133,341 | 2,083.45 | 3,353.89 |
| 2,048 request 정렬 | 1.977 | 133,341 | 2,083.45 | 3,308.58 |
| 128 request 정렬·인접 병합 | 3.258 | 101,291 | 2,083.45 | 3,068.58 |
| 512 request 정렬·인접 병합 | 2.576 | 100,645 | 2,083.45 | 3,214.58 |
| 128 request 정렬·gap 병합 | 1.652 | 6,555 | 3,564.30 | 3,644.78 |
| 512 request 정렬·gap 병합 | 1.514 | 4,372 | 3,588.94 | 3,647.83 |
| 16 heap-page batch 정렬 | 4.350 | 133,341 | 2,083.45 | 2,838.39 |
| 64 heap-page batch 정렬 | 3.449 | 133,341 | 2,083.45 | 2,946.62 |
| 64 heap-page batch·인접 병합 | 3.974 | 100,523 | 2,083.45 | 2,752.59 |
| 64 heap-page batch·gap 병합 | 1.965 | 3,921 | 3,592.86 | 3,621.56 |
| global 정렬 | 2.822 | 133,341 | 2,083.45 | 2,765.25 |
| global 정렬·인접 병합 | 1.446 | 100,522 | 2,083.45 | 3,579.64 |
| global 정렬·gap 병합 | 1.277 | 3,649 | 3,597.12 | 3,657.59 |

base 원래 순서는 1.104초였다. 세 pass의 범위는 1.103–1.105초다.
64 heap-page 정렬은 원래 OOS 재생 대비 약 21.8% 짧고, 같은 batch의 gap 병합은 약 55.5% 짧다.
그러나 gap은 96,602개 page occurrence를 추가하고 요청량을 72.4% 늘렸다. 필요한 페이지 집합을 보존한 대조와 구분한다.
인접 병합은 같은 byte를 읽고 syscall 수를 줄여도 해당 bounded 조건에서는 더 느렸다.
global 정렬이 일부 request window보다 느린 것도 관측했다. offset 순서만으로 전체 kernel/device 동작을 예측하지 않는다.

정렬·인접 병합은 page occurrence를 정확히 보존하고, gap은 원래 occurrence를 모두 포함하는지 검사했다.
선택한 모든 page 내용의 전체 SHA-256을 재생 전후 읽어 비교했고 양쪽 engine 모두 같았다.
검증용 추가 읽기는 timed replay 밖에서 수행했다.

### 메모리와 첫 결과 시간의 해석

64 heap-page 모델에서 최대 입력 묶음은 256개 요청/4MiB이고, 512-request window는 8MiB다.
이는 선택 I/O 범위이며 엔진이 동시에 보관할 payload 메모리가 아니다. 도구의 Python RSS도 전체 trace·Counter를 담으므로 제품 메모리 예산으로 쓰지 않는다.
64 heap-page 정렬의 첫 batch I/O는 약 11.0ms, 512-request 정렬은 약 18.9ms였다.
이는 주소 수집·가시성·predicate·decode 시간을 제외한 proxy이며 실제 첫 행 반환 지연이 아니다.
전체 계획·무결성 검사 비용도 재생 시간에서 제외하고 기계 요약에 따로 기록했다.

## 정확한 source 책임과 후속 seam

| 위치 | 확인한 책임과 제약 |
| --- | --- |
| [heap_oos_read_grouped_payloads](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_oos.cpp#L734) | 한 record의 요청 OOS 속성이 2개 이상일 때만 raw destination을 할당해 모은다. cleanup은 부분 실패에서도 필요하다. |
| [heap_attrinfo_read_dbvalues_with_oos_prefetch](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L11670) | 0/1개는 scalar 경로, 다중 속성은 grouped Resolve 후 DB_VALUE로 복사하고 raw buffer를 해제한다. |
| [oos_read_many](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L2854) | 요청의 처음 나타난 head page 순서로 같은 VPID를 찾아 묶는다. 주소순 전체 정렬이나 syscall 병합이 아니다. head를 unfix한 뒤 continuation을 따라가므로 여러 OOS page를 고정해 두지 않는다. |
| [oos_read](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L2793) | head page 존재·type, slot·stamp·index·길이를 payload 복사 전에 검증한다. continuation 주소는 이전 chunk를 읽어야 알 수 있다. |
| [scan_next_heap_scan](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/scan_manager.c#L5681) | 현재 visible record를 가져와 predicate를 평가하고 rest attribute를 읽는다. watcher page 변경 시 COPY/retry한다. 행을 넘는 수집에는 record·attr cache 수명 변경이 필요하다. |
| [eval_data_filter](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/query_evaluator.c#L3460) | lazy attribute 읽기로 short-circuit에서 필요 없는 값의 Resolve를 피한다. batch가 모든 predicate 속성을 미리 Resolve해서는 안 된다. |
| [page-buffer miss](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/page_buffer.c#L8480) | BCB 예약과 DWB 확인 뒤 한 page를 읽고 TDE 처리를 수행한다. 이 경로를 건너뛰는 raw bulk read는 동등하지 않다. |
| [fileio_read_pages](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_io.c#L4221) | 연속 low-level 읽기 함수다. 현 호출자는 DWB 복구와 로그 경로이며, data page buffer의 batch 계약을 제공하지 않는다. |

규범상 Resolve는 필요한 속성의 lazy 조회이고, Expand는 raw record 소비자를 위한 별도 계약이다.
이를 한꺼번에 Expand하도록 바꿔 batch를 만드는 안은 작은 컬럼 이득과 책임 구분을 잃는다.
`FILE_OOS`는 logical file이다. 위 offset은 physical volume 안의 위치이며 별도 OS OOS 파일을 관측한 것이 아니다.

## 재현과 보존

새 raw root는 다음이다. 기존 실측·진단 root와 파일을 덮어쓰지 않았다.

```text
/mnt/nvme/data-5/tmp/CBRD-27791-20261028-h6a_kjx_
```

그 안의 `diagnose.py repro --name opening --repeats 3`이 실행한 RED-capable native loop다.
marker는 head wall >1.5배, CPU <1.2배, engine reads <0.8배이며 제품 합격 기준이 아니다.
종료 시 같은 명령을 `--name closing`으로 재실행해 base 2.36초/OOS 5.70초의 RED 판정을 다시 얻었다.
총 native 성능 표본은 60개, 별도 traced 실행은 2개, timed replay는 54개다.
이름 재사용을 거부하므로 재실행은 새 빈 artifact root에서 수행한다.

공유 가능한 입력은 [fixture.sql](fixture.sql), offline 도구는 [bounded_replay.py](bounded_replay.py),
선별 수치·artifact 이름·script fingerprint는 [기계 요약](selected-summary_dcbf09e.json)에 보존한다.
fixture와 명령을 다른 Linux 호스트로 옮길 때는 독립 source/install/DB와 registry·port·TMP·설정을 먼저 분리한다.
같은 source도 재적재 시 물리 배치가 달라질 수 있으므로 새 trace로 대조하며 기존 숫자의 정확한 재현을 보장하지 않는다.

```sh
# 두 exact revision을 별도 source/install로 준비한다. 아래는 build profile의 예다.
cmake -S "$SOURCE" -B "$BUILD" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="$INSTALL" -DUNIT_TESTS=OFF -DUNIT_TEST_OOS=OFF
cmake --build "$BUILD" --parallel 4
cmake --install "$BUILD"
# 각 DB는 matching install의 createdb로 16KiB data/log page로 새로 만든다.
# data_buffer_size=512M, max_query_cache_entries=0, query_cache_size_in_pages=0을 설정한다.
csql -C -u dba -i fixture.sql "$DATABASE"
```

위 build 예는 이번 턴에 재실행한 명령이 아니다. 실제 compile command·최적화·계측 상태는 기존 `builds.json`과 이번 preflight를 근거로 확인했다.
raw DB가 준비된 현 호스트의 전체 재측정은 `remeasure.py`, trace 감사·분류는 `prepare_controls.py`, replay schedule은 `run_bounded.py`에 있다.

portable replay 입력은 manifest와 `request-types.tsv`다. manifest는 `source`, `install`, `volume_root`,
`volumes`의 `path/dev/ino/size`, `fd_map`, `request_types`를 포함한다. TSV는 captured fd·offset·size·ptype 4열이다.
도구는 해당 설치의 실행 프로세스가 있거나 volume identity·소유·scope가 다르면 읽기·cache advice를 거부한다.
정지한 전용 DB에서 자신의 trace와 manifest를 준비한 뒤 다음처럼 실행한다.

```sh
python3 -B bounded_replay.py --manifest head-manifest.json \
  --output fresh-h64-sort --policy heap-batch --window 64 --gap -1 --cpu 16
python3 -B bounded_replay.py --manifest head-manifest.json \
  --output fresh-h64-gap --policy heap-batch --window 64 --gap 16384 --cpu 16
```

실제 측정의 page type 2/14, 16KiB 크기에 고정된 도구다. 다른 source/layout에 무조건 적용하는 범용 DB runner가 아니다.
trace 재조립, 15개 작은 변형의 page multiplicity/gap 검사, 모든 timed trial의 요청 검증과 전후 전체 내용 hash를 확인했다.
inode가 다른 manifest는 cache advice 전에 거부되는 음성 검증도 확인했다.
종료 시 두 설정의 byte 복원, 바이너리 불변, source tracked clean과 해당 설치의 실행 프로세스 0개를 확인했다.
환경 점검의 root `compile_commands.json` 링크 누락 경고는 source 텍스트 탐색에 영향을 주지 않았고, build/install identity는 별도로 확인했다.
새 규범 설계의 채택, 엔진 단위·SQL·shell·medium 회귀나 회사 CI를 실행한 것으로 해석하지 않는다.
