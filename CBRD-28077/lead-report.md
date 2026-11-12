# 큰 컬럼의 행 밖 저장 방식 비교

CBRD-28077 첫 번째 실행에 대한 팀장 검토용 보고서

이 보고서는 팀장이 OOS 보완과 대안 POC의 후속 검증 우선순위를 판단할 수 있도록, 동일 workload에서 관찰한 저장 방식별 이득과 비용을 설명한다. 대상은 `run-20261112-220750`이며, 측정 시각은 2026-11-12 22:07부터 2026-11-13 00:34까지이다. 시각은 Asia/Seoul 기준이다. 기존 측정 자료와 소스를 분석한 보고서이며, 새로운 성능 실험의 결과는 포함하지 않는다. [실행 보고서][run]

> **정정 (2026-11-13).** 이 보고서를 쓴 뒤, 1차 실행의 S7과 S8b가 의도한 크기의 값을 쓰지 않았다는 것을 확인했다. develop에서 같은 형태의 UPDATE를 plan 재사용으로 실행하면 `REPEAT(X'..', N)`이 N/4 크기의 텍스트를 저장하기 때문이다. 그래서 이 보고서의 S7·S8b 수치는 큰 값을 1/4 크기 값으로 바꾸는 비용이다. S8s, S9와 io 조건의 변경도 그 상태 위에서 측정되었다. 반복 측정, 빌드 간 결과 검사, 값 길이 검사를 더한 3차 실행이 이 항목들을 대체한다: [run3-report.md](run3-report.md). S1·S2·S3·S5의 방향과 OOS 재적재, Inner Table index 경로에 관한 결론은 3차 실행에서도 재현되었다.

## 1. 초록 (Abstract)

큰 값을 행 밖으로 분리하면 작은 열만 읽는 작업의 페이지 접근을 줄일 수 있다. 그러나 큰 값의 접근 방식과 버전 수명 관리에 따라 읽기와 쓰기의 비용은 달라진다. 본 연구는 develop을 기준으로 OOS, Sidecar, Inner Table을 비교한다. 압축되지 않는 값의 크기를 바꾸고, 작은 버퍼와 캐시 제거를 사용하는 io 조건 및 큰 버퍼를 사용하는 warm 조건에서 조회와 변경 workload를 측정한다.

행 밖 저장이 동작하는 8 KB와 64 KB에서 작은 열 scan의 서버 명령어 수는 io 조건에서 develop의 0.01~0.07배이다. 반면 작은 열만 바꾸는 전체 UPDATE는 OOS에서 12.81~16.26배, Sidecar에서 0.07~0.18배, Inner Table에서 0.42~0.66배이다. 큰 값을 교체하는 S6는 모든 설계에서 develop보다 많은 명령어를 사용한다. Inner Table의 큰 값 scan은 io에서 2.25~3.80배, warm에서 9.53~11.25배이다. 이 수치는 경과 시간의 배율이 아니다. [집계 표][tables]

OOS의 미변경 값 재적재는 별도 probe와 profile로 확인됐다. Inner Table의 작은 열 PK 조회가 큰 값을 읽는 이유는 scan 경로별 참조 확장 설정의 차이로 소스에서 확인됐다. 다만 큰 값 scan의 비용을 각 함수에 배분하는 설명은 profile하지 않은 추론이다. 이번 관찰에서는 Sidecar가 후속 검증의 우선 후보라는 판단을 내린다. 공용 서버 부하, 변경 작업의 단일 표본, 서로 다른 develop 기반, 미완성 운영 기능 때문에 제품 채택이나 최종 설계 우위까지 결론내리지는 않는다. [실행 후 확인 사항][brief], [실행 보고서][run]

## 2. 배경과 연구 질문

### 2.1 대안 설계가 필요한 이유

OOS는 큰 컬럼 값을 전용 파일로 분리한다. 작은 열만 읽을 때 큰 값을 읽지 않는다는 장점이 있지만, 분리된 값의 주소와 수명을 heap 행의 MVCC 수명에 맞추는 별도 처리가 필요하다. 대안 POC가 등장한 배경은 다음 결함 부류이다. 아래 항목은 제공된 설계 이슈의 문제 분류이며, 이번 성능 실험에서 재현한 정확성 결함 목록은 아니다. [Sidecar 설계 이슈][sidecar-issue], [Inner Table 설계 이슈][inner-issue], [CBRD-27230 설명][dedup]

| 결함 부류 | 관련 근거 | 설계 판단에서의 의미 |
| --- | --- | --- |
| 슬롯 재사용, undo, vacuum 사이의 수명 불일치와 잘못된 회수 | CBRD-27858, CBRD-27781, CBRD-27237, CBRD-26950 | 주소가 재사용되거나 rollback으로 값이 복원돼도 살아 있는 값을 회수하지 않아야 한다. |
| OOS chain 회수 누락 | CBRD-28035 | 논리적 삭제 이후 실제 공간 회수까지 책임을 추적해야 한다. |
| 동시 INSERT의 OOS 파일 헤더 경합 | CBRD-27827 | 단일 접속의 읽기 이득으로 동시 쓰기 확장성을 설명할 수 없다. |
| 미할당 큰 값의 재판독과 재적재 | CBRD-27230 | 작은 열만 바꿔도 큰 값의 읽기, 쓰기, 이전 값 회수 비용을 낼 수 있다. |

Sidecar는 큰 값을 테이블별 store heap의 일반 MVCC 레코드로 저장한다. Inner Table은 값을 숨은 companion 테이블의 chunk 행으로 저장한다. 두 설계는 분리된 값의 수명을 기존 heap과 vacuum 경로에 맡기려 한다. 기존 경로를 사용한다고 정확성이 자동으로 보장되지는 않는다. 설계 이슈에는 기존 heap 경로의 슬롯 보호 결함인 CBRD-27935와 CBRD-27936을 대안 POC에서도 확인했다는 기록이 있다. [Sidecar 설계 이슈][sidecar-issue], [Inner Table 설계 이슈][inner-issue]

### 2.2 이번 실행이 묻는 것

핵심 질문은 큰 값을 분리했을 때 어떤 workload에서 이득을 얻고, 어떤 workload에서 그 이득을 상쇄하는 비용을 내는가이다. 작은 열 scan뿐 아니라 PK 조회, 대량 적재, 큰 값 교체, 반복 commit, DELETE와 후속 회수를 함께 살핀다. 기능을 사용하지 않는 작은 값에서도 비용이 늘어나는지 확인한다. [비교 실험 이슈][benchmark-issue]

비교의 단위는 추상적인 설계가 아니라 지정된 커밋과 설정의 구현이다. 특히 develop도 64 KB 행은 overflow로 저장한다. 따라서 비교는 모든 큰 값이 한 페이지 안에 있는 기준과의 비교가 아니다. 행 전체의 overflow와 열 단위 분리의 차이도 포함한다. [실행 보고서][run]

## 3. 비교 대상과 실험 설계

### 3.1 빌드와 저장 정책

| 대상 | 측정 브랜치 | 측정 커밋 | 기준 develop | 이번 실험의 저장 조건 |
| --- | --- | --- | --- | --- |
| develop | `develop` | `a7f220d5d7` | 해당 없음 | 8 KB 행은 inline, 64 KB 행은 overflow이다. |
| OOS | `feature/oos-merge` | `c02f897268` | `a7f220d5d7` | 행이 inline 목표 약 4,060 B를 넘으면 큰 값부터 OOS 파일로 옮긴다. |
| Sidecar | `sidecar` | `7c5028d5bd` | `e64a04a79a` | 기본 `sidecar_inline_target=4060`을 사용한다. 대상 값의 최소 크기는 256 B이다. |
| Inner Table | `inner-table` | `fbb4f25057` | `81fa5696cd` | `inner_table_threshold=4060`과 `t__inner`를 사용한다. |

