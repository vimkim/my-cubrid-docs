Replace MVCC Hdr or MVCC Header to Record Header for clarity. It seems confusing that OOS uses MVCC header. Currently we call is mvcc_flags for legacy issue but this will be refactored in the future (don't mention this).

---

불변식 — 루프는 pre-loop header 크기로 비교하는 보수적 추정: 최대 1개 over-demote 는 가능하지만 under-demote 는 불가 → "record 는 항상 페이지에 들어간다"가 보존된다. <- this part is not easy to understand. Make it easier to understand with examples. Mention that postgres has the same logic when sending to TOAST.

---

BLOB/CLOB locator 도 동일 규칙 <- do not mention this. not important.

---


