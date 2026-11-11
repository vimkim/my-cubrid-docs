https://jira.cubrid.org/browse/CBRD-27925

## Purpose

- OOS 파일에서 값이 지워져 빈 페이지가 생기면, 다음 INSERT가 새 공간을 잡기 전에 그 페이지를 다시 써야 합니다(ADR-0009).
- AS-IS: 빈 페이지를 파일에서 해제(dealloc)한 뒤 `file_alloc`으로 같은 페이지를 다시 받습니다. 그때마다 system operation이 두 번 돌고, 다른 INSERT도 쓰는 OOS 헤더 페이지 래치를 그동안 잡고 있습니다.
- TO-BE: 빈 페이지를 해제하지 않고 그 자리에서 다시 씁니다. 해제는 `file_destroy`에서만 일어납니다.

## Implementation

- 성장(새 페이지가 필요한 INSERT)은 빈 페이지 집합에서 후보를 하나씩 꺼내 조건부 WRITE 래치로 잡습니다. 래치를 잡은 채로 `PAGE_OOS`인지, 이 파일의 페이지인지, 비었는지, 레코드가 들어갈 자리가 있는지 확인하고 그대로 씁니다(`oos_try_reuse_page`).
- 지워진 slot이 남아 자리가 모자라면 페이지를 새 OOS 페이지로 다시 초기화합니다. 이 로그는 redo 전용입니다(`RVPGBUF_NEW_PAGE`, vacuum의 dropped-file 페이지와 같은 방식). undo가 있으면 페이지가 타입 없이 할당된 채로 남기 때문입니다.
- vacuum fast path(배치 끝에서 빈 페이지 해제)와 그것에 필요한 emptied-page 목록 전달 코드를 지웁니다. `oos_delete`의 `emptied_vpids` 인자도 없어집니다.
- 지우기로 빈 페이지는 bestspace 캐시(전체 OOS 파일이 함께 쓰는 1,000칸)에 넣지 않고 빈 페이지 집합에만 넣습니다. 캐시는 반쯤 찬 페이지가 씁니다.
- 설계 결정은 `cubrid-oos-context`의 ADR-0011(제안 상태)에 적었습니다. ADR-0009 결정 3과 ADR-0010 결정 3을 고칩니다.

## Remarks

- #8434 위에 쌓인 PR입니다. #8434가 머지되기 전에는 diff에 #8434 커밋도 보입니다. 이 PR의 커밋은 마지막 5개입니다.
- 측정(CBRD-27872 churn, release 빌드, #8434 기준과 비교): sector 수는 2,000행 32, 6,000행 94로 같습니다. 반복 churn에서 파일이 첫 사이클보다 커지지 않습니다. 대량 UPDATE는 2,000행 129→111 ms, 6,000행 386→334 ms입니다. 단건·동시 INSERT는 차이가 없습니다.
- 로그 레코드는 INSERT 1,000건당 약 10.2K에서 6.2K로 줄어듭니다.
- 테스트: 빈 페이지 재사용, 재초기화와 abort, 재시작 후 재사용, 집합 넘침, churn 크기 테스트, 재초기화 직후 crash 뒤 재시작 테스트를 추가했습니다. 재초기화 로그를 빼거나 undo 가능하게 바꾸면 crash 테스트가 실패합니다.
- `ctest -R oos` 53개: rebase 전에는 모두 통과했습니다. #8434 새 head로 rebase한 뒤에는 부하가 큰 상태에서 51개 통과했고, 시간 초과 1개와 vacuum 타이밍 검사 1개는 단독으로 3번 다시 돌려 모두 통과했습니다.
- 남은 점: 재초기화 로그 뒤, INSERT 로그 전에 죽는 순간은 테스트하지 못했습니다(테스트 훅이 없음). UPDATE 뒤 vacuum이 정리를 마치는 시간이 #8434보다 길고, 원인은 아직 모릅니다. 여러 OOS 파일이 동시에 churn하는 경우는 측정하지 않았습니다.