커밋과 기반 정보는 [실행 보고서][run] 및 [비교 실험 이슈][benchmark-issue]를 따른다. Inner Table은 행 길이를 먼저 검사하고, 이동할 개별 값의 인코딩 길이에도 threshold를 적용한다. 같은 숫자의 threshold가 모든 행 형태에서 같은 이동 정책을 뜻하지는 않는다. 이번에는 큰 값 하나를 둬 8 KB와 64 KB에서 모든 설계가 분리하도록 했다. [Inner Table 이동 조건][inner-threshold]

모두 별도 worktree와 설치 경로에서 `release_gcc` preset으로 빌드했다. GCC 11.5, RelWithDebInfo, `-O2` 조건이다. develop과 OOS는 `src/optimizer/query_planner.c`의 `-Werror=return-local-addr`로 release 빌드가 실패했다. develop, OOS, Sidecar에는 `-Wno-error=return-local-addr`을 추가했다. 이 옵션은 경고를 오류로 취급할지만 바꾸며 생성 코드는 바꾸지 않는다. 네 DB 모두 `ha_mode=off`이다. Java PL 서버가 시작되지 않아 `stored_procedure=no`로 통일했다. [실행 보고서][run], [실행 후 확인 사항][brief]

### 3.2 테이블과 데이터

실제 driver의 테이블은 다음과 같다. 초기 계획의 VARCHAR 대신 압축되지 않는 BIT VARYING을 사용하므로, 문자열 압축률 차이가 비교에 들어가지 않는다. `big`은 `REPEAT(X'AB', SIZE)`로 생성한다. [측정 driver][driver]

```sql
CREATE TABLE t (
	id INT PRIMARY KEY,
	k INT NOT NULL,
	s VARCHAR(50),
	big BIT VARYING
);
```

| big 크기 | 실제 바이트 수 | 초기 행 수 | 비교 목적 |
| --- | ---: | ---: | --- |
| 100 B | 100 | 1,000,000 | 모든 설계에서 inline인 기능 미사용 조건이다. S10에 해당한다. |
| 2 KB | 2,048 | 400,000 | 모든 설계에서 inline인 추가 대조 조건이다. |
| 8 KB | 8,192 | 120,000 | develop은 페이지당 한 행을 두며, 나머지 설계는 큰 값을 분리한다. |
| 64 KB | 65,536 | 16,000 | develop의 행 overflow와 열 단위 분리를 비교한다. |

이 문서의 KB 표기는 위 바이트 수를 뜻한다. 파일과 OS I/O 표의 MiB는 바이트 수를 `2**20`으로 나눈 값이다. 적재 직후의 별도 저장 확인에서는 8 KB 값 12,000행에 대해 OOS 레코드 12,000개, Sidecar store 레코드 12,000개, Inner Table chunk 행 24,000개를 확인했다. 이 저장 확인 표본은 본 실행의 120,000행과 구분한다. [실행 보고서][run], [집계 코드][analysis]

### 3.3 버퍼, 캐시, 실행 순서

| 조건 | data buffer | 시작 상태와 해석 |
| --- | --- | --- |
| io | 128M | 각 측정 SQL 묶음 전에 서버를 재시작한다. 서버를 멈춘 상태에서 DB 파일에 `posix_fadvise(DONTNEED)`를 적용한다. |
| warm | 4G | 읽기 workload를 한 번 실행해 데운 뒤 측정한다. 변경 workload는 앞선 작업이 남긴 상태에서 실행한다. |

각 크기와 빌드 조합마다 새 DB를 만든다. 실행 순서는 S4 적재, io 읽기, warm 읽기, warm 변경, io 변경이다. 변경 단계 안에서는 S5, S6, S7, S8b, S8s, S9 순서를 따른다. 따라서 io 변경은 warm 변경이 남긴 데이터와 파일 상태를 이어받는다. io와 warm은 같은 초기 DB에서 독립적으로 시작한 표본이 아니다. [측정 driver][driver]

io의 캐시 제거는 각 PK 조회 한 건마다 수행하지 않는다. S3의 5,000건 묶음 전에 수행하므로, 묶음 안에서 캐시가 데워지는 효과를 포함한다. OS 캐시 제거도 advisory 호출이며 전체 시스템의 모든 캐시를 초기화하는 절차는 아니다. [측정 driver][driver]

### 3.4 시나리오

| 시나리오 | 실제 작업 | 조건별 반복 수 |
| --- | --- | --- |
| S1 | `SELECT SUM(k) FROM t`로 작은 열 전체 scan | io와 warm 각각 3회 |
| S2 | `SELECT COUNT(*) FROM t WHERE big > X'00'`로 큰 값 접근 전체 scan | io와 warm 각각 3회 |
| S3n | PK로 `k`만 읽는 조회 5,000건 | io와 warm 각각 3회 |
| S3w | PK 및 `big > X'00'` 조건으로 `COUNT(*)`를 구하는 조회 5,000건 | io와 warm 각각 3회 |
| S4 | `INSERT ... SELECT`로 초기 N행 적재 | warm에서만 1회 |
| S5 | `UPDATE t SET k = k + 1`로 전체 행 변경 | io와 warm 각각 1회 |
| S6 | 초기 행 수의 1/4 범위에 새로운 `big` 값 할당 | io와 warm 각각 1회 |
| S7 | 한 행의 `big` UPDATE, 한 행 INSERT, COMMIT을 3,000회 반복 | io와 warm 각각 1회 |
| S8b | 100개 hot 행 중 한 행의 `big` UPDATE와 COMMIT을 3,000회 반복 | io와 warm 각각 1회 |
| S8s | 100개 hot 행 중 한 행의 `k` UPDATE와 COMMIT을 3,000회 반복 | io와 warm 각각 1회 |
| S9 | `MOD(id, 4)`의 특정 나머지 조건에 속한 행 DELETE | io와 warm 각각 1회 |
| S10 | 100 B 데이터에서 위 작업을 수행해 기능 미사용 비용 확인 | 별도 SQL 시나리오가 아니라 데이터 크기 조건이다. |

S5, S6, S9는 SQL 문장 단위 트랜잭션이다. S7과 S8은 루프마다 명시적으로 commit한다. 난수 seed를 고정해 같은 작업 대상을 사용한다. S2와 S3w는 큰 값을 조건 평가에 사용하지만 큰 값 전체를 클라이언트로 전송하는 실험은 아니다. [측정 driver][driver]

S7과 S8b의 UPDATE는 같은 모드 안에서 동일한 바이트 값을 반복 할당한다. 특히 S8b는 같은 hot 행을 다시 선택하면 이미 같은 값일 수 있다. 매번 다른 내용으로 큰 값을 교체하는 workload와 구분해야 한다. [측정 driver][driver]

### 3.5 지표와 집계 범위

