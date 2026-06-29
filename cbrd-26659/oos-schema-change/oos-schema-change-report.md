# OOS 스키마 변경 영향 검토 결과

## 결론

스키마 변경 때문에 OOS 컬럼 값이 깨지거나 잘못 읽힐 수 있다는 우려는 이번 검증 범위에서는 성립하지 않습니다.

OOS 대상 레코드를 만든 뒤 컬럼 위치 변경, 컬럼 추가/삭제, 레코드 rewrite, default value 기반 rewrite, OOS 컬럼 drop, inline 컬럼의 OOS 전환, 컬럼 타입/속성 변경을 검증했습니다. 같은 SQL 을 `csql -S` 와 server/client 모드에서 모두 실행했고, 모든 값 비교 결과가 정상입니다.

`oos_data_a` 와 `oos_data_b` 는 hot/cold 의미가 아닙니다. 서로 다른 큰 OOS 값을 구분하기 위한 이름입니다.

## 우려 사항별 정리

| 우려 사항 | 검증 시나리오 | 결과 | 왜 틀렸는지 |
|---|---|---|---|
| 컬럼 위치 변경으로 OOS 컬럼을 잘못 읽을 수 있다 | `oos_data_b` 를 `FIRST` 로 이동하고, `oos_data_a` 를 `note` 뒤로 이동 | `oos_a_ok = 1`, `oos_b_ok = 1` | 컬럼 순서가 바뀐 뒤에도 두 OOS 컬럼이 각각 원래 값과 정확히 일치했다. 컬럼 순서 변경이 OOS OID 해석을 깨뜨리지 않았다. |
| 컬럼만 추가하면 기존 OOS 값 해석이 틀어질 수 있다 | nullable `meta_only` 컬럼 추가 | 기존 OOS 값 정상, 새 컬럼은 `NULL` | metadata 성격의 ADD COLUMN 후에도 기존 OOS 값이 그대로 조회됐다. 새 컬럼 추가가 기존 variable column offset 해석을 깨뜨리지 않았다. |
| 컬럼만 삭제하면 기존 OOS 값 해석이 틀어질 수 있다 | nullable `meta_only` 컬럼 삭제 | 기존 OOS 값 정상 | DROP COLUMN 후에도 남은 OOS 컬럼 값이 원래 값과 일치했다. 삭제된 컬럼 때문에 남은 OOS 컬럼의 위치/값 매핑이 틀어지지 않았다. |
| 컬럼 추가 후 record rewrite 가 발생하면 기존 OOS 값이 깨질 수 있다 | `rewrite_data` 컬럼 추가 후 1200 byte 값 저장, `note` 도 함께 update | 기존 OOS 값 정상, `rewrite_data` 도 정상 | 실제 row 값이 바뀌는 rewrite 후에도 기존 OOS 값과 새 컬럼 값이 모두 정상이다. rewrite 과정에서 OOS OID 가 유실되거나 다른 값으로 연결되지 않았다. |
| 값이 있던 컬럼을 삭제하면 남은 OOS 값이 깨질 수 있다 | 값이 들어간 `rewrite_data` 컬럼 삭제 | 기존 OOS 값 정상 | 데이터가 있던 컬럼을 삭제해도 남은 OOS 컬럼 값이 유지됐다. DROP COLUMN 의 record 재구성이 남은 OOS 값을 손상시키지 않았다. |
| `ALTER TABLE ... DEFAULT` 로 전체 record 가 rewrite 되면 OOS 값이 깨질 수 있다 | `add_column_update_hard_default=yes` 상태에서 `default_col int not null default 77` 추가 | 기존 OOS 값 정상, `default_col = 77` | hard default 가 기존 row 에 실제로 채워지는 rewrite 후에도 OOS 값이 유지됐다. default value rewrite 가 OOS 컬럼 resolve 를 깨뜨리지 않았다. |
| OOS 를 포함한 컬럼이 사라질 때 남은 record/OOS 값이 깨질 수 있다 | OOS 대상 컬럼인 `oos_data_b` 를 DROP | 남은 `oos_data_a` 정상, row 정상, catalog 에서 `oos_data_b` 제거 확인 | OOS 컬럼 자체를 삭제해도 남은 OOS 컬럼과 일반 컬럼 값이 정상이다. 삭제 대상 OOS 컬럼 정리가 남은 record 를 손상시키지 않았다. |
| OOS 가 아니었던 컬럼이 OOS 로 전환될 때 값이 깨질 수 있다 | 3000 byte `inline_then_oos` 만 있는 row 를 먼저 만들고, 이후 2500 byte default column 을 hard rewrite 로 추가 | 전환 전/후 모두 `inline_ok = 1`, 추가된 `grow_ok = 1` | 처음 row 는 `DB_PAGESIZE/4` 이하라 OOS 대상이 아니다. default column 추가 후 row 가 커져 기존 컬럼이 OOS demotion 대상이 되는 조건을 만들었지만, 전환 후에도 값이 정확히 유지됐다. |
| OOS 컬럼 자신의 타입/속성 변경이 OOS 값 resolve 에 영향을 줄 수 있다 | `oos_data_a bit varying -> bit varying(50000) not null` | `oos_data_a` 값 정상, `oos_data_b` 값 정상, catalog 에서 `oos_data_a` 가 `VARBIT(50000) NOT NULL` 로 변경됨 | 실제 OOS 컬럼의 precision/nullable 속성을 바꾼 뒤에도 기존 OOS 값이 그대로 복원됐다. OOS 컬럼 자체의 타입/속성 metadata 변경이 OOS OID 해석이나 `oos_read` 결과를 깨뜨리지 않았다. |
| standalone 과 server/client 경로가 다르게 동작할 수 있다 | 동일 SQL 을 `csql -S` 와 CS mode 에서 각각 실행 | 두 모드 모두 성공 | OOS 값 resolve 와 schema rewrite 결과가 실행 모드에 의존하지 않았다. |

