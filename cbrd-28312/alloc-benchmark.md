# CBRD-28312 행 단위 레코드 버퍼 할당 비용 측정 기록

- 분석일: 2026-11-23 (Asia/Seoul)
- 이슈: [CBRD-28312](https://jira.cubrid.org/browse/CBRD-28312) (parent [CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978), relates [CBRD-28278](https://jira.cubrid.org/browse/CBRD-28278))
- 소스: `CUBRID/cubrid` `origin/develop` `ed394047b5` (2026-11-23 fetch)

## 질문과 결론

질문: OOS(PR #7990, `68a9c7766f`)가 `locator_attribute_info_force ()` 의 copy area 풀을 스택 지역 `heap_pending_record` 로 바꾸면서 생긴 행마다의 glibc `malloc`/`free` 가 서버 측 대량 INSERT ... SELECT·UPDATE에서 측정 가능한 비용인가.

결론:

- 레코드 버퍼 할당을 없애면(변형 B) 인라인 행에서 서버 명령어 수가 행당 134(INSERT)\~151(UPDATE)개, 0.68%·0.57% 줄었다. 10회 반복의 범위가 겹치지 않는다.
- cycle과 wall time은 공유 장비의 변동이 효과보다 커서 판정하지 못했다. 수행 시간 개선은 측정되지 않았다.
- OOS 행에서 레코드 버퍼 몫은 약 0.1%이고, 행마다 만드는 OOS vector들(`heap_oos_finalize_record ()` 등)이 0.6\~2.3%로 더 크다.
- 서버 할당 비용의 대부분(6\~13%)은 OOS와 무관한 log prior list 노드 할당이다.
- 작성자 결정(2026-11-23): 효과가 명령어 수 1% 미만이고 설계 선택지가 남아 있어, 수정은 ANALYSIS로 넘기고 이번에는 구현하지 않는다.

## 구현과 변형

- A: `ed394047b5` 그대로.
- B: A에 [variant-b-stack-buffer.patch](bench/variant-b-stack-buffer.patch)를 적용. `locator_attribute_info_force ()` 의 pending record 버퍼를 `cubmem::stack_block<IO_MAX_PAGE_SIZE>` 외부 버퍼로 바꾼다. 측정 전용이다. 외래 키 cascade 재귀 시 스택 사용량, debug assert 완화 등은 검토하지 않았다.
- 빌드: `release_gcc` 사용자 preset(CMake RelWithDebInfo, `-O2 -DNDEBUG -finline-functions -ggdb -fno-omit-frame-pointer`), `UNIT_TESTS` 와 `UNIT_TEST_*` 모두 OFF, `compile_commands.json` 에 `CUBRID_UNIT_TEST_ENABLED` 없음. GCC 11.5.0, glibc 2.34.
- 설치: 각 변형을 별도 prefix로 복사(`libcubrid.so` sha256 앞부분 A `687b301e83b9e6bb`, B `622663f3fc1f3532`).
- 로컬 `develop` `16325f31b6` 은 `e2bfdc3939`(CBRD-28188) 의 `OR_MVCC_FLAG_SHIFT_BITS` 때문에 컴파일되지 않아 `origin/develop` 을 썼다(`208ea37f11` 에서 수정됨).

## 상태와 환경

- 호스트: Xeon Gold 5218R 2소켓 80 thread, Linux 5.14.0-570.30.1.el9_6, 공유 장비(측정 중 load average 약 7\~13). affinity, governor 변경 없음.
- 변형별 별도 DB, CS 모드 서버 1개, `csql -C` 클라이언트 1개. `cubrid.conf`: `data_buffer_size=4G`, `log_buffer_size=256M`, `enable_string_compression=n`, `java_stored_procedure=no`, 변형별 `cubrid_port_id`. `createdb --db-volume-size=4G --log-volume-size=1G benchdb en_US.utf8`, page 16KB.
- 원본: `create table src (id int primary key); insert into src select level from db_root connect by level <= 1000000;`
- 반복마다 `t_in (id int, s varchar(64), n int)`, `t_oos (id int, big varchar(10000), n int)` 를 새로 만든다. OOS 행은 6,000B 값 1개로 quarter-page inline target을 넘겨 OOS로 간다.
- 워크로드와 수집 명령은 [run.sh](bench/run.sh)(10회, A/B 순서 교대)다. 문장마다 서버 CPU가 1초에 2 tick 이하가 될 때까지 기다린 뒤 `perf stat -x, -e instructions:u,cycles:u -p <cub_server pid> -- csql ...` 로 서버 프로세스 전체를 센다. 문장마다 새 csql 연결이므로 연결 비용이 같은 크기로 들어간다. 원자료: [results.csv](bench/results.csv). 환경 파일 [env.sh](bench/env.sh)의 경로는 측정 호스트의 임시 경로다.

## 결과

10회 중앙값(최소\~최대), 서버 명령어 수.

| 문장 | 행 | A | B | B−A | 행당 |
|---|---|---|---|---|---|
| `insert into t_in select id, 'val' \|\| id, id from src` | 1,000,000 | 19.699G (19.691\~19.715) | 19.565G (19.558\~19.575) | −0.68% | −134 |
| `update t_in set n = n + 1` | 1,000,000 | 26.619G (26.560\~26.779) | 26.468G (26.408\~26.538) | −0.57% | −151 |
| `insert into t_oos select id, id \|\| repeat('x', 6000), id from src where id <= 100000` | 100,000 | 7.904G (7.752\~7.934) | 7.906G (7.833\~7.931) | +0.02% | 구분 안 됨 |
| `update t_oos set n = n + 1` | 100,000 | 3.586G (3.582\~3.634) | 3.580G (3.575\~3.625) | −0.17% | 구분 안 됨 |
| `update t_oos set big = big \|\| 'y' where id <= 20000` | 20,000 | 2.408G (2.405\~2.481) | 2.407G (2.399\~2.466) | −0.04% | 구분 안 됨 |

cycle 중앙값 차이(B−A): +1.40%, −0.10%, −1.19%, −0.70%, +3.34%. wall 중앙값 차이: +2.32%, −1.77%, −1.51%, +0.51%, +5.46%. 같은 변형의 cycle 최대값이 최소값의 약 2배까지 나와(ins_inline A 9.34G\~17.90G) 판정하지 않는다.

## 프로파일 귀속

변형 A에서 [profile.sh](bench/profile.sh)로 문장별 `perf record -e instructions:u -c 200003 --call-graph lbr` 를 받고 [attr2.py](bench/attr2.py)로 glibc 할당 함수에 떨어진 표본을 첫 호출자로 묶었다. glibc에는 frame pointer가 없어 `--call-graph fp` 로는 호출자가 대부분 끊겼고, LBR로 다시 받았다. upd_inline은 첫 수집 파일이 깨져(data size 0) 같은 테이블에 UPDATE를 한 번 더 실행해 따로 받았다(idle 대기 5초).

| 호출자 묶음 | ins_inline | upd_inline | ins_oos | upd_oos_n | upd_oos_big |
|---|---|---|---|---|---|
| 레코드 버퍼 | 0.52% | 0.67% | 0.10% | 0.12% | 0.11% |
| OOS payload | --- | --- | 0.46% | --- | 0.22% |
| OOS 계획·finalize·참조 vector | --- | --- | 0.62% | 2.34% | 1.82% |
| log prior list | 6.10% | 8.09% | 6.54% | 6.42% | 13.41% |
| 연결 시 `sysprm_unpack_session_parameters ()` → `calloc` → `malloc_consolidate`(측정 방법의 부산물) | --- | --- | 6.29% | 9.87% | 3.84% |
| 기타 | 0.58% | 3.67% | 0.23% | 0.35% | 1.01% |

upd_oos_n의 OOS vector 몫 중 `heap_oos_finalize_record ()` 가 1.03%, `std::vector<oos_chain_ref>` 확장이 0.64%, `std::vector<heap_oos_column_plan>` 이 0.26%다.

## 한계와 다음 실험

- 클라이언트 1개만 쟀다. 동시 DML에서 glibc arena 경합이 수행 시간 차이를 키우는지는 모른다. 다음 실험은 같은 워크로드를 여러 세션에서 동시에 돌려 throughput을 비교하는 것이다.
- OOS 이전 develop(`68a9c7766f^`)과 직접 비교하지 않았다. 그 비교는 [CBRD-27816](https://jira.cubrid.org/browse/CBRD-27816)이 UPDATE에 대해 했다.
- B는 레코드 버퍼만 바꿨다. OOS vector를 줄인 변형은 재지 않았다.
- loaddb, REPLACE, ON DUPLICATE KEY UPDATE, copy area, 파티션 재분배의 `heap_pending_record` 는 재지 않았다.