| 지표 | 수집과 집계 | 해석의 범위 |
| --- | --- | --- |
| 서버 명령어 수 | `perf stat -e instructions,cycles,task-clock -p <cub_server>` | 본문의 주 지표이다. 변경은 SQL 실행과 drain의 명령어 수를 합한다. 클라이언트 비용은 포함하지 않는다. |
| data page fetch 및 page I/O | `cubrid statdump -c` 전후 차이 | 기존 집계 표의 fetch 및 read는 SQL 측정 구간이며 drain을 합하지 않는다. |
| OS 읽기 바이트 | `/proc/<cub_server>/io`의 `read_bytes` 차이 | SQL 측정 구간이다. page fetch 횟수와 물리 읽기 바이트는 다른 지표이다. |
| OS 쓰기 바이트 | 같은 파일의 `write_bytes` 차이 | drain을 합한다. 데이터 파일만의 쓰기량은 아니다. |
| log page 쓰기 횟수 | `Num_log_page_iowrites` 차이 | drain을 합한다. 논리적인 WAL 생성 바이트와 동일하지 않다. |
| 경과 시간 | csql 프로세스의 wall time | 클라이언트 실행 비용을 포함하지만 drain은 별도이다. 결론의 주 지표로 사용하지 않는다. |
| DB 관련 파일 크기 | driver의 `db_bytes` | 데이터와 로그 경로 아래 파일의 `st_size` 합계이다. 순수한 테이블 데이터 크기가 아니다. |

각 측정 전에는 CPU 누적 사용량을 0.25초 간격으로 관찰해 8회 연속 driver의 저부하 기준을 만족하는 idle 상태를 기다린다. 변경 후에도 같은 기준까지의 일을 drain으로 별도 수집한다. 이는 백그라운드 작업을 포함하려는 절차이며, 정확한 회수 완료나 모든 dirty page의 영속화를 검사하는 별도 검증은 아니다. `statdump`는 watcher가 등록된 동안만 전역 통계를 모으므로 driver가 서버 시작마다 `cubrid statdump -i 3600`을 유지한다. [측정 driver][driver], [집계 코드][analysis], [실행 후 확인 사항][brief]

비율은 각 조건의 중앙값을 develop 중앙값으로 나눈 값이다. 변경 작업은 표본이 하나라 중앙값이 그 측정값과 같다. 이하의 주요 비율 표는 소수 둘째 자리로 반올림한다. 1 미만이면 해당 지표의 일이 줄었다는 뜻이며, 그 역수만큼 응답이 빨라졌다는 뜻은 아니다. [집계 코드][analysis]

## 4. 예상 결과 (가설)

다음은 초기 실험 이슈와 저장 구조에서 재구성한 정성적 가설이다. 결과를 제시하기 전에 비교 기준을 명시하지만, 측정 전에 별도로 등록한 가설이라고 주장하지 않는다. 실행 후 발견한 Inner Table의 index 경로 차이는 가설에 소급해 넣지 않고 결과 해석에서 다룬다. [비교 실험 이슈][benchmark-issue], [대안 설계 설명][sidecar-issue], [Inner Table 설계 설명][inner-issue]

| 가설 | OOS의 예상 | Sidecar의 예상 | Inner Table의 예상 |
| --- | --- | --- | --- |
| H1. 작은 열 scan인 S1 | 작은 heap만 읽으므로 유리하다. | 작은 hot heap만 읽으므로 유리하다. | 참조 확장을 생략하면 companion을 읽지 않아 유리하다. |
| H2. 큰 값 scan과 큰 값 PK 조회인 S2, S3w | 큰 값 접근이 필요해 S1의 이득은 줄고 참조 처리 비용이 든다. 기준의 overflow 비용에 따라 손익은 달라진다. | store 읽기와 값 복사가 필요해 이득이 줄어든다. 큰 값은 store에서도 overflow를 사용할 수 있다. | chunk별 인덱스 검색, heap fetch, 값 복원 때문에 불리할 것으로 예상한다. |
| H3. 작은 열 PK 조회인 S3n | 큰 값 읽기를 생략하면 유리하다. 다만 단건 index 탐색 비용은 남는다. | 필요한 열만 해석하면 유리하다. | projection 생략이 단건 조회에도 적용된다면 유리할 것으로 예상한다. |
| H4. 대량 적재와 큰 값 교체인 S4, S6 | 분리 저장과 회수 비용 때문에 불리할 가능성이 있다. | store 레코드의 생성과 이전 값 은퇴 때문에 불리할 가능성이 있다. | 여러 chunk 행과 인덱스를 변경하므로 비용이 커질 것으로 예상한다. |
| H5. 작은 열 UPDATE인 S5, S8s | 큰 값을 읽지 않고 재사용할 수 있다면 유리하지만, CBRD-27230의 현행 재적재가 남아 있어 이득이 깨질 것으로 예상한다. | 미할당 참조를 유지하므로 유리할 것으로 예상한다. | 미할당 참조를 재사용하므로 쓰기는 줄지만, 읽기 경로의 확장 비용에 따라 이득이 제한될 수 있다. |
| H6. 혼합 변경과 큰 값의 반복 commit인 S7, S8b | 값 교체와 회수에 따른 비용을 예상한다. | 좁은 hot 행의 이득과 store 변경 비용이 경쟁한다. | chunk 및 인덱스 변경 비용이 반복되므로 불리할 가능성이 있다. |
| H7. DELETE와 후속 회수인 S9 | 작은 heap의 이득과 chain 회수 비용이 경쟁하므로 방향을 단정하지 않는다. | 작은 hot 행의 이득과 store MVCC 삭제 비용이 경쟁한다. | 여러 chunk의 MVCC 삭제와 인덱스 회수 때문에 불리할 가능성이 있다. |
| H8. inline 대조군인 S10 및 2 KB | 미사용 검사가 작다면 develop에 가까워야 한다. | 같은 기대를 둔다. | 참조 여부 검사 등 추가 경로가 있더라도 비용이 작아야 한다. |

정확한 순위나 배율은 위 가설만으로 예측하지 않는다. 특히 단일 변경 작업의 작은 차이는 반복 검증 대상으로 둔다.

## 5. 실제 결과

### 5.1 io 조건의 서버 명령어 수

각 값은 develop 대비 비율이다. 변경은 drain을 포함한다. S4는 io 측정이 없다. 표 전체를 [집계 표][tables] 및 [원시 결과][raw]와 대조했다.

| 시나리오 | 8 KB OOS | 8 KB Sidecar | 8 KB Inner Table | 64 KB OOS | 64 KB Sidecar | 64 KB Inner Table |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 작은 열 scan | 0.07 | 0.04 | 0.03 | 0.02 | 0.01 | 0.01 |
| S2 큰 값 scan | 1.35 | 1.09 | 2.25 | 1.05 | 1.05 | 3.80 |
| S3n 작은 열 PK 조회 | 0.98 | 0.93 | 1.23 | 0.61 | 0.64 | 1.62 |
| S3w 큰 값 PK 조회 | 1.20 | 0.99 | 1.12 | 0.94 | 0.99 | 1.65 |
| S5 작은 열 전체 UPDATE | 12.81 | 0.18 | 0.42 | 16.26 | 0.07 | 0.66 |
| S6 큰 값 UPDATE | 4.96 | 1.35 | 2.02 | 3.37 | 1.23 | 3.02 |
| S7 UPDATE와 INSERT 반복 | 2.19 | 1.26 | 1.16 | 1.86 | 1.07 | 1.54 |
| S8b 큰 값 UPDATE 반복 | 1.75 | 0.92 | 1.15 | 1.32 | 0.91 | 1.41 |
| S8s 작은 열 UPDATE 반복 | 1.73 | 0.75 | 0.90 | 2.09 | 0.73 | 1.24 |
| S9 DELETE | 0.41 | 0.52 | 0.98 | 0.69 | 0.77 | 3.09 |

### 5.2 warm 조건의 서버 명령어 수