## 테스트 파일

- SQL: <https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26659/oos-schema-change/cbrd_26517_oos_schema_change.sql>
- Answer: <https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26659/oos-schema-change/cbrd_26517_oos_schema_change.answer>
- Report: <https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26659/oos-schema-change/oos-schema-change-report.md>

## 검증 방식

초기 OOS 레코드는 다음 값으로 생성했습니다.

| 컬럼 | 값 | 확인 결과 |
|---|---:|---:|
| `oos_data_a` | 5000 byte payload | `DISK_SIZE = 5008`, 값 비교 성공 |
| `oos_data_b` | 4600 byte payload | `DISK_SIZE = 4608`, 값 비교 성공 |

이 크기는 현재 OOS trigger 조건인 `record > DB_PAGESIZE/4` 를 넘기므로 OOS 경로를 탑니다. 테스트는 문자열 압축 영향을 피하기 위해 `BIT VARYING` 을 사용했습니다.

각 단계에서는 다음을 확인했습니다.

- row count 유지
- `DISK_SIZE()` 유지
- 원래 값과의 equality 비교 결과가 `1`
- 일반 컬럼 값 유지
- `db_attribute` 의 컬럼 순서/타입/nullable 정보가 의도대로 변경

## 최종 판단

이번 concern 은 "스키마 변경이나 record rewrite 가 OOS 컬럼의 논리 값 정확성을 깨뜨릴 수 있다"는 관점에서는 유효하지 않습니다.

테스트된 대표 시나리오에서 OOS 대상 레코드는 스키마 변경 전후로 동일한 값을 반환했고, default value rewrite 및 OOS 컬럼 drop 이후에도 남은 값이 정상입니다. 또한 OOS 컬럼 자신의 `BIT VARYING` precision/nullable 속성을 바꾼 뒤에도 값이 정상입니다. 따라서 현재 구현은 일반적인 컬럼 위치 변경, 컬럼 추가/삭제, default 기반 rewrite, inline-to-OOS 전환, OOS 컬럼 타입/속성 변경에 대해 OOS 값 정확성을 유지한다고 판단할 수 있습니다.

참고로 이 SQL 테스트는 논리 값 정확성을 검증합니다. 실제 어떤 컬럼이 물리적으로 OOS file 에 들어갔는지까지 release SQL 출력만으로 증명하려면 한계가 있으므로, 물리 배치 확인이 필요하면 debug `oos.log` 를 함께 보면 됩니다.
