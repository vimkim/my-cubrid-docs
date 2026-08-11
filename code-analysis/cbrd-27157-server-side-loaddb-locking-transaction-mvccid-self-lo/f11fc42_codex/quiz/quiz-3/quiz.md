# Quiz 3 — 큰 값이 연 숨은 loaddb 경로

100바이트 값과 5,000바이트 `BIT VARYING` 값을 각각 새 DB에 server-side `loaddb`로 넣는다고 생각하세요. 실행 전에 다음 call path의 빈칸을 채우세요.

```text
큰 값
  → [큰 값을 inline 밖으로 옮기는 단계]
  → [첫 전용 file을 만드는 단계]
  → file_create(FILE_OOS)
  → [현재 writer 식별자를 얻는 단계]
  → [transaction resource lock 단계]
  → 과거 TT_LOADDB assert
```

그다음 질문에 답하세요.

- OOS가 직접 `BU_LOCK` 또는 MVCCID self-lock을 잡나요?
- session과 worker batch 중 누가 `BU_LOCK`을 소유하고, 누가 MVCCID self-lock을 소유하나요?
- 현재 fix가 허용한 것은 모든 object lock인가요, transaction resource인가요?
- `exercise.sql` 결과만으로 역사적 수정 전 debug assert까지 재현했다고 말할 수 있나요?

## 안전한 실행

예상 시간은 약 20초다. launcher는 `ca27157q3srcf11`, `ca27157q3dstf11`만 소유하며 동명 DB가 있으면 중단한다. 실제 `unloaddb` → fixed build의 `loaddb -C` → `;oos_stats`를 수행하고 trap으로 두 DB를 정리한다.

```bash
./run.sh
```

## 답안 공백

- small/large가 storage placement의 대조군이 되는 이유: `__________`
- 이 결과가 역사적 pre-fix A/B가 아닌 이유: `__________`
- PostgreSQL/MySQL의 nearest mechanism과 비교할 때, CUBRID fix가 지켜야 하는 책임 경계 한 가지: `__________`
- 모든 object lock 허용으로 넓히지 않고 transaction resource만 허용해야 하는 invariant: `__________`

sample output은 비권위 형식 예시이며 실제 stdout과 cleanup 결과가 권위다.

연결: `loaddb-oos-regression`, `CUBRID-C020`, 8·9장.