| 시나리오 | 8 KB OOS | 8 KB Sidecar | 8 KB Inner Table | 64 KB OOS | 64 KB Sidecar | 64 KB Inner Table |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| S1 작은 열 scan | 0.30 | 0.12 | 0.08 | 0.17 | 0.08 | 0.07 |
| S2 큰 값 scan | 1.77 | 1.10 | 9.53 | 0.68 | 0.76 | 11.25 |
| S3n 작은 열 PK 조회 | 0.98 | 0.98 | 1.06 | 0.94 | 0.93 | 1.68 |
| S3w 큰 값 PK 조회 | 1.01 | 0.99 | 1.08 | 1.12 | 0.97 | 1.64 |
| S4 적재 | 0.94 | 1.02 | 1.16 | 1.02 | 1.02 | 1.35 |
| S5 작은 열 전체 UPDATE | 1.82 | 0.41 | 0.76 | 2.05 | 0.13 | 0.86 |
| S6 큰 값 UPDATE | 5.59 | 1.32 | 1.98 | 3.28 | 1.20 | 2.05 |
| S7 UPDATE와 INSERT 반복 | 1.82 | 1.31 | 1.23 | 1.59 | 0.98 | 1.24 |
| S8b 큰 값 UPDATE 반복 | 1.63 | 1.00 | 1.25 | 1.17 | 0.96 | 1.41 |
| S8s 작은 열 UPDATE 반복 | 1.59 | 0.85 | 0.92 | 1.62 | 0.74 | 1.11 |
| S9 DELETE | 0.52 | 0.68 | 1.59 | 0.23 | 0.44 | 2.13 |

두 표에서 모든 설계가 일관되게 유리한 경우는 S1이다. S5에서는 Sidecar가 유리하고 OOS가 불리하다. Inner Table의 S5는 이득이 있지만 S8s까지 일관되지는 않는다. S6는 모든 설계에서 불리하다. Sidecar도 S6와 대부분의 S7에서 비용이 늘므로 모든 쓰기 workload에 유리하다고 할 수 없다. [집계 표][tables]

64 KB warm S2의 OOS 0.68배와 Sidecar 0.76배는 중앙값 기준 관찰이다. 이 조건의 develop 명령어 수 자체에 반복 변동이 있어 우위의 확정 근거로 사용하지 않는다. 자세한 원시 값은 특이사항에서 제시한다. [원시 결과][raw]

### 5.3 페이지 접근과 OS 읽기

64 KB io 조건의 OS 읽기 바이트는 다음과 같다. 단위는 MiB이며 소수 부분을 반올림했다. [집계 표][tables]

| 시나리오 | develop | OOS | Sidecar | Inner Table |
| --- | ---: | ---: | ---: | ---: |
| S1 작은 열 scan | 1,260 | 5 | 6 | 5 |
| S2 큰 값 scan | 1,260 | 1,261 | 1,261 | 2,013 |
| S3n 작은 열 PK 조회 | 1,004 | 4 | 11 | 1,828 |
| S3w 큰 값 PK 조회 | 1,030 | 400 | 1,033 | 1,817 |

S1은 세 설계 모두 큰 값 읽기를 피한다. 그러나 S3n에서는 OOS와 Sidecar만 같은 이득을 보이며 Inner Table은 develop보다 많이 읽는다. S3w에서 OOS의 읽기량이 작다는 관찰도 있지만, 이 차이의 원인은 이번 자료만으로 확정하지 않는다.

S2의 page fetch 비율은 8 KB에서 OOS 3.00배, Sidecar 1.00배, Inner Table 5.00배이다. 64 KB에서는 각각 1.17배, 1.33배, 4.33배이다. Inner Table의 8 KB S2는 OS 읽기 바이트가 develop과 비슷해도 page fetch와 명령어 수는 증가한다. 캐시 hit를 포함한 페이지 접근과 값 복원 비용을 물리 I/O만으로 설명할 수 없다는 증거이다. [집계 표][tables]

### 5.4 변경 작업의 쓰기와 log page 쓰기

다음은 io 조건에서 SQL 실행과 drain을 합한 OS 쓰기 바이트이다. 단위는 MiB이다. [집계 표][tables]

| 값 크기와 시나리오 | develop | OOS | Sidecar | Inner Table |
| --- | ---: | ---: | ---: | ---: |
| 8 KB S5 | 5,605 | 5,923 | 40 | 45 |
| 64 KB S5 | 2,476 | 4,413 | 7 | 7 |
| 8 KB S6 | 969 | 1,255 | 2,521 | 2,759 |
| 64 KB S6 | 303 | 798 | 931 | 3,113 |
| 64 KB S9 | 757 | 642 | 650 | 3,352 |

Sidecar와 Inner Table은 S5의 쓰기를 줄이지만 S6에서는 쓰기가 증가한다. Inner Table의 64 KB S6는 OS 쓰기가 develop의 10.28배이다. 이 비율은 데이터 파일만의 쓰기 증폭률로 해석하지 않는다. [집계 표][tables]

log page 쓰기 횟수도 같은 방향의 일부 근거를 제공한다. 아래 수치는 원시 JSON의 본 구간과 `drain_Num_log_page_iowrites`를 합산한 값이다. [원시 결과][raw], [집계 코드][analysis]

| io 조건 | develop | OOS | Sidecar | Inner Table |
| --- | ---: | ---: | ---: | ---: |
| 8 KB S5 | 3,584 | 13,748 | 1,297 | 1,364 |
| 64 KB S5 | 2,344 | 9,880 | 212 | 214 |
| 64 KB S6 | 462 | 1,984 | 1,478 | 6,717 |
| 64 KB S9 | 1,206 | 1,362 | 1,108 | 7,815 |

명령어 감소와 모든 쓰기 지표의 감소가 항상 함께 나타나지는 않는다. 예를 들어 OOS의 64 KB S9는 명령어 비율이 0.69이지만 log page 쓰기 횟수는 develop보다 많다. 작업별 비용을 단일 비율로 합쳐 판단하기 어려운 이유이다.

### 5.5 기능 미사용 조건과 파일 크기

100 B와 2 KB에서 S4를 제외한 page fetch 비율은 0.98~1.03이다. Inner Table S2를 제외한 반복 읽기의 명령어 비율은 원시 결과 재집계 기준 0.93~1.03이다. Inner Table S2는 inline 값에서도 1.08~1.21배이다. 변경 작업의 명령어 비율은 0.89~1.16이며, 단일 표본이다. 별도로 Sidecar의 100 B 적재는 1.16배, 2 KB 적재는 1.08배이다. 따라서 미사용 비용이 항상 작다는 판정을 내릴 수 없다. [집계 표][tables], [원시 결과][raw]

| 값 크기 | 시점 | develop | OOS | Sidecar | Inner Table |
| --- | --- | ---: | ---: | ---: | ---: |
| 8 KB | 적재 직후 | 2,401 | 2,305 | 2,401 | 2,433 |
| 8 KB | 전체 작업 후 | 2,593 | 4,705 | 3,041 | 3,233 |
| 64 KB | 적재 직후 | 1,633 | 1,633 | 1,633 | 2,529 |
| 64 KB | 전체 작업 후 | 2,049 | 3,201 | 2,017 | 3,649 |

단위는 MiB이다. 이 표는 `db_bytes`이며, driver가 데이터와 로그 디렉터리 아래 파일 길이를 합산한 값이다. 볼륨의 큰 단위 확장과 로그를 포함하므로 실제 payload 공간이나 누수 바이트를 뜻하지 않는다. 전체 작업 후 OOS와 Inner Table의 파일 합계가 커졌다는 사실은 후속 공간 검증의 근거이며, 그 전부를 특정 결함의 누수로 귀속할 수는 없다. [측정 driver][driver], [원시 결과][raw]

