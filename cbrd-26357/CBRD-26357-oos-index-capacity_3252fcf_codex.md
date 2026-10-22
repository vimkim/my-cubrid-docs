# PR 7990: OOS 인덱스 용량 TC 기대값 조정

https://jira.cubrid.org/browse/CBRD-26357

분석일: 2026-10-22, Asia/Seoul. 대상 독자: PR 7990 작성자와 리뷰어.
범위는 `cbrd_24916_check_index_ovfps` 한 건입니다. 엔진 변경 없이 answer 파일 5개의 숫자 6줄을 조정해 현재 OOS head에서 13개 검사가 모두 통과했습니다.

## Purpose

이 TC는 `check_index_ovfps.sh`의 정렬, 소유자 선택, 인덱스 가시성, 임계값 및 페이지 수 출력을 검사합니다.
답지는 페이지 수를 정확한 값으로 비교합니다. OOS는 힙 헤더 크기를 바꾸므로 같은 정수 데이터도 다른 물리적 배치를 가질 수 있습니다.

- AS-IS: develop에서 통과하는 답지가 OOS에서는 검사 8, 9, 10, 12, 13에서 다른 페이지 수를 보고합니다.
- TO-BE: 독립 검사로 확인한 OOS 페이지 수를 답지에 반영하고 기존 13개 검사를 유지합니다.

### 소스와 실행 식별 정보

| 구분 | 커밋 또는 설정 |
| --- | --- |
| 이번 OOS 엔진 | `3252fcffce9762641fb9ae6f4a5d8ae89affc738` |
| 이전 원시 볼륨 분석 엔진 | `1a8c7057623d92205dbc1324ec43e3cc40fc4cd2` |
| 이전 정확한 기준 엔진 | `3ba41d74509d9a6c19ef9adc6cf12d9ebebdbbac` |
| 로컬 develop 비교 엔진 | `60ad770f0f84c54cf9fdf8ee213d543bb36a6906` |
| develop 비교 TC | `ba7ba142f03c5b30471d5a11a6cecb8caa170fd8` |
| 이번 수정 전 TC | `73e2b2f44f5ed79e1fad15bfaf55731959121a3d` |
| 이번 수정 TC | `046d0e2f81e117df0592387983c978acaa411c68` |
| CTP 자산 | `af69c0039ff084fea5ee5ff296cc5301203d4c3f` |
| 빌드 | OptDebug, `-O2`, assertions enabled, GCC 11.5 |

`3252fcf`는 `1a8c705` 뒤에 지연 OOS 쓰기 변경을 추가한 PR head입니다.
힙 레코드 처리 경로가 바뀌었으므로 기존 실행 결과를 그대로 적용하지 않고 새 head를 빌드했습니다.
`HEAP_HDR_STATS` 구조체, `btree.c`, `btree_load.c`, `check_index_ovfps.sh`는 두 head에서 동일합니다.

## Implementation

### 페이지 수가 달라지는 이유

