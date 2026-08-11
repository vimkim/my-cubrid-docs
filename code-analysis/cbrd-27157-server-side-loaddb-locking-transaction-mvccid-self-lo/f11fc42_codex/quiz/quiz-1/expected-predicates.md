# 기계적 성공 조건

- `PREDICATE_OK`에 `target_holder=BU_LOCK`과 `target_waiter=SCH_M_LOCK`이 있다.
- observer가 `after_bu` attribute를 읽는다.
- 마지막 줄이 전용 DB의 `CLEANUP_VERIFIED`다.

이 조건은 원인을 알려 주지 않는다. resource·owner·lifetime 설명은 학습자가 작성한다.
