# CONTEXT — CUBRID 로그 매니저 용어집

> grill 세션에서 확정된 용어만 기록한다. 구현 세부사항은 overview/dynamic-analysis 문서 참조.

## LSA 좌표

- **LSA** (Log Sequence Address): 로그 내 바이트 좌표. `(pageid, offset)` 쌍.
- **prior_lsa**: 다음 로그 레코드가 받을 **메모리상 예약 좌표**. prior list(메모리 목록)에 레코드가 생성될 때 이 좌표를 할당받으며 전진한다.
- **append_lsa**: prior list에서 **로그 페이지 버퍼로 복사(drain)가 끝난 경계**.
- **nxio_lsa** ("next I/O LSA"): **디스크에 아직 기록되지 않은 첫 위치**. 이 좌표 미만의 모든 로그는 fsync까지 완료된 상태. "여기까지 썼다"가 아니라 "여기부터 안 썼다"는 방향임에 주의. 항상 완결된 레코드의 경계에만 멈춘다.

## prior list

- **prior list**: 로그 레코드의 메모리상 대기 목록. MPSC 큐(다수 생산자, 단일 소비자 역할)이되, 일반 비동기 로그 큐와 달리 **enqueue 시점에 레코드의 최종 LSA가 확정**된다(좌석 예약 시스템). 생산자는 `prior_lsa_mutex`(초단기)만 잡고, 소비(drain)는 `LOG_CS`를 잡은 자의 역할 — 평상시 log-flush 데몬, 로그를 되읽어야 하는 스레드(롤백 등)도 수행.
- **drain**: prior list 전체를 떼어 로그 페이지 버퍼로 복사하는 행위 (`logpb_prior_lsa_append_all_list`). 이때 `append_lsa`가 전진한다.
- **백프레셔**: prior list가 `log_buffer_size`를 넘으면 생산자가 데몬을 깨우고 레코드당 1ms 양보(소프트 스로틀, 하드 상한 없음).

## 커밋 내구성

- **durable (커밋 확정)**: 커밋 레코드 **전체**가 디스크에 있는 상태. 엄밀한 조건은 `nxio_lsa > commit_lsa` (= nxio가 커밋 레코드의 끝 이상). 코드의 대기 탈출 조건은 `nxio_lsa >= commit_lsa`(시작 LSA 기준, 등호 포함)인데, nxio가 레코드 경계에만 멈추는 성질 때문에 일반 경로에서는 strict `>`로만 탈출한다. 등호 케이스의 도달 가능성은 **미해결 질문** (dynamic-analysis 문서 참조).
- **commit_lsa**: 해당 트랜잭션의 `LOG_COMMIT` 레코드가 **시작**하는 LSA.
