https://jira.cubrid.org/browse/CBRD-26939

## Purpose

- AS-IS: OOS(큰 컬럼 값을 별도 페이지에 저장하는 방식)의 과거 로그에는 값 대신 저장 위치가 남았습니다. vacuum(더 이상 필요 없는 저장 공간의 회수)이 그 위치를 회수한 뒤 CDC(변경 내역 추출)와 flashback(과거 변경 SQL 조회)이 값을 읽으면 추출 실패나 서버 종료가 발생했습니다.
- TO-BE: 변경 시점의 실제 값을 별도 로그에 저장합니다. 원래 저장 공간이 회수된 뒤에도 보관된 로그에서 INSERT, UPDATE, DELETE의 과거 값을 읽습니다. 지원하지 않는 과거 형식과 잘못된 이미지는 명시적인 오류로 중단합니다.

이 문서는 승인된 ADR-0004의 durable supplemental image 설계와 로컬 티켓 01–04에 해당하는 구현과 검증 결과를 설명합니다. 소스 커밋은 `7d97d4bf63ee375da5fa6f6d2e4c1985f084532a`이며, PR의 대상 브랜치는 `feat/oos`입니다. 독립적인 JDBC `bug_bts_4633` 수리는 이 CDC 구현의 완료 근거에 포함하지 않습니다.

## Implementation

### Activation and compatibility

티켓 01의 `cubrid activatehistorydb`는 기존 데이터베이스가 새 로그 형식을 사용하도록 명시적으로 전환합니다. 전환 전에는 supplemental logging(변경 값을 추가로 기록하는 기능)이 필요한 OOS 쓰기를 거부합니다. 새 데이터베이스는 처음부터 현재 형식을 사용합니다.

디스크 호환성 식별자 `11.6`은 제품 버전 문자열과 별개입니다. 전환은 되돌릴 수 없으며, 이전 엔진은 복구 전에 현재 형식의 데이터베이스를 거부합니다. 오프라인 유틸리티는 정상 종료 상태와 배타적 활성 로그 잠금을 확인하고, 동기화가 성공해야 완료를 보고합니다. 운영 절차는 소스의 `docs/oos_history_activation.md`에 있습니다.

### Durable row images

`src/storage/heap_oos.cpp`의 `heap_oos_copy_expanded_record`는 OOS 값을 소유권이 분리된 버퍼에 펼칩니다. 호출자의 버퍼와 물리 복구 로그는 기존 표현을 유지합니다. `src/storage/heap_file.c`는 보호된 변경 전 레코드에서 before image를, 변경할 레코드에서 after image를 확보합니다. relocation(다른 힙 페이지로 옮겨진 레코드)은 해당 페이지를 고정한 상태에서 읽으며, eager cleanup(쓰기 중 즉시 공간 회수)보다 먼저 값을 확보합니다.

`LOG_SUPPLEMENT_OOS_IMAGE`는 기존 supplemental enum 값 뒤에 추가됩니다. payload는 레코드 종류와 완전히 펼친 레코드 바이트로 구성됩니다. DML 로그는 성공적으로 추가된 이미지의 LSA(로그 위치)만 참조합니다. INSERT는 after image, DELETE는 before image, UPDATE는 필요한 양쪽 이미지를 기록합니다. OOS가 없는 쪽은 기존 복구 로그 참조를 사용합니다.

DML 참조와 그 뒤의 사용자 메타데이터는 두 레코드의 메모리를 모두 확보한 뒤 같은 로그 큐 잠금 안에서 게시합니다. 사용자 메타데이터 확보 실패 시 DML 참조도 게시하지 않으므로, 실패한 statement의 반쪽짜리 DML 참조가 남지 않습니다. commit 시점의 선택적인 사용자 복사본에 의존하지 않습니다. 읽기 중 사용자 메타데이터가 아직 디스크에 보이지 않으면 같은 DML 위치를 재시도합니다.

이미지 생성, 메모리 할당, 로그 추가 및 DML 참조 추가 실패는 SQL 오류로 전달되어 일반 rollback 경로를 따릅니다. 기존 supplemental undo 추가 경로도 반환값을 확인합니다. 압축이 공간을 줄이지 못하면 원본 바이트를 기록하며, 압축 버퍼 할당 실패는 쓰기 실패로 전달합니다. supplemental logging이 꺼져 있으면 추가 이미지 생성 경로에 들어가지 않습니다.

### Historical readers

