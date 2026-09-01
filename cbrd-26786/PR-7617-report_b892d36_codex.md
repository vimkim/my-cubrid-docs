# PR #7617 코드 리뷰 보고서

**PR:** [CUBRID/cubrid#7617](https://github.com/CUBRID/cubrid/pull/7617)
**제목:** [CBRD-26786] Reclaim empty OOS pages in vacuum via file_dealloc
**작성자:** vimkim
**HEAD SHA:** `b892d36a4bd46d54f3e6cf4e5ae24924b6dfd4fe`
**리뷰 일시:** 2026-09-01

> **TL;DR** (Blocking): 같은 OOS(Out-of-row Overflow Storage, 큰 속성 값을 heap 레코드 밖에 저장하는 구조) 파일에서 두 insert가 동시에 성장하면 두 번째 insert가 진행 중인 성장 게이트 sweep(파일 확장 직전 빈 페이지를 회수하는 절차)을 건너뛰고 새 섹터를 예약할 수 있습니다. 이는 CBRD-26786의 핵심 성장 불변식을 직접 위반합니다.

## Summary

- **변경 요약**: vacuum fast path, LSA 게이트, 성장 게이트 sweep으로 완전히 빈 OOS 페이지를 `file_dealloc` 에 반환합니다.
- **주요 이슈**: 동시 grower가 진행 중인 sweep을 기다리지 않아 회수 가능한 페이지가 있어도 파일이 확장됩니다.
- **확인 필요 사항**: 두 번째 grower를 진행 중인 sweep과 조정하고 해당 동시성 회귀 테스트를 추가해야 합니다.
- **검증**: debug 빌드와 구성된 OOS 테스트 27개가 모두 통과했지만 동시 grower 시나리오는 포함하지 않습니다.

---

## Findings

### Blocking (must fix)

- `src/storage/oos_file.cpp:1783-1787,1817-1838,1952-1964` -- 같은 VFID의 첫 grower가 `sweep_in_progress` 를 설정하면 두 번째 grower는 `claimed == false` 로 즉시 sweep을 빠져나가 `oos_file_alloc_new` 를 호출하므로, 첫 sweep이 안전하게 회수 가능한 페이지를 반환하기 전에 `file_alloc` 이 새 섹터를 예약할 수 있고 파일 소유 공간이 불필요하게 영구 확장됩니다.

### Non-blocking (should consider)

- `src/query/vacuum.c:1945` -- 새 C++ 전용 호출인 `oos_touched_pages.empty()` 가 legacy `.c` 파일의 필수 `/* *INDENT-OFF* */` / `/* *INDENT-ON* */` 보호 밖에 있어 GNU indent 실행 시 해당 코드가 재작성되거나 흔들릴 수 있습니다.

## JIRA Context

CBRD-26786은 "OOS 파일은 지금 안전하게 회수 가능한 빈 페이지가 없을 때만 새 섹터를 예약한다"를 best-effort가 아닌 불변식으로 요구합니다. 현재 single-flight 우회는 코드 주석에서도 이 규칙의 의도적 완화라고 명시하므로 구현이 현재 JIRA 계약과 일치하지 않습니다.
