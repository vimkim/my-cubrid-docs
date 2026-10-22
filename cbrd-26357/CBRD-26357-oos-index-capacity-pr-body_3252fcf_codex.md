https://jira.cubrid.org/browse/CBRD-26357

## Purpose

OOS (큰 컬럼 값을 별도로 저장하는 기능)의 develop 병합을 준비합니다.

## Implementation

변경 사항은 준비 중이며 후속 커밋으로 추가할 예정입니다.

## Remarks

준비 중인 Draft PR입니다.

### 인덱스 용량 TC 기대값 조정

- `tc/pr-7990`의 `cbrd_24916_check_index_ovfps` answer 파일 5개에서 숫자 6줄만 조정합니다. 원본 스크립트와 13개 검사를 유지합니다.
- OOS의 `oos_vfid` 필드로 힙 헤더(테이블 저장 파일의 관리 정보)가 8바이트 커집니다. OID(행의 물리 주소) 배치가 달라져 인덱스 오버플로 페이지가 다르게 분할됩니다.
- `xx1/xx2`의 총 오버플로 페이지 수를 `278/280`에서 `274/282`로, `xx1`의 키당 정수 평균을 `55`에서 `54`로 갱신합니다.
- `1a8c705`에서 원시 볼륨 검사와 `checkdb`로 페이지 수 및 데이터 무결성을 확인했습니다. 기준 엔진의 헤더만 8바이트 늘린 실험도 OOS와 같은 배치를 재현했습니다.

### Test Plan

- develop `60ad770f0`에서 원본 TC의 13개 검사가 모두 통과했습니다.
- OOS `3252fcf`에서 수정 전 5개 검사의 불일치를 재현했습니다. 기대값 수정 후 새 DB에서 13개 검사와 실행 산출물 검증이 모두 통과했습니다.
- 이 결과는 해당 TC 한 건의 로컬 OptDebug 검증입니다. 전체 CI 통과를 뜻하지 않습니다.
- [수정 근거와 검증 범위](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/CBRD-26357-oos-index-capacity_3252fcf_codex.md)