`src/transaction/log_manager.c`의 공통 디코더가 CDC와 flashback의 before/after image를 처리합니다. 이미지 헤더, 레코드 종류, 펼쳐진 상태와 VOT(가변 길이 속성의 위치 표)의 경계를 확인합니다. 이미지 payload 자체는 이벤트가 아니므로 DML 참조를 만났을 때만 해석합니다.

기존 non-OOS 로그는 계속 읽습니다. OOS 위치 참조가 남은 이전 형식은 `ER_CDC_LEGACY_OOS_IMAGE`(-1387), 잘못된 펼친 이미지는 `ER_CDC_INVALID_HISTORY_IMAGE`(-1388)로 거부합니다. 이 경로에서는 실제 OOS 슬롯을 읽지 않습니다. CDC는 요청 위치를 유지하며 오류를 반환하고, 새 세션은 지원되는 이후 로그 위치에서 추출할 수 있습니다. 일시적인 읽기·할당 오류는 영구적인 형식 오류로 바꾸지 않습니다.

flashback 출력은 trigger INSERT/UPDATE/DELETE를 처리합니다. partition(분할 테이블)의 경우 CDC는 기존처럼 부모 테이블 식별자를 노출하지만, flashback detail은 summary와 같은 분할 테이블 식별자를 유지합니다. 잘못된 클래스 인덱스도 배열 접근 전에 거부합니다. flashback 유틸리티는 지원하지 않는 이미지의 오류 원인을 화면에 표시합니다.

CCI의 오류 코드 헤더는 companion commit `268d152`와 일치시켰습니다. Windows 지원 코드는 추가하지 않았습니다.

## Remarks

### Verification

테스트는 SQL 결과, 공개 CDC API, flashback 출력, `SHOW ALL HEAP OOS`의 실제 회수 결과를 확인합니다. 고정된 32KB 값과 513바이트 추가 속성을 사용하며, 고엔트로피 fixture는 저장소에 고정된 바이트 파일입니다. 동일 길이의 서로 다른 값, 여러 청크, 양쪽 `all_in_cond` 모드의 ID·개수·값을 확인합니다.

| 검증 | 결과 / 증거 |
| --- | --- |
| RED: 티켓 01 엔진, DELETE 후 vacuum | `cdc.quFuD1`: OOS 90→0 후 추출 실패 및 서버 종료 |
| DELETE durable before image | `cdc.Ea91QH`: OOS 90→0, 양쪽 모드 10/10 |
| INSERT→UPDATE→DELETE 및 flashback | `cdc.UR4rg3`: 양쪽 CDC 30/30, flashback 30 |
| 8KB, 압축, 여러 속성 | `cdc.v1JdqP`: OOS 60→0, CDC 30/30, flashback 30 |
| 16KB, 압축, 고엔트로피 값 | `cdc.6LcyRm`: OOS 40→0, CDC 30/30, flashback 30 |
| trigger, 강제 종료 복구, backup/restore | `cdc.tpNQH8`: 8KB·압축·고엔트로피, CDC 60/60, flashback 60; trigger I/U의 기존 full-row 경로 포함 |
| partition | `cdc.YoGpcJ`: OOS 84→40, 양쪽 CDC 30/30, flashback 30 |
| OOS 초기 행의 DELETE 및 audit trigger | `cdc.Bp4ecW`: OOS 100→0, 양쪽 CDC 20/20, flashback 20 |
| legacy / malformed flashback 오류 및 생존 | `cdc.fhAqcx` / `cdc.Z2T2Cz`: 명시적 오류, CDC 위치 유지, 서버 생존 |
| 생성·추가·참조·사용자 메타데이터 실패 × INSERT/UPDATE/DELETE | `cdc.S7LyLx`: 사용자 메타데이터 포함 12개 SQL 실패 후 원래 10개 행·값 유지, 이후 CDC/flashback DELETE 10개 통과 |
| 잘못된 이미지 거부 후 새 세션에서 재개 | `cdc.TTeTep`: 오류 반복 시 위치 유지, 이후 정상 값 추출, 서버 생존 |
| 원래 CTP `cbrd_27064`, `cbrd_27075` | `regressions.Mq331X`: INSERT/DELETE/UPDATE 및 4/8/16KB rollover 회귀 통과 |
| 구성된 전체 테스트 | `ctest.Adj8oO`: 27/27 통과. 최종 메타데이터 변경 후 `ctest.iLL4hg`: 26 통과·server 60초 시간 초과. 해당 테스트와 fixture를 별도 실행한 `ctest.MLM8as`: 3/3 통과(37초) |

