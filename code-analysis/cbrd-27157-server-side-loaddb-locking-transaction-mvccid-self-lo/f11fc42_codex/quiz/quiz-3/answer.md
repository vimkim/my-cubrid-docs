# Quiz 3 모범 답안과 해설

큰 값은 OOS demotion을 거쳐 첫 `FILE_OOS` lazy creation을 연다. `file_create`는 vacuum의 dropped-file 식별자 재사용을 안전하게 판단하려고 current MVCCID를 요구한다. 처음 MVCCID가 발급되면 같은 transaction resource에 X self-lock을 잡는다. OOS가 lock manager의 새 정책을 만든 것이 아니라, 기존 정책으로 들어가는 숨은 길을 연 것이다.

class `BU_LOCK`의 owner는 loaddb session transaction이다. worker batch는 별도 transaction이며 자기 MVCCID self-lock을 소유한다. 현재 fix는 `TT_LOADDB`가 transaction resource를 획득하는 경우만 assert에서 허용한다. class/instance object-lock 우회 계약은 그대로 남는다.

검증 run은 같은 dump에서 small/large 두 행을 적재하고 값 일치 1을 확인한다. `;oos_stats`는 small에 OOS file이 없고 large에 OOS VFID와 live record가 있음을 직접 구분한다. 이것은 고정된 수정 후 debug build의 TO-BE 결과다. 수정 전 binary를 실행하지 않았으므로 역사적 assert 실패의 runtime A/B 재현이라고 확대하면 안 된다.

이 책이 source-backed로 비교한 범위는 TOAST/off-page 저장 배치 자체가 아니라 loader와 lock의 책임 경계다. PostgreSQL `COPY FROM`의 relation lock과 MySQL `LOAD DATA`의 MDL·InnoDB table lock은 CUBRID `BU_LOCK`과 coarse coordination만 닮은 Partial analogy다 (`PG-C001`, `MYSQL-C001`, `CMP-C001`). unfinished inserter 재검사도 CUBRID·PostgreSQL의 transaction-ID rendezvous와 MySQL의 record wait/retry가 전체적으로는 Partial analogy다 (`PG-C010`, `MYSQL-C010`, `CMP-C010`). 따라서 이 Quiz 결과로 PostgreSQL TOAST나 MySQL off-page storage 구현까지 비교했다고 말하면 근거 범위를 벗어난다.

fix invariant는 `TT_LOADDB`의 기존 object-lock 우회 계약을 넓히지 않고, worker가 자기 MVCCID를 발급받을 때 필요한 transaction resource self-lock만 허용하는 것이다. 흔한 오답은 OOS가 직접 BU/self-lock 정책을 만든다고 보거나 모든 object lock을 예외 처리하는 것이다.
