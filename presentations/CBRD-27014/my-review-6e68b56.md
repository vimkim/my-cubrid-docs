 언제 생기나
예: 큰 고정 길이 BIT(n) 컬럼이 여러 개인 테이블. variable column 을 전부 OOS 로 보내도 record 가 한 페이지 (≈16KB) 를 넘는다 — 실제 QA 에서 만난 사례다.

이때 OOS OID 를 품은 record 를 여러 페이지짜리 bigone (overflow record) 으로 다시 쪼개는 조합은 지원하지 않는다 (CBRD-26937).

this part is too difficult to understand. Show an example schema code and explain in easy language.

---

Resolve 대신 Lazy read 라는 말을 써줘.

---

Call site 전수조사 했다는 부분은 빼줘.

---

raw-byte 를 소비하는 경로가 Expand 를 빠뜨리면, 값 대신 OOS OID 가 그대로 밖으로 새어 나간다. 확인된 사례: xlocator_fetch_all → unloaddb/compactdb (CBRD-26948 · OPEN). <- 이거에 대해서는 별도 slide 로, recdes 가 네트워크를 통해 밖으로 빠져나가는 unloaddb 의 경우 OOS OID 를 모두 OOS payloads 로 바꿔서 완전한 형태의 recdes 를 보내는 작업이 필요하다고 말하고 visualize

---

OOS Chunk (partial OOS payload) 라고 이름 짓고 Chunk record 라는 말은 사용하지 말자.

---

동시성에 대해서 그냥 테이블만 적지 말고 record 형태가 어떻게 바뀌는지 visualize 해줘.

슬라이드 여러장 사용해도 좋아.

---

claude.md 에 슬라이드 수 제한 이런거 지워줘.

