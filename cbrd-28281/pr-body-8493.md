https://jira.cubrid.org/browse/CBRD-28281

## Purpose

- OOS 파일에서 값이 지워져 빈 페이지가 생기면, 다음 INSERT가 새 공간을 잡기 전에 그 페이지를 다시 써야 합니다(ADR-0009). 이 규칙은 #8434(CBRD-27925)로 충족했고, 이 PR은 그 재사용 경로의 비용을 줄입니다.
- AS-IS: 빈 페이지를 파일에서 해제(dealloc)한 뒤 `file_alloc`으로 같은 페이지를 다시 받습니다. 그때마다 system operation이 두 번 돌고, 다른 INSERT도 쓰는 OOS 헤더 페이지 래치를 그동안 잡고 있습니다.
- TO-BE: 빈 페이지를 해제하지 않고 그 자리에서 다시 씁니다. 해제는 `file_destroy`에서만 일어납니다.
- 2026-11-05 미팅에서 유지하기로 한 vacuum fast path를 없애므로, 채택 여부는 CBRD-28281에서 정합니다. 그때까지 Draft로 둡니다.

## Implementation

- 성장(새 페이지가 필요한 INSERT)은 빈 페이지 집합에서 후보를 하나씩 꺼내 조건부 WRITE 래치로 잡습니다. 래치를 잡은 채로 `PAGE_OOS`인지, 이 파일의 페이지인지, 비었는지, 레코드가 들어갈 자리가 있는지 확인하고 그대로 씁니다(`oos_try_reuse_page`).
- 지워진 slot이 남아 자리가 모자라면 페이지를 새 OOS 페이지로 다시 초기화합니다. 이 로그는 redo 전용입니다(`RVPGBUF_NEW_PAGE`, vacuum의 dropped-file 페이지와 같은 방식). undo가 있으면 페이지가 타입 없이 할당된 채로 남기 때문입니다.
- vacuum fast path(배치 끝에서 빈 페이지 해제)와 그것에 필요한 emptied-page 목록 전달 코드를 지웁니다. `oos_delete`의 `emptied_vpids` 인자도 없어집니다.
- 지우기로 빈 페이지는 bestspace 캐시(전체 OOS 파일이 함께 쓰는 1,000칸)에 넣지 않고 빈 페이지 집합에만 넣습니다. 캐시는 반쯤 찬 페이지가 씁니다.
- 설계 결정은 `cubrid-oos-context`의 ADR-0011(제안 상태)에 적었습니다. ADR-0009 결정 3과 ADR-0010 결정 3을 고칩니다.

## Remarks

- #7990이 develop에 squash 병합되어(`68a9c7766f`) base를 develop으로 바꿨습니다. 원격 PR head(`f1c78ce70b`)는 아직 11-12의 `feature/oos-merge` 위에 있어 develop과 충돌하며, CBRD-28281 triage 뒤 추가 테스트 커밋(`96fb566bcc`, 로컬)을 포함해 develop으로 rebase하고 CI를 실행합니다.
- 측정(CBRD-27872 churn, release 빌드, #8434 기준과 비교): sector 수는 2,000행 32, 6,000행 94로 같습니다. 반복 churn에서 파일이 첫 사이클보다 커지지 않습니다. 대량 UPDATE는 2,000행 129→111 ms, 6,000행 386→334 ms입니다. 단건·동시 INSERT는 차이가 없습니다.
- 로그 레코드는 INSERT 1,000건당 약 10.2K에서 6.2K로 줄어듭니다.
- 기존 테스트(`ctest -R oos` 53건): rebase 전 모두 통과했고, #8434 새 head rebase 뒤 부하 상태에서 51건 통과, 나머지 2건은 단독 3회 재실행으로 통과했습니다.
- **vacuum drain 지연(`0.34 s → 2.4 s`) 원인 규명**: `er_log_vacuum` 분석 결과, fast path 제거 후 vacuum worker가 `file_dealloc` sysop WAL로 후속 31쪽 블록을 스스로 닫아주던 부수 효과가 사라져 idle filler가 단일 31쪽 블록을 닫아야 해서 생기는 현상입니다(`REPEAT('f', 1500)` filler는 LZ4 압축 기준 약 2.07쪽 전진). 대기·filler 없는 연속 churn 3종에서 무한 누적이나 vacuum backlog는 없었고, 섹터 수도 ADR-0010과 같거나 작았습니다(500행 16 vs 17, 1,000행 24 vs 24, 동시 4세션 47 vs 48, 2,000행 36 vs 33~37).
- **재초기화~INSERT 사이 crash 공백 해소**: 빈 OOS 페이지를 대상으로 하는 undo 경로가 코드상 0건임을 확인했고, `oos_test_exit_after_empty_page_reinit` 훅으로 `RVPGBUF_NEW_PAGE` flush 직후 `RVOOS_INSERT` 전 crash 테스트 2건(단독·선행 미커밋 `RVOOS_INSERT`로 active UNDO 동반)을 추가해 Debug 빌드 `ctest` OOS 12/12(`test_oos_server_crash_recovery` 4건 포함)를 통과했습니다(로컬 커밋 `96fb566bcc`).
- 남은 점: 여러 OOS 파일이 동시에 churn하는 경우는 측정하지 않았습니다.
- 기술 검증 상세 보고서: https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-28281/adr-0011-technical-verification.md
