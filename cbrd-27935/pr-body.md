https://jira.cubrid.org/browse/CBRD-27935

> **Validation only.** 이 draft PR은 CI로 수정을 검증하려고 올렸다. 정식 PR 여부는 담당자 검토 뒤 정한다.

## Purpose

- `vacuum_heap_record`는 relocation된 행을 지울 때 forward 슬롯을 비우고, 그 페이지를 놓은 다음에 내부 작업(sysop)을 commit한다. 그 사이 다른 트랜잭션이 비운 슬롯을 쓰고, 서버가 중단되면 재시작 복구의 undo가 그 슬롯을 덮어쓸 수 있다.
- AS-IS: forward 페이지를 `log_sysop_commit` 전에 놓는다.
- TO-BE: forward 페이지를 `log_sysop_commit` 뒤까지 잡아, sysop이 끝나기 전에는 다른 트랜잭션이 그 슬롯을 쓰지 못한다.

## Implementation

- `src/query/vacuum.c`: `vacuum_heap_record`에서 forward 페이지를 `DONT_FREE`로 dirty 표시하고, `log_sysop_commit` 뒤에 놓는다.

## Remarks

- 이 수정과 CBRD-27936 수정을 함께 넣은 PR #8494(Inner Table POC)의 gha-ci run 43022406457에서 CREATE INDEX 중 `btsort_radix_validate` assert와 재시작 복구 중 `spage_find_empty_slot_at` assert가 났다. 같은 base의 develop은 통과했다. 두 수정을 따로 올려 어느 쪽이 원인인지 가린다. CBRD-27936은 별도 draft PR로 검증한다.
- 로컬 확인: 바뀐 파일을 debug와 `-O2 -Werror`로 컴파일했다. 서버 실행 테스트는 CI에 맡겼다.