[힙 헤더의 `oos_vfid`](https://github.com/CUBRID/cubrid/blob/3252fcffce9762641fb9ae6f4a5d8ae89affc738/src/storage/heap_file.c#L216)는 OOS 파일을 가리키는 8바이트 필드입니다.
이 필드로 첫 힙 페이지의 행 저장 공간이 줄어듭니다. OID는 행의 물리 주소이므로 행의 OID 배치도 바뀝니다.
OID 순서에 따라 관리하는 B-tree 오버플로 체인은 이 입력에서 다른 페이지 분할 결과를 냅니다.

[이전 독립 실험](non_cdc_followup_1a8c705_codex.md)에서는 기준 엔진의 힙 헤더에 사용하지 않는 8바이트 필드만 추가했습니다.
그 실험은 OOS와 같은 `274/282` 페이지 수뿐 아니라 체인 페이지 ID, OID 해시 및 힙 페이지 점유 결과도 재현했습니다.
원시 볼륨을 직접 읽은 검사는 각 인덱스의 100000개 고유 OID와 대응하는 힙 행 및 키를 확인했습니다.
세 엔진에서 논리적 데이터가 같았고 힙/B-tree 구조 `checkdb`도 통과했습니다. 이 무결성 실험은 이전에 기록한 엔진들에 해당합니다.

### 수정 범위

모든 파일은 private shell TC의 `shell/_38_fig/cbrd_24916_check_index_ovfps/cases/` 아래에 있습니다.

| answer 파일 | 변경 |
| --- | --- |
| `check_index_ovfps_sort1.answer` | xx1 키당 정수 평균 `55 → 54` |
| `check_index_ovfps_sort2.answer` | xx1 키당 정수 평균 `55 → 54` |
| `check_index_ovfps_sort3.answer` | xx1 키당 정수 평균 `55 → 54` |
| `check_index_ovfps_key2.answer` | xx1 키당 정수 평균 `55 → 54` |
| `check_index_ovfps_key3.answer` | xx1 총 페이지 `278 → 274`, xx2 총 페이지 `280 → 282` |

원본 `.sh` 파일, 입력 SQL, 난수 seed, 행 순서, 공백, 나머지 수치 및 플래그는 그대로입니다.
최댓값 answer인 `check_index_ovfps_key1.answer`도 바꾸지 않았습니다.
페이지 수를 가리거나 여러 값을 허용하지 않았습니다. 엔진 수정은 없습니다.

## Remarks

### Test Plan

수정 전과 수정 후에 각각 새 설치 복사본, DB registry, HOME 및 일회용 실행 공간을 사용했습니다.
원본 TC는 읽기 전용 corpus에서 가져왔고 파일 쓰기는 격리된 overlay에서 수행했습니다.
각 실행은 한 slot, 재시도 0, TC 업데이트 없음, 제외 0으로 진행했습니다.

```sh
TESTKIT_NATIVE=shell TESTKIT_CONTAIN=1 testkit shell -c "$CONF"
```

| 실행 | 관찰 및 판정 |
| --- | --- |
| develop `60ad770f0` + 원본 답지 | 1/1 PASS, 13개 검사 OK, 실행 산출물 검증 통과 |
| OOS `3252fcf` + 원본 답지 | 검사 8, 9, 10, 12, 13의 숫자 불일치 재현. 나머지 8개 검사는 OK |
| OOS `3252fcf` + 수정 답지 | 1/1 PASS, 13개 검사 OK, 실패·skip 0, 유효한 JUnit, 실행 산출물 검증 통과 |

수정 전 실행의 JUnit은 line 366에서 파싱에 실패했습니다. 위 실패 관찰은 보존한 원본 비교 로그와 검사별 OK/NOK 및 실행 요약에 근거합니다.
그 XML을 고치거나 실패를 통과로 처리하지 않았습니다. 수정 후 실행은 원본 XML 그대로 파싱과 검증을 통과했습니다.
커밋의 전체 diff는 실행 전 보관한 패치와 바이트 단위로 같습니다. 변경한 파일 5개의 내용 해시도 일치합니다.
숫자 외 문자와 공백은 수정 전후 동일합니다. `git diff --check`가 보고하는 줄 끝 공백은 기존 출력 형식을 보존한 것입니다.

### 검증 범위와 후속 작업

- 이 결과는 해당 TC 한 건의 로컬 검증입니다. 전체 shell suite나 GitHub CI 통과를 주장하지 않습니다.
- develop 비교는 위 커밋에 고정한 결과입니다. 이후 develop 커밋은 이 보고서의 재실행 대상이 아닙니다.
- 로컬 GCC 및 실행 환경은 CI 이미지와 다릅니다.
- 현재 head에서 TC 동작을 재검증했습니다. 원시 볼륨 전체 순회와 헤더 크기 분리 실험은 이전 보고서의 커밋 범위에 한정합니다.
- 통계 TC와 allocator crash의 후속 작업은 work item `490`의 별도 범위로 남아 있습니다.
- 이 관찰은 엔진 용량 계산 결함이나 머지 충돌 해결 실수의 근거가 아닙니다. 기존 OOS 통합 작업의 TC 유지보수로 처리합니다.

[검토할 PR 본문](CBRD-26357-oos-index-capacity-pr-body_3252fcf_codex.md)과 [게시 작업 범위](CBRD-26357-oos-index-capacity-pr-context_3252fcf_codex.md)를 별도로 보관합니다.
