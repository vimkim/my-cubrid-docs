## Purpose

CBRD-26814 는 `feat/oos` 브랜치에서 OOS (큰 컬럼 값을 heap record 밖의 OOS file에 저장하는 방식) 컬럼이 여러 개 있는 row 를 INSERT 할 때 `csql` 이 `or_put_bigint` assertion 으로 종료되는 회귀를 다룬다.

- AS-IS: `heap_attrinfo_transform_variable_to_disk()` 의 OOS 분기는 inline OOS stub 이 들어갈 공간을 `buf->ptr` 기준으로 검사했다. 이 포인터는 아직 variable offset table 쪽을 가리키므로, 실제 쓰기 위치인 variable value area 의 남은 공간을 보장하지 못했다.
- TO-BE: inline OOS stub 이 실제로 기록되는 `*ptr_varvals` 기준으로 공간을 검사한다. 공간이 부족하면 기존처럼 `S_DOESNT_FIT` 를 반환하고, 상위 copyarea retry 경로가 더 큰 buffer 로 다시 시도한다.

이 변경의 목적은 여러 OOS 컬럼을 가진 row 의 write-side serialization 이 buffer 끝을 넘지 않고, 부족한 buffer 를 정상적인 retry 흐름으로 처리하게 하는 것이다.

## Implementation

변경 범위는 `src/storage/heap_file.c` 한 파일이다.

`heap_attrinfo_transform_variable_to_disk()` 는 variable column 하나를 disk record 형식으로 쓰는 함수다. OOS column 은 실제 값 대신 inline OOS stub 을 variable value area 에 기록하고, variable offset table entry 에는 OOS flag 를 표시한다.

기존 코드는 OOS 분기에서 `buf->ptr + OR_OOS_INLINE_SIZE > buf->endptr` 를 검사했다. 하지만 이 시점의 `buf->ptr` 는 offset table entry 를 쓰고 난 위치이며, 곧바로 `buf->ptr = *ptr_varvals` 로 실제 값 영역에 점프한다.

이 PR은 검사식을 `*ptr_varvals + OR_OOS_INLINE_SIZE > buf->endptr` 로 바꾼다. `or_put_oid()` 와 `or_put_bigint()` 가 실제로 쓰는 위치와 같은 기준으로 bounds check 를 수행하므로, 부족한 경우 assertion 이 아니라 `S_DOESNT_FIT` 로 빠진다.

다른 OOS demotion 정책, inline OOS stub 형식, LOB/ELO 저장 방식, read-side OOS expansion 동작은 변경하지 않는다.

## Remarks

### Reviewer Focus

리뷰어는 `src/storage/heap_file.c` 의 `heap_attrinfo_transform_variable_to_disk()` 안 OOS 분기만 보면 된다. 핵심은 "검사한 포인터"와 "실제로 쓰는 포인터"가 같아졌는지이다.

### Verification

- `src/storage/heap_file.c` 의 diff 는 1 line 이며, `git diff --check -- src/storage/heap_file.c` 를 통과했다.
- debug build 가 성공했다.
- CBRD-26814 의 직접 실패 단계인 `bigPageSize.sh` 의 `init.sql` INSERT 가 assertion 없이 끝났고, `select count(*) from t` 결과가 256 인 것을 확인했다.
- 전체 `bigPageSize.sh` 는 더 이상 `or_put_bigint` assertion 이나 `unloaddb` crash 를 보이지 않았다. 다만 최종 결과는 LOB locator path 문자열 차이로 `NOK` 가 남았고, 이는 이 write-side bounds fix 와 별개의 비교/locator 이슈로 보아야 한다.

### Limits

이 PR은 CBRD-26814 의 write-side buffer bounds 문제만 고친다. CBRD-26660 의 LOB/ELO cluster 안에서 남는 locator path 비교, stale database volume, `databases.txt` 의존성 같은 shell-test 문제는 이 PR의 범위가 아니다.