원래 CTP 테스트 소스 커밋: `a8d61f27443e3c8b56bcaf94b23a8b88dff9069a`. 테스트 스크립트 자체는 수정하지 않고 private Linux namespace에서 실행했습니다. 테스트가 사용하는 `hostname -I`를 위해 private dummy 네트워크 주소를 제공했습니다. 엔진은 GCC debug 구성을 빌드했습니다. 선택적인 Manager 서버는 고정된 구형 libevent가 Linux에서 제거된 `sysctl` 심볼을 요구하여 로컬 구성에서 제외했습니다.

재현 명령:

```sh
HISTORY_LIFECYCLE=1 HISTORY_CLIENT_MODE=lifecycle \
  bash unit_tests/oos/scripts/test_cdc_history.sh /path/to/current/install
HISTORY_PARTITION=1 HISTORY_PAGE_SIZE=16K HISTORY_LIFECYCLE=1 HISTORY_CLIENT_MODE=lifecycle \
  bash unit_tests/oos/scripts/test_cdc_history.sh /path/to/current/install
HISTORY_CORRUPT=1 HISTORY_CLIENT_MODE=reject HISTORY_REPOSITION=1 \
  bash unit_tests/oos/scripts/test_cdc_history.sh /path/to/current/install
HISTORY_FAULTS=1 bash unit_tests/oos/scripts/test_cdc_history.sh /path/to/current/install
```

### Cost observations

4KB 페이지와 압축을 사용한 고엔트로피 10행 INSERT→UPDATE→DELETE 작업을 추가 기록 활성/비활성으로 비교했습니다. 공개 `SHOW LOG HEADER`의 append 위치 차이를 페이지 크기로 환산한 값이며, 페이지 헤더·정렬·일반 로그도 포함합니다. `cdc.PM2Gjb`(활성)와 `cdc.ZY8E3Q`(비활성)의 관측값입니다.

| 관측 | 활성 | 비활성 |
| --- | ---: | ---: |
| 로그 위치 증가량 환산 | 1,310,928 bytes | 742,912 bytes |
| SQL 작업 경과 시간 | 0.601 s | 0.640 s |
| 서버 최대 RSS | 366,720 KiB | 362,880 KiB |

추가 로그 비용은 관측되지만 시간과 RSS 차이를 단독 기능 비용으로 해석할 수 없습니다. 짧은 동시 실행, SQL 연결 비용, 스케줄링, 기존 메모리 풀을 포함한 관측이며 serialization만 분리한 마이크로벤치마크가 아닙니다. 성능 합격 기준을 새로 설정하지 않았습니다.

### Boundaries

- 활성화는 기존 OOS 로그에 누락된 과거 값을 복원하지 않습니다. 이전 reader와 HA 구성요소는 전환 전에 함께 교체해야 합니다. 기존 독립 applier까지 엔진의 시작 검사가 차단해 주지는 않습니다.
- trigger의 INSERT/UPDATE는 현재 엔진에서 기존 full-row 저장 경로를 쓰는 경우도 있어 그 경로의 결과를 함께 검증했습니다. 별도 초기 OOS 행 DELETE+trigger 테스트는 실제 OOS 회수 뒤 값을 검증했습니다.
- 필요한 로그 보관과 스키마 가용성은 기존 CDC/flashback 계약을 따릅니다. 이미 삭제된 archive나 변경된 스키마를 복원하는 기능은 아닙니다.
- partition 테스트에서 초기 부모 파일의 OOS 레코드가 일부 남는 별도 저장 동작이 관측되었습니다. 검증은 실제 회수된 레코드와 정확한 역사 값을 확인하며, 모든 partition 저장 공간이 0이 된다고 주장하지 않습니다. 일반 테이블 테스트에서는 0까지 회수된 뒤 추출했습니다.
- `bug_bts_4633`의 JDBC undo-read crash는 별도 티켓 05입니다. 전체 원본 PR의 성공은 그 수리와 최종 CI까지 확인해야 합니다.
- 설계는 앞선 grill-with-docs에서 승인된 ADR-0004와 여섯 티켓의 결정을 유지합니다. 구현 리뷰에서 발견한 압축 실패 분류, 기존 append 오류 전달, 이미지 경계 검사, 큐 오류 초기화, partition 식별자 문제를 반영했습니다.
