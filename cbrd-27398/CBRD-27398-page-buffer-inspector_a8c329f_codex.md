https://jira.cubrid.org/browse/CBRD-27398

## Purpose

페이지 버퍼는 디스크 페이지를 메모리에 보관하는 공간이다. 진단 도구가 페이지별 상주 여부와 변경 상태를 읽을 수 있도록, Linux 서버에 선택적으로 활성화하는 읽기 전용 관찰 인터페이스를 추가한다.

- AS-IS: 디스크 페이지 지도와 버퍼 집계 정보만으로는 특정 페이지의 상주·dirty·latch 상태를 연결해서 확인하기 어렵다.
- TO-BE: 서버가 제한된 범위의 상주 페이지 상태를 JSON-lines로 제공하며, 소비자는 볼륨·페이지 식별자로 디스크 지도와 연결할 수 있다.

이 PR은 엔진 생산자, wire 계약, 테스트와 검증 기록을 포함한다. Volmap의 HTTP·브라우저 구현은 별도 저장소의 변경이다.

기준 소스: `a8c329fef5bf14ea09a5c156bb4a17967b262480`.
대상 develop: `c3967ec22ada2dd71d1cd45b0705d09d0d425ec3`.

## Implementation

### 활성화와 수명

`src/base/system_parameter.c`와 `.h`에 숨김 서버 전용 Boolean `enable_pgbuf_inspector`를 추가한다. 기본값은 false이며 시작 시 한 번 읽는다. 기존 파라미터 번호를 유지하기 위해 새 ID와 정의를 끝에 추가한다.

`src/transaction/boot_sr.c`는 서버 시작 후 inspector를 초기화하고 버퍼 관련 daemon을 종료하기 전에 해제한다. `src/storage/pgbuf_inspector.cpp`는 비활성 상태에서 daemon과 socket을 만들지 않는다. 활성화 실패 시 경고를 남기고 데이터베이스 시작을 계속한다. 이번 서버 endpoint는 Linux에만 연결한다.

### 접속과 데이터베이스 식별

`src/storage/pgbuf_inspector_socket.cpp`는 Unix domain stream socket과 비차단 입출력을 구현한다. 전용 디렉터리는 0700, socket은 0600이며 `SO_PEERCRED`로 같은 effective UID만 허용한다. 안전하지 않은 기존 경로는 보존하며 종료 시 자신이 만든 socket만 제거한다.

Handshake는 재시작마다 달라지는 incarnation과 데이터베이스 생성 정보, 영구 볼륨의 생성 정보·device·inode, LRU 구성을 전달한다. 소비자는 자신의 대상과 이 정보를 비교해야 한다. `src/storage/disk_manager.c`는 정상 boot/format/recovery 경로에서 생성 정보를 캐시하여 관찰 접속 때문에 볼륨 헤더 페이지를 읽지 않도록 한다.

### 버퍼 관찰과 결과 해석

`src/storage/page_buffer.c`의 `make_scan_source`는 버퍼 슬롯 관리 정보인 BCB의 mutex를 한 번 비차단 방식으로 획득하고 스칼라 값만 복사한다. 획득 실패는 부분 관찰로 표시한다. Latch는 페이지 접근을 조정하는 상태이며, latch tuple과 flags tuple은 각각 한 번의 atomic 읽기로 얻는다.

페이지 종류와 로그 위치인 LSA는 latch 없음·fix count 0·flush 중 아님을 확인한 경우에만 읽는다. 그 외에는 해당 필드를 생략하여 unknown을 표현한다. 페이지 fix/load, 내용 복사, 디스크 읽기 또는 hot path 계측을 추가하지 않는다. 복사 후 mutex를 풀고 직렬화·socket 전송을 수행한다.

Develop의 native page type을 의미 문자열로 변환한다. 공유 wire vocabulary에는 예약값 `oos`가 남지만 develop 생산자는 이를 만들지 않는다.

