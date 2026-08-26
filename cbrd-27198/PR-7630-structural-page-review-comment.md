`structural page`의 의미와 적용 범위를 명확히 해주셨으면 합니다.

확인한 merge-base `169cef54`에는 `structural page`라는 표현이 없으며, 현재 HEAD의 다섯 용례는 모두 이 PR에서 추가됐습니다. 기존 CUBRID의 concrete page classification에는 `PAGE_VOLHEADER`, `PAGE_VOLBITMAP` 등이 있지만, 이를 묶는 `structural page` type, predicate 또는 membership rule은 없습니다.

이 표현이 단순히 현재 두 call site를 설명하기 위한 shorthand라면, generic한 `structural page` 대신 `volume-header page`와 `sector allocation-table page`를 정확히 명시하는 편이 적절해 보입니다.

반대로 transaction no-wait policy를 무시해야 하는 별도의 page category를 의도한 것이라면 다음 contract가 필요해 보입니다.

1. 정확히 어떤 page가 이 범주에 포함되는가?
2. Volume header와 sector table만 포함되는가, 아니면 file header, heap header, B-tree root 등도 포함되는가?
3. 이 범주에 속하는 page는 어떤 근거로 반드시 unconditional wait해야 하는가?
4. 향후 caller가 `pgbuf_set_force_latch_wait()`를 사용해도 되는지는 어떤 기준으로 판단하는가?

현재 `pgbuf_set_force_latch_wait(thread_p, bool)`는 page identity나 `PAGE_TYPE`을 전달받지 않으므로, 해당 범주를 코드에서 검증하거나 제한할 수 없습니다. 결과적으로 적용 범위가 전적으로 caller와 새 주석에 의존합니다. 새로운 enum을 반드시 추가해야 한다는 의미는 아니지만, wait behavior를 변경하는 policy boundary라면 최소한 정확한 대상과 invariant가 문서화돼야 한다고 생각합니다.

또한 helper 주석의 “latch is internal and held for microseconds”가 correctness 근거로 사용될 수 있는지도 확인이 필요합니다.

실제 reservation 경로에서는 [volume-header WRITE latch를 획득](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L4092-L4098)한 뒤 sector-table 전체 탐색과 allocation hint 갱신이 끝나고 [함수를 빠져나갈 때까지 보유](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/disk_manager.c#L4155-L4164)합니다. Sector-table page latch 역시 page 내부 unit 순회와 reservation/logging callback이 끝난 뒤 해제됩니다. 코드상 이 구간을 microseconds로 제한하는 deadline이나 상한은 확인되지 않습니다.

특히 volume-header WRITE latch를 보유한 상태에서 sector-table page latch를 요청합니다. Sector-table page가 busy하면 zero-wait transaction도 이 PR에 의해 waiter queue에 들어가며, [실제 wait에는 `page_latch_timeout_in_msecs`가 사용](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/storage/page_buffer.c#L7284-L7296)됩니다. 이 parameter의 [기본값은 300초](https://github.com/CUBRID/cubrid/blob/1185f16d7e5f540ffdad4509cbd061ef0535f4df/src/base/system_parameter.c#L5308-L5319)입니다.

따라서 worst case에는 한 thread가 sector-table page latch를 기다리는 동안 volume-header WRITE latch를 계속 보유하고, 다른 reservation thread들이 volume header에서 연쇄적으로 대기하는 latch convoy가 발생할 수 있습니다. 이것이 deadlock이라는 의미는 아니지만, `held for microseconds`가 코드로 보장되는 maximum hold time은 아니라는 점은 분명해 보입니다.

따라서 “microseconds”가:

- 코드로 보장되는 invariant인지,
- 경합이 없는 일반적인 경우의 관측값인지,
- 특정 benchmark 결과인지

알려주시면 좋겠습니다. 관측값이라면 사용한 workload와 worst-case 수치가 필요하고, invariant라면 어떤 코드 구조가 그 상한을 보장하는지 설명이 필요합니다. 현재 문구만으로는 측정되거나 강제되지 않은 성능 가정을 근거로 no-wait policy를 override하는 것으로 읽힙니다.

제가 다음 주 휴가이므로 후속 대응 부탁드립니다. @hornetmj