## 6. 결과 해석

### 6.1 작은 열 scan의 이득과 단건 조회의 한계

H1은 관찰 범위에서 지지된다. 큰 값이 사라진 작은 heap에는 페이지당 더 많은 행이 들어가므로 S1의 page fetch와 OS 읽기가 줄어든다. warm에서도 명령어 수가 줄어, 이득이 물리 I/O 절감에만 한정되지 않는다. 이 연결은 저장 구조와 지표가 함께 뒷받침하는 해석이다. [실행 보고서][run], [집계 표][tables]

H3은 OOS와 Sidecar에서는 부분적으로 지지된다. 64 KB io S3n에서 큰 값 읽기를 피하는 이득이 명확하지만, 8 KB에서는 PK 탐색과 SQL 실행 자체의 비용이 남아 명령어 차이가 작다. 이 비용 구성의 설명은 별도 profile하지 않은 추론이다.

Inner Table에서는 H3의 기대가 반증된다. 현재 코드의 heap scan open은 읽는 속성에 VARCHAR 또는 VARBIT이 없으면 `inner_table_skip_expand=true`를 설정한다. 반면 index scan open에는 같은 설정이 없다. 기본값은 false이므로 S3n처럼 heap fetch를 수행하는 PK 조회도 참조를 확장한다. `inner_table_expand`는 이 flag를 검사한 뒤 행 안의 참조를 순회한다. 이는 결과에서 추정만 한 원인이 아니라 해당 커밋의 소스로 확인한 동작이다. index-only 경로까지 모두 같은 동작을 한다는 뜻은 아니다. [heap scan 설정][inner-scan], [index scan 시작][inner-index], [초기값][inner-cache], [참조 확장][inner-expand]

### 6.2 큰 값을 읽을 때 Inner Table이 비싼 이유

H2의 Inner Table 예상은 지지된다. `read_chunks`는 chunk마다 `btree_find_unique_visible`로 키를 찾고, `heap_get_visible_version`의 COPY 모드로 행을 읽으며, 값 바이트를 결합한다. 이어서 `inner_table_expand`가 행을 다시 구성하고 완성된 레코드를 복사한다. 이 작업은 companion heap을 순서대로 한 번 읽는 scan과 다르다. [chunk 읽기][inner-chunks], [레코드 복원][inner-rebuild]

chunk별 B-tree 탐색, heap fetch, 값 결합과 전체 레코드 복사가 S2 비용을 설명한다는 해석은 추론이다. 각 단계가 증가분에서 차지하는 비중은 profile하지 않았다. 또한 소스는 참조 확장을 생략할 수 없는 Inner Table 클래스에 heap batch scan을 허용하지 않는다. 이 경로 차이의 기여도 역시 이번 측정에서 분리하지 않았다. [batch scan 제한][inner-batch]

OOS와 Sidecar에 대해서 H2는 조건부로만 지지된다. 8 KB S2는 두 설계 모두 develop보다 많은 명령어를 사용하지만, 64 KB에서는 기준도 overflow를 읽으므로 손익이 달라진다. Sidecar의 보호된 query scan은 필요한 속성만 나중에 읽지만, S2는 모든 행의 `big`을 조건에서 해석하므로 값 판독 생략의 이득이 사라진다. store 접근과 복사가 남는다는 것은 코드로 확인되며, 그 비용의 정량적 비중은 추론이다. [Sidecar 지연 읽기][sidecar-lazy], [Sidecar store 읽기][sidecar-read]

### 6.3 작은 열 UPDATE에서 세 설계가 갈리는 이유

H5의 핵심 차이는 미할당 큰 값을 새로 저장하는지, 읽기까지 생략하는지이다.

OOS는 새 disk image를 만들기 전에 미초기화 속성을 읽는다. 이후 큰 값을 직렬화해 `heap_oos_insert_serialized_values`와 `oos_insert_many`로 전달한다. 따라서 SQL이 `k`만 할당해도 큰 값이 다시 읽히고 저장된다. 이 소스 경로는 CBRD-27230의 현행 동작과 일치하고, 별도 S5 probe와 profile이 실제 실행을 뒷받침한다. H5의 OOS 비용 증가는 지지된다. [미할당 속성 판독][oos-uninit], [재직렬화][oos-serialize], [재적재 호출][oos-insert], [OOS batch insert][oos-many], [CBRD-27230 설명][dedup]

Sidecar는 `HEAP_UNINIT_ATTRVALUE`를 처리할 때 기존 참조를 유지하면 값 판독을 건너뛴다. `sidecar_keep_ref`가 참조를 `HEAP_KEPT_REF_ATTRVALUE`로 보존하고 새 image에 복사한다. S5에서 store 읽기와 재적재를 피하는 경로가 확인되므로 이득의 설명이 성립한다. 이는 미할당 열의 SQL UPDATE 경로에 대한 설명이다. 다른 쓰기 경로까지 항상 무판독 재사용이라고 일반화하지 않는다. [Sidecar UPDATE 분기][sidecar-uninit], [참조 유지][sidecar-keep]

Inner Table도 미할당 속성의 기존 참조를 재사용한다. 따라서 OOS와 달리 큰 값을 매번 새 chunk로 쓰는 구조라고 설명하면 틀린다. 다만 기존 행을 fetch할 때 값 확장이 일어나는 경로가 남아 있어, 쓰기 절감에 비해 읽기와 복원 비용이 클 수 있다. 참조 재사용은 소스 확인 사항이고, 이 남은 비용이 S5와 S8s의 차이를 얼마나 설명하는지는 추론이다. H5는 Inner Table에서 부분 지지된다. [Inner Table 참조 재사용][inner-keep], [참조 확장][inner-expand]

### 6.4 적재, 값 교체, 반복 변경, DELETE

H4는 S6에서는 지지되지만 S4에서는 부분 지지된다. 세 설계 모두 큰 값 교체 때 명령어 비용이 증가한다. Inner Table은 새 chunk 행 및 인덱스 기록과 이전 chunk의 은퇴를 수행하므로 page fetch와 log page 쓰기도 커진다는 설명이 소스와 부합한다. 다만 명령어 증가분을 그 작업들에 정량 배분한 결과는 아니다. 초기 적재는 이전 값 회수가 없고 공통 SQL 처리도 포함하므로 OOS와 Sidecar의 비용 증가가 일관되지 않는다. [집계 표][tables], [Inner Table 쓰기 코드][inner-threshold], [Inner Table 이전 값 은퇴][inner-retire]

H6은 혼합 결과이다. OOS와 Inner Table은 S7 및 S8b에서 대체로 불리하지만, Sidecar는 S8b에서 develop과 비슷하거나 명령어가 적다. 짧은 트랜잭션에서는 값 교체뿐 아니라 PK 접근, 반복 SQL, commit, 캐시 상태의 영향도 들어간다. 각 비용의 profile 없이 한 원인으로 단정하지 않는다.

특히 S8b는 같은 값을 반복 할당한다. Sidecar에는 새 값과 기존 참조의 길이가 같으면 store 값을 읽어 비교하고, 바이트가 같으면 참조를 유지하는 경로가 있다. 따라서 S8b의 이득에 동일 값 재사용이 기여했을 가능성이 있다는 해석은 추론이다. 해당 분기의 실행 횟수는 이번 자료에 없다. 이 결과를 매회 다른 값으로 바꾸는 UPDATE의 이득으로 일반화하지 않는다. [측정 driver][driver], [Sidecar 동일 값 비교와 재사용][sidecar-compare]