결과는 전체 풀을 한 시점에 고정한 snapshot이 아니다. 정상 footer가 있는 완전 scan에서 빠진 페이지는 관찰상 비상주이며, 부분 scan에서 빠진 페이지는 unknown이다. Dirty와 LSA는 commit 여부나 디스크 영속성을 증명하지 않는다.

### Wire와 자원 제한

`pgbuf_inspector_wire.*`, `pgbuf_inspector_protocol.cpp`, `pgbuf_inspector_scan.*`에 framing, 검증, 상태 변환과 순회를 나눈다. `docs/pgbuf-inspector/v1/`은 v1 계약과 재생 가능한 conformance corpus를 제공한다.

| 항목 | 현재 구현 한계 |
| --- | --- |
| 동시 접속 / scan 시작 간격 | 2개 / 전체 접속에 걸쳐 최소 100 ms |
| scan 방문 슬롯 / 출력 레코드 | 각각 65,536개 |
| scan 전체 출력 | 1 GiB 상한; 전체 결과를 메모리에 보관하지 않음 |
| 페이지·control frame / handshake | 4 KiB / 64 KiB |
| 연결별 출력 버퍼 / JSON depth | 64 KiB / 16 |
| 순회 경과 / 전체 교환 | 1,500 ms / 2 s |
| write 진행 없음 / handshake | 250 ms / 500 ms |

매 polling turn의 순회 작업은 약 2 ms로 제한하며 다음 turn에 이어간다. Footer 공간을 먼저 확보하고, 한계에 도달하면 partial 여부를 표시한다. 시간 한계는 스케줄링 영향을 받으므로 실시간 보장이 아니다.

### 빌드와 테스트 연결

`cubrid/CMakeLists.txt`는 Linux 서버에 생산자를 연결한다. `UNIT_TEST_PGBUF_INSPECTOR`로 테스트 실행 파일과 native fixture를 구성하고 최상위 `enable_testing()`으로 CTest 등록을 보장한다. Native fixture는 13개 develop page kind와 독립적으로 제어한 페이지 상태를 확인한다.

## Remarks

### 검증 결과

2026-09-12 develop 재배치 후 동일 소스 내용으로 GCC Debug 빌드와 별도 디렉터리 설치를 완료했다. 호환성 커밋의 pre-commit 포맷 검사에서 소스 변경은 없었다. 당시 CTest 실행 기록을 PR 작성 시 다시 확인했다.

- `test_pgbuf_inspector`: 62 test cases, 1,120,566 assertions 통과.
- `test_pgbuf_inspector_native`: 13개 develop page kind, clean/dirty 관찰, complete/partial scan, eviction 뒤 비상주/unknown 구분과 종료 검증 통과.
- 등록된 CTest 2개 모두 통과, 총 110.56초.
- develop 대비 diff 공백 검사 통과.

테스트 빌드에서 `UNIT_TEST_PGBUF_INSPECTOR=ON`을 활성화하고, 설치한 빌드에 맞게 `CUBRID`, 실행 경로와 라이브러리 경로를 설정한 뒤 `ctest --test-dir <build-dir> -R '^test_pgbuf_inspector(_native)?$' --output-on-failure`로 실행할 수 있다.

### Draft 범위와 남은 검증

현재 HEAD에 대한 Release·다중 UID credential·전체 CTP·Volmap end-to-end·전용 호스트 성능 검증을 이번 PR 작성에서 새로 실행하지 않았다. 저장소의 이전 통합·브라우저·release 기록은 당시 source/consumer에 대한 이력이며 현재 develop HEAD의 검증으로 확대하지 않는다. Native/단위 테스트 통과만으로 이슈의 전체 성능 수락 조건을 충족했다고 보지 않는다.

리뷰에서는 BCB 스칼라 접근 조건과 수명, 생성 정보 캐시 갱신 경로, socket 소유권·종료 처리, partial/unknown 해석을 우선 확인한다. Windows 및 비서버 endpoint, 페이지 이미지 비교, flush 이벤트 이력은 제공하지 않는다.
