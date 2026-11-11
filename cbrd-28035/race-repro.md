# CBRD-28035 NEXT VALUE와 fixed가 아닌 scan의 경쟁 상태 재현

## Purpose

- PR [CUBRID/cubrid#8492](https://github.com/CUBRID/cubrid/pull/8492)의 첫 설계는 `NEXT VALUE`가 serial 행을 다시 쓸 때 이전 OOS chain을 바로 지웠습니다.
- 리뷰에서 이 설계가 fixed가 아닌 scan과 경쟁한다는 지적이 나왔습니다. 이 문서는 그 경쟁 상태를 실행으로 재현한 절차와 결과입니다.
- AS-IS(바로 지우는 설계): join이나 subquery reader가 OOS를 읽다가 손상 오류를 받습니다.
- TO-BE(바뀌지 않은 chain 유지): 지우는 일이 없으므로 같은 reader가 오류 없이 읽습니다.

## Implementation

### 원리

- fixed가 아닌 scan은 행을 COPY로 읽고 page latch를 놓습니다. OOS 값은 그 뒤 `fetch_val_list`나 `heap_attrinfo_read_dbvalues`에서 읽습니다.
- `NEXT VALUE`는 serial 행에 instance X lock을 잡지 않고 page latch만 잡습니다. 그래서 reader가 복사한 뒤, OOS를 읽기 전에 행을 다시 쓰고 chain을 지울 수 있습니다.
- 단순 `SELECT`는 fixed scan이라 latch를 쥔 채 OOS를 읽습니다. 그래서 이 경쟁을 만들지 못합니다. 첫 검증에서 단순 `SELECT` reader로는 오류가 없었던 이유입니다.

### 절차

4K page DB에서 NOCACHE serial 하나에 압축되지 않는 1000 byte comment를 넣습니다. writer 4개가 `NEXT VALUE`를 400회씩 부르고, 동시에 reader 4개가 아래 두 질의를 400회씩 실행합니다.

```sql
select /*+ ORDERED */ s.name, if(s.comment = '<comment>', 1, 0)
  from _db_serial s, t2 where t2.a = 1 and s.name = 's1';
select if(comment = '<comment>', 1, 0)
  from _db_serial where name = 's1' and exists (select 1 from t2 where t2.a > 0);
```

`t2`는 행 3개짜리 작은 표입니다. 첫 `NEXT VALUE` 하나를 미리 실행해 comment를 OOS로 옮겨 둡니다.

## Remarks

### 결과 (debug 빌드, 2026-11-11)

| 엔진 | reader 오류 | 값 불일치 | 끝난 뒤 OOS 레코드 |
|---|---|---|---|
| 수정 전 (`feature/oos-merge` `67220b7e23`) | 0 | 0 | 1601 |
| 바로 지우는 설계 (`bee96e666`), 1회차 | 354 | 0 | 1 |
| 바로 지우는 설계 (`bee96e666`), 2회차 | 492 | 0 | 1 |
| 바뀌지 않은 chain 유지 (`7e9a4a513`) | 0 | 0 | 1 |

- 오류 메시지는 모두 `Internal error: out-of-row storage record metadata is inconsistent or corrupted.`였습니다.
- 수정 전 엔진은 오류가 없지만 OOS 레코드가 호출 수만큼 쌓입니다. 이것이 CBRD-28035의 누수입니다.
- 같은 틈은 `_db_ha_apply_info`의 [CBRD-27981](https://jira.cubrid.org/browse/CBRD-27981)에도 있다는 리뷰 의견이 있습니다. 이 문서는 serial 경로만 다룹니다.