H7의 Inner Table 예상은 특히 64 KB S9에서 지지된다. 여러 chunk와 인덱스의 수명을 처리하는 구조가 명령어 3.09배, OS 쓰기 4.43배와 부합한다. OOS와 Sidecar는 이번 S9에서 명령어가 줄지만, 회수가 정확히 끝났다는 증거와는 구분한다. drain을 포함한 비용 절감이 모든 chain의 회수 완료를 증명하지는 않는다. [집계 표][tables], [원시 결과][raw]

H8은 작은 값의 페이지 접근에 대해서는 대체로 지지되지만, 미사용 비용 수락 여부에 대해서는 미확정이다. Inner Table의 inline S2와 Sidecar의 적재 예외가 있으며 기반 커밋도 다르다. 작은 값에서 develop에 가깝다는 관찰과 수락 기준을 통과했다는 판정은 구분해야 한다.

## 7. 특이사항

### 7.1 OOS S5의 미변경 값 재적재 확인

본 실행의 큰 S5 비용을 확인하기 위해 별도로 수행한 probe는 8 KB 값 30,000행, io 조건에서 `UPDATE t SET k = k + 1`을 실행했다. 아래는 당시 관측이며 이번 보고서 작성 중 다시 실행한 결과가 아니다. [실행 보고서][run], [실행 후 확인 사항][brief], [probe 코드][probe]

| 관측 시점 | Oos_num_user_pages | Oos_num_recs | Oos_recs_sumlen |
| --- | ---: | ---: | ---: |
| UPDATE 전 | 30,001 | 30,000 | 246,720,000 |
| UPDATE 및 vacuum 후 | 60,001 | 30,000 | 246,720,000 |

큰 값은 바꾸지 않았지만 OOS 페이지 수가 늘었다. 레코드 수와 길이 합계가 유지된 것은 이전 레코드가 사라지고 같은 값이 새로 저장된 관측과 부합한다. 해당 probe에서 페이지가 늘었다는 사실을 모든 UPDATE에서 파일이 같은 비율로 증가한다는 법칙으로 일반화하지 않는다.

같은 UPDATE의 `perf record`에서 확인한 누적 children 비율은 다음과 같다. [실행 후 확인 사항][brief]

| 경로 또는 함수 | 누적 비율 | 관찰 의미 |
| --- | ---: | --- |
| `heap_oos_insert_serialized_values`에서 `oos_insert_many` | 19% | 미변경 값의 새 적재가 실행된다. |
| `oos_find_best_page` | 16% | 적재할 페이지 탐색 비용이 있다. |
| `oos_alloc_page_with_reclaim` | 15% | 페이지 할당과 회수 검사 비용이 있다. |
| `heap_attrvalue_read_oos`에서 `oos_read` | 9% | 기존 큰 값을 다시 읽는다. |
| pgbuf victim 탐색 계열 | 약 7% | 작은 버퍼에서 페이지 교체 비용이 있다. |

누적 비율은 호출 관계상 겹칠 수 있어 합산하지 않는다. 작은 probe의 비율로 본 실행의 S5 증가분 전체를 설명하거나 수정 후 개선율을 예측할 수 없다. 이 확인으로 CBRD-27230과의 연결은 강해졌지만, 해당 이슈는 제공된 자료 기준 Open이며 수정 후의 성능은 측정하지 않았다.

### 7.2 Inner Table PK 조회의 설명 갱신

기존 실행 보고서는 S3n의 큰 값 접근을 코드 미확인 추정으로 남겼다. 실행 후 확인에서 heap scan의 projection 생략 설정이 index scan에는 없다는 점을 확인했다. 본 보고서는 이를 확인된 코드 동작으로 갱신한다. 큰 값 scan의 비용 원인에 대한 함수별 기여도는 여전히 추론으로 남긴다. [실행 보고서][run], [실행 후 확인 사항][brief], [heap scan 설정][inner-scan], [index scan 시작][inner-index]

### 7.3 원시 자료 재검토에서 드러난 변동과 표기 차이

기존 보고서는 명령어 수의 반복 차이가 경과 시간보다 작다는 점을 강조한다. 그러나 64 KB warm S2의 develop 명령어 수는 아래처럼 변한다. 이 조건에서 명령어 수까지 안정적이라고 일반화하면 안 된다. page fetch는 세 반복 모두 96,096회이고 data page I/O read는 모두 0회이다. 변동의 원인은 이번 자료로 확인하지 못한다. [원시 결과][raw]

| 반복 | develop 서버 명령어 수 |
| --- | ---: |
| 0 | 219,470,782 |
| 1 | 506,681,429 |
| 2 | 365,668,174 |

기존 집계의 최대 반복 spread인 4.62는 `(최댓값 - 최솟값) / 중앙값`이다. 최댓값을 최솟값으로 나눈 배율과 다르다. 8 KB io S3n의 develop wall time은 약 2.920초, 3.070초, 17.095초로 기록됐다. 본 보고서는 이 변동을 특정 배수의 가속 주장에 사용하지 않는다. [집계 표][tables], [원시 결과][raw]

기능 미사용 읽기 비율도 원시 자료에 맞춰 범위를 보완했다. Inner Table S2를 제외한 상한은 2 KB io S3w의 약 1.029로, 반올림하면 1.03이다. 기존 보고서의 1.02 상한을 그대로 사용하지 않았다. Inner Table S2의 전체 명령어 비율 범위 역시 조건별 표의 2.25~11.25를 사용한다. [집계 표][tables], [원시 결과][raw]

### 7.4 시험 실행의 미재현 이상값과 측정 환경 보정

본 실행 전 시험 실행의 8 KB, 12,000행 warm S6에서 OOS page fetch가 약 5,000만 회였으나, 전체 실행에서는 약 80만 회로 재현되지 않았다. 원인은 조사하지 않았으며 본 실행 결과와 섞지 않는다. [실행 보고서][run]

빌드 경고 완화, Java PL 비활성화, statdump watcher 유지는 각각 빌드 실패, PL 서버 시작 실패, 전역 카운터 수집 조건에 대응한 조치이다. 이 조치와 실제 반복 수를 실험 설계에 명시했다. 계획서의 모든 경우 3~5회 반복이라는 목표를 첫 실행이 충족했다고 쓰지 않는다. [측정 driver][driver], [비교 실험 이슈][benchmark-issue], [실행 후 확인 사항][brief]

## 8. 눈여겨볼 사항

### 8.1 작은 열 scan 성능만으로 설계를 고를 수 없다

S1의 이득은 세 설계에서 공통이다. 설계 선택을 가르는 항목은 큰 값이 필요할 때의 읽기, 작은 열 UPDATE의 참조 재사용, 큰 값 교체와 회수 비용이다. 실제 서비스에서 각 작업이 차지하는 비중 없이 시나리오별 비율을 평균 내 전체 우승자를 정하는 것은 적절하지 않다.

| 후보 | 이번 실행이 뒷받침하는 강점 | 결정 전에 해소할 항목 |
| --- | --- | --- |
| OOS | 작은 열 scan과 일부 DELETE에서 명령어와 읽기가 감소한다. | 미변경 값 재적재 수정 전후를 구분해야 한다. 회수 정확성과 동시 INSERT 경합도 별도 검증 대상이다. |
| Sidecar | 작은 열 scan 및 작은 열 UPDATE에서 이득이 있다. 이번 큰 값 workload에서 명령어 손실이 비교적 작다. | 큰 값 교체의 쓰기 비용, HA 구현 후 비용, 장기 churn과 공간 정책, 회귀 검증을 확인해야 한다. |
| Inner Table | 작은 열 heap scan의 이득과 일반 MVCC 행을 통한 수명 관리 가능성을 보인다. | index 조회의 projection, chunk 읽기와 복사, 큰 값 변경 및 삭제 비용, 미완성 운영 기능을 검증해야 한다. |

