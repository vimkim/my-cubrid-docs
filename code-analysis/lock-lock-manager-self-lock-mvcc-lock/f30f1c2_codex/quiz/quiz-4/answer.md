# Answer 4 — completion rendezvous

Wait target은 inserter의 full MVCCID로 key된 `LOCK_RESOURCE_TRANSACTION`이다. T1은 X holder, T2는 S waiter다. `self`는 owner가 자기 MVCCID resource를 선점한다는 뜻이며 T1이 S를 요청해 자기 자신을 기다리는 protocol이 아니다.

X/S compatibility는 같은 typed key에서만 적용된다. T2는 grant 후 S를 full-release하고 MVCCID active 상태와 B-tree key를 다시 검사한다. T1 rollback이면 conflict row가 사라져 T2 key 100 insert가 성공한다.

INSID를 X ensure 전에 공개하면 T2 S가 holder 없이 즉시 성공할 수 있다. Inactive publication 전에 X를 풀면 T2가 깨어나 active owner를 보게 된다. 따라서 두 ordering 모두 correctness requirement다.

한 MVCCID X는 여러 inserted row observer의 completion wait를 모아 holder entry 수를 줄일 수 있다. 그러나 non-MVCC/tracking failure는 row X fallback이고 prepared 2PC는 OID list와 materialized object X가 필요하다. PostgreSQL XID lock은 transaction-resource 축, speculative token은 decision ordering 축의 partial analogy다. InnoDB implicit X는 목적은 닮지만 record resource이므로 direct equivalent가 아니다.

흔한 오답은 `tran_index == MVCCID`라고 보는 것, self-lock이 자기 자신을 block한다고 보는 것, observer S가 key를 transaction 끝까지 영구 보호한다고 보는 것, 이 정책이 모든 row X를 제거한다고 보는 것이다. Runtime Quiz는 unique/rollback 한 사례뿐이다. FK, page-unfix/root-restart instruction, scaling, fallback, prepared-2PC는 실행하지 않았다.
