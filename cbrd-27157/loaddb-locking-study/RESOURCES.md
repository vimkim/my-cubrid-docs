# CBRD-27157 loaddb 잠금 설계 Resources

## Knowledge

- [CUBRID 한국어 매뉴얼: MVCC와 MVCCID](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/ko/sql/transaction.rst#L291-L351)
  MVCC가 여러 row version과 inserter/deleter MVCCID로 가시성을 판단하는 기본 모델. Use for: MVCCID와 INSID의 의미를 처음 확인할 때.
- [CUBRID 한국어 매뉴얼: 잠금 protocol과 granularity](https://github.com/CUBRID/cubrid-manual/blob/3b6ae97bfbdc664b010ffa933ded5a05b291ae03/ko/sql/transaction.rst#L715-L758)
  object lock, table/row granularity, intent lock의 공식 설명. Use for: class lock과 instance lock의 계층을 복습할 때.
- [CUBRID source: lock compatibility table](https://github.com/CUBRID/cubrid/blob/f11fc42594732c263d8f10101f9df73a21346ee9/src/transaction/lock_table.c#L35-L131)
  `BU_LOCK`이 `BU_LOCK`·`SCH_S_LOCK`과 호환되고 일반 data access의 IS/S/IX/SIX/X와 충돌한다는 primary source. Use for: “다른 transaction이 들어올 수 없다”는 말을 정확히 한정할 때.
- [CBRD-23375 commit: no locking for load workers](https://github.com/CUBRID/cubrid/commit/1994f0be34e919d3819c92eef39837f00d98827f)
  `TT_LOADDB` object-lock 우회와 internal assert가 함께 들어온 역사적 primary source. Use for: 기존 규칙의 범위를 해석할 때.
- [CBRD-26942 commit: transaction MVCCID self-lock](https://github.com/CUBRID/cubrid/commit/741734a8f3785a3e2a678bb52e289000c2261b6f)
  per-row X lock을 transaction-keyed rendezvous로 바꾼 설계의 primary source. Use for: self-lock의 보호 대상과 waiter 동작을 이해할 때.
- [PR #7588 head: `lock_manager.c`](https://github.com/CUBRID/cubrid/blob/f11fc42594732c263d8f10101f9df73a21346ee9/src/transaction/lock_manager.c#L3471-L3543)
  generic resource acquisition과 현재의 `TT_LOADDB || is_transaction_lock` assert를 보여주는 구현 증거. Use for: 현재 수정안의 정확한 범위를 확인할 때.
- [PR #7588 head: `log_tran_table.c`](https://github.com/CUBRID/cubrid/blob/f11fc42594732c263d8f10101f9df73a21346ee9/src/transaction/log_tran_table.c#L4053-L4170)
  MVCCID 발급 시 self-lock을 얻는 choke point와 기존 no-op guard를 보여주는 구현 증거. Use for: early return을 둘 seam을 검토할 때.
- [PR #7588 head: bulk insert의 INSID 처리](https://github.com/CUBRID/cubrid/blob/f11fc42594732c263d8f10101f9df73a21346ee9/src/storage/heap_file.c#L21188-L21265)
  `is_bulk_op`이면 MVCC INSID를 기록하지 않는 구현 증거. Use for: loaddb self-lock의 현재 관측자가 있는지 판단할 때.
- [PR #7588](https://github.com/CUBRID/cubrid/pull/7588)
  현재 patch, 설명, 검증 결과, 리뷰 대화를 함께 보는 작업 맥락. Use for: 최종 결정을 내리기 전에 live discussion을 확인할 때.
- [Local analysis: CBRD-27157 loaddb MVCCID self-lock](/home/vimkim/gh/my-cubrid-docs/cbrd-27157/CBRD-27157-loaddb-mvccid-selflock_c0a5e1e_claude.md)
  초기 skip안과 uniform self-lock 개정안을 한 문서에서 비교한 supporting evidence. Primary source가 아니므로 반드시 source/commit과 대조한다.

## Wisdom (Communities)

- [PR #7588 review thread](https://github.com/CUBRID/cubrid/pull/7588#discussion_r3719386723)
  CUBRID maintainers가 `BU_LOCK`과 MVCCID self-lock의 적용 범위를 실제로 협의하는 곳. Use for: 학습한 구분을 실전 질문으로 검증할 때.
- CUBRID storage/transaction 팀 회의 및 담당 개발자 DM
  코드에 기록되지 않은 설계 의도와 운영 경험을 확인하는 가장 직접적인 practitioner feedback. 질문은 resource, owner, observer, invariant를 분리해 제시한다.

## Gaps

- CBRD-23375 ticket 본문에서 “no locking”이 object lock만을 뜻했는지 모든 lock resource를 뜻했는지에 대한 명시적 문구는 아직 확보하지 못했다.
- PR #7588의 skip 대 uniform self-lock 선택은 팀의 추가 논의가 필요한 live decision이며, 본 자료는 어느 쪽도 accepted design으로 표시하지 않는다.