이 표의 우선순위는 관찰 결과에 대한 판단이며 제품 채택 판정은 아니다. 성능 문제와 정확성·기능 완성도 문제는 각각의 근거로 평가해야 한다.

### 8.2 OOS의 현행 비용과 보완 후 비용을 구분해야 한다

S5의 큰 손실은 OOS에서 미변경 값을 다시 적재하는 현행 구현의 결과이다. CBRD-27230을 해결하면 이 비용의 일부가 줄 것이라는 예상은 타당하지만 감소 폭은 미측정이다. 이 이슈는 단순히 읽기 한 번을 빼는 최적화가 아니다. 참조 재사용, 버린 chain의 commit 후 회수 알림, rollback과 snapshot 안전성, 복제 측 참조 보정이 함께 맞아야 한다. [CBRD-27230 설명][dedup]

### 8.3 HA 미지원은 이번 차이의 설명이 되지 않는다

네 DB는 모두 HA를 끄고 측정했다. CUBRID의 복제 로그는 HA가 켜졌을 때 기록되며, OOS S5 profile의 복제 관련 관측은 `log_does_allow_replication` 0.05%이다. 따라서 Sidecar와 Inner Table이 HA를 구현하지 않아 복제 비용을 생략했기 때문에 이번 결과가 유리하다는 설명은 성립하지 않는다. [실행 후 확인 사항][brief]

반대로 HA-off 결과로 HA-on 비용이 동등하다고 할 수도 없다. 현재 Sidecar는 HA-enabled DB에서 값을 밖으로 옮기지 않는다. 같은 외부 저장 workload의 HA-on 비교를 하려면 먼저 기능을 구현해야 한다. Inner Table의 HA-on 쓰기 비용도 알려져 있지 않다. [Sidecar admission 코드][sidecar-ha], [실행 후 확인 사항][brief]

## 9. 위협 요인 (Threats to validity)

| 요인 | 이번 실행에 미치는 영향과 해석 제한 |
| --- | --- |
| 공용 서버 부하 | 기존 보고서의 실행 초반 load average는 17~30이다. wall time 변동이 커 응답 시간과 처리량 우위를 확정하기 어렵다. 명령어 수도 일부 조건에서는 변한다. |
| 변경 작업 단일 표본 | S4 적재와 변경 작업은 조건별 1회이다. 분산이나 신뢰구간을 추정할 수 없다. 특히 1에 가까운 차이는 회귀나 개선으로 판정하지 않는다. |
| 서로 다른 develop 기반 | OOS는 기준과 같지만 Sidecar와 Inner Table은 다르다. 미사용 비용이나 작은 차이를 해당 기능만의 비용으로 분리할 수 없다. Inner Table 설계 초안의 기반 설명보다 이번 실행에 명시된 `81fa5696cd`를 적용했다. |
| 변경 순서와 물리 상태 | warm 변경 뒤 io 변경을 수행한다. 앞선 변경의 파일 확장, 버전과 값 상태를 이어받는다. 같은 절차를 썼어도 설계마다 남은 물리 상태가 같다는 뜻은 아니다. |
| 단순한 값과 스키마 | 압축되지 않는 반복 바이트 값 하나와 단순한 테이블이다. S8b는 동일 값을 반복 할당한다. 압축 VARCHAR, 여러 큰 열, 매회 다른 값의 교체, 값 분포, 임계값 부근의 이동 정책을 대표하지 않는다. |
| 단일 접속 | 동시 쓰기의 헤더 경합, latch 경합, 확장성은 측정하지 않았다. |
| 측정 구간 차이 | 명령어 수, OS 쓰기, log 쓰기는 drain을 포함하지만 기존 fetch와 OS 읽기 표 및 wall time은 같은 합산 범위가 아니다. 서로 다른 범위의 수치를 같은 작업량처럼 비교하면 안 된다. |
| idle의 의미 | 실제 비교식은 구간의 CPU 누적 초 증가량이 0.0101 이하인지 확인하며, 이를 관측 간격으로 나누지 않는다. 기존 보고서의 CPU 1% 이하를 엄밀하게 검사하는 코드는 아니다. 전체 회수 완료, checkpoint 완료, 긴 snapshot의 영향도 검증하지 않는다. |
| OS 쓰기와 파일 크기 | OS 쓰기는 로그 등을 포함하며 flush 시점의 영향을 받는다. `db_bytes`는 데이터와 로그 경로의 파일 길이 합계여서 순수 저장 효율이나 누수량이 아니다. |
| HA-off 및 미완성 기능 | HA-on 비용은 미확정이다. Sidecar는 HA 및 supplemental log 사용 시 외부화를 제한한다. Inner Table은 HA, CDC, flashback, TDE 등 운영 기능이 미완성이다. |
| 기능 완성도와 정확성 검증 | 성능 실행이 recovery, MVCC, vacuum, 회귀 전체의 수락을 대신하지 않는다. 두 POC가 기존 heap 경로의 결함을 함께 물려받을 수 있다. |
| 결과 동등성 검증의 범위 | 원시 JSON에는 592개 측정 레코드와 32개 저장 확인 레코드가 있고 실패 레코드는 없다. 그러나 driver는 SQL 오류와 timeout을 검사할 뿐 빌드 간 결과값의 동등성을 별도 판정하지 않는다. 오류가 기록되지 않았다는 사실을 정확성 보장으로 바꾸지 않는다. |

위 제한의 근거는 [실행 보고서][run], [측정 driver][driver], [집계 코드][analysis], [원시 결과][raw], [Sidecar 설계 이슈][sidecar-issue], [Inner Table 설계 이슈][inner-issue], [실행 후 확인 사항][brief]에 있다. 초기 이슈의 0 크기 및 VARCHAR 계획, 사용자 공간 전용 `instructions:u` 지표, 모든 경우 3~5회 반복이라는 기술과 달리 실제 driver는 100 B 대조군, BIT VARYING, `instructions` 이벤트, 읽기 3회와 변경 1회를 사용한다. 본문은 실제 실행을 기준으로 해석한다.

## 10. 의의와 결론

첫 실행은 같은 driver에서 작은 열 scan의 공통 이득과 설계별 불리한 작업을 함께 드러냈다. OOS의 현행 작은 열 UPDATE는 큰 값을 그대로 두는 작업에서도 재적재 비용을 낸다. Sidecar는 이 경로에서 값 읽기와 재적재를 피한다. Inner Table은 작은 열 heap scan의 이득을 보이지만 index 경로의 확장 생략과 큰 값 읽기 비용에 개선 여지가 있다. 이 구분은 측정과 소스 확인이 함께 뒷받침한다.

팀장에게 권고하는 다음 검증 순서는 아래와 같다. 이는 성능과 기능 검증의 우선순위 제안이며 병합이나 채택 승인 요청이 아니다.

1. 반복 수와 결과 동등성 검증을 보강해 주요 차이가 유지되는지 확인한다. 진행 중인 보충 실행은 3~5회 반복, 빌드 간 결과 확인, 두 번째 기준인 develop `e64a04a79`, 4 KB 값, 8-client 동시 접속을 포함한다. 아직 결과를 이 보고서의 근거로 사용하지 않는다. [실행 후 확인 사항][brief]
2. OOS의 CBRD-27230 반영 전후에 S5, S7, S8s를 다시 비교한다. 재사용된 값이 rollback, snapshot, vacuum, restart 및 HA에서 안전한지도 함께 검증한다. 감소 폭을 현재 profile의 비율로 대신하지 않는다. [CBRD-27230 설명][dedup]
3. Inner Table의 작은 열 index 조회에서 참조 확장을 생략할 수 있는지 검증하고 S3n을 다시 측정한다. S2는 chunk별 탐색과 heap fetch, 복사 및 batch 경로를 profile해 원인을 분리한다. [index scan 시작][inner-index], [chunk 읽기][inner-chunks], [batch scan 제한][inner-batch]
4. Sidecar를 우선 후속 검증 후보로 두되, 큰 값 교체의 쓰기 비용과 장기 공간 사용, HA 구현 후의 같은 workload, 남은 정확성 및 회귀 항목을 확인한다. 매회 다른 값을 할당하는 반복 UPDATE도 비교한다. 이번 수치로 미완성 기능의 비용을 추정하지 않는다. [집계 표][tables], [Sidecar 설계 이슈][sidecar-issue], [측정 driver][driver]
5. 최종 미사용 비용과 작은 차이를 판정할 때에는 공통 develop 기반과 더 통제된 부하를 사용한다. 저장 정책의 임계값 부근과 실제 서비스의 작업 비중도 추가한다. [실행 보고서][run]

이번 실행이 확립한 것은 특정 커밋과 HA-off 조건에서의 workload별 비용 차이이다. 확립하지 못한 것은 제품 수준의 응답 시간 우위, 동시 접속 확장성, 모든 운영 기능을 포함한 최종 비용, 정확성 수락, 보완 후 OOS와의 최종 순위이다. 현재 근거는 설계 선택을 끝내기보다 다음 검증에서 무엇을 확인해야 하는지를 좁히는 데 사용해야 한다.

## 11. 참고

아래 문서와 코드는 본 보고서 작성 중 읽은 자료이다. 소스 링크는 측정한 커밋에 고정되어 있다.

- [첫 실행 보고서인 benchmark-report.md][run]. 실험 방법, 절대값, 관측과 기존 해석을 제공한다.
- [전체 집계인 results-tables.md][tables]. 조건별 비율, 절대값, 파일 크기 및 반복 spread를 제공한다.
- 원시 측정 `results.jsonl`은 로컬에만 있으며 git에 넣지 않았다. 본문의 비율 재검산, log page 합산, 반복 변동과 레코드 수 확인에 사용했고, 집계는 [results-tables.md][tables]에 있다.
- [측정 driver인 oosbench.py][driver], [집계 코드인 analyze.py][analysis], [OOS S5 probe인 oos_s5_probe.py][probe]. 실제 SQL, 순서, 반복 수와 지표 범위를 확인한다.
- [CBRD-28077 로컬 이슈 설명][benchmark-issue]. 원래 연구 질문과 측정 계획을 제공한다.
- [CBRD-28053 Sidecar 로컬 설계 이슈][sidecar-issue], [CBRD-28054 Inner Table 로컬 설계 이슈][inner-issue]. 대안 설계의 동기, 구조와 알려진 한계를 제공한다.
- [CBRD-27230 로컬 설명][dedup]. 미할당 OOS 값 재사용과 회수·복제 정합성의 요구를 제공한다.
- [OOS 미할당 값 처리][oos-uninit], [OOS 재직렬화][oos-serialize], [OOS 적재 호출][oos-insert], [OOS batch insert][oos-many]. 측정 커밋 `c02f897268`의 경로를 확인한다.
- [Sidecar UPDATE 분기][sidecar-uninit], [참조 유지][sidecar-keep], [동일 값 비교와 재사용][sidecar-compare], [지연 읽기][sidecar-lazy], [store 읽기][sidecar-read], [HA 외부화 제한][sidecar-ha]. 측정 커밋 `7c5028d5bd`의 경로를 확인한다.
- [Inner Table heap scan][inner-scan], [index scan][inner-index], [cache 초기값][inner-cache], [chunk 읽기][inner-chunks], [참조 확장][inner-expand], [행 복원][inner-rebuild], [참조 재사용][inner-keep], [이전 값 은퇴][inner-retire], [이동 조건][inner-threshold], [batch scan 제한][inner-batch]. 측정 커밋 `fbb4f25057`의 경로를 확인한다.

[brief]: https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28077/run3-report.md
[run]: https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28077/benchmark-report.md
[tables]: https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28077/results-tables.md
[raw]: https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28077/results-tables.md
[driver]: https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28077/tools/oosbench.py
[analysis]: https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28077/tools/analyze.py
[probe]: https://github.com/vimkim/my-cubrid-docs/blob/main/CBRD-28077/tools/oos_s5_probe.py
[benchmark-issue]: https://jira.cubrid.org/browse/CBRD-28077
[sidecar-issue]: https://jira.cubrid.org/browse/CBRD-28053
[inner-issue]: https://jira.cubrid.org/browse/CBRD-28054
[dedup]: https://jira.cubrid.org/browse/CBRD-27230
[oos-uninit]: https://github.com/CUBRID/cubrid/blob/c02f897268b03526c1b4dd0359220f924d58b810/src/storage/heap_file.c#L13760
[oos-serialize]: https://github.com/CUBRID/cubrid/blob/c02f897268b03526c1b4dd0359220f924d58b810/src/storage/heap_file.c#L14304
[oos-insert]: https://github.com/CUBRID/cubrid/blob/c02f897268b03526c1b4dd0359220f924d58b810/src/storage/heap_file.c#L14390
[oos-many]: https://github.com/CUBRID/cubrid/blob/c02f897268b03526c1b4dd0359220f924d58b810/src/storage/heap_oos.cpp#L889
[sidecar-uninit]: https://github.com/vimkim/cubrid/blob/7c5028d5bd811255cdaa40b6901a68d03c09550c/src/storage/heap_file.c#L13489
[sidecar-keep]: https://github.com/vimkim/cubrid/blob/7c5028d5bd811255cdaa40b6901a68d03c09550c/src/storage/sidecar.cpp#L1859
[sidecar-compare]: https://github.com/vimkim/cubrid/blob/7c5028d5bd811255cdaa40b6901a68d03c09550c/src/storage/sidecar.cpp#L1349
[sidecar-lazy]: https://github.com/vimkim/cubrid/blob/7c5028d5bd811255cdaa40b6901a68d03c09550c/src/storage/sidecar.cpp#L2383
[sidecar-read]: https://github.com/vimkim/cubrid/blob/7c5028d5bd811255cdaa40b6901a68d03c09550c/src/storage/sidecar.cpp#L2259
[sidecar-ha]: https://github.com/vimkim/cubrid/blob/7c5028d5bd811255cdaa40b6901a68d03c09550c/src/base/sidecar_format.c#L553
[inner-scan]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/query/scan_manager.c#L4073
[inner-index]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/query/scan_manager.c#L4172
[inner-cache]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/heap_file.c#L6540
[inner-threshold]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L690
[inner-keep]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L728
[inner-retire]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L894
[inner-chunks]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L519
[inner-expand]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L940
[inner-rebuild]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/storage/inner_table.cpp#L1003
[inner-batch]: https://github.com/vimkim/cubrid/blob/fbb4f250576a1d39a5202ab2b5ddb9965560d6f1/src/query/scan_manager.c#L7512
