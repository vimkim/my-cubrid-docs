Replace MVCC Hdr or MVCC Header to Record Header for clarity. It seems confusing that OOS uses MVCC header. Currently we call is mvcc_flags for legacy issue but this will be refactored in the future (don't mention this).

---

불변식 — 루프는 pre-loop header 크기로 비교하는 보수적 추정: 최대 1개 over-demote 는 가능하지만 under-demote 는 불가 → "record 는 항상 페이지에 들어간다"가 보존된다. <- this part is not easy to understand. Make it easier to understand with examples. Mention that postgres has the same logic when sending to TOAST.

---

BLOB/CLOB locator 도 동일 규칙 <- do not mention this. not important.

---

Overall, the language is too nerdy. Make them easy and kind and understandable by Koreans.

---

경계 조건 OOS + bigone <- remove this. Say that, in the future, we plan on removing heap + bigone and remove multipage bigone and use OOS.

mention that,
There can be cases where nothing can go OOS anymore and still it dones not fix a single page. It had that issue that there were too many BIT columns and nothing can go OOS and the record size is still over DB_PAGESIZE so it errored. Postgres makes this case a user error. We can do the same.

---

Visualize more about multichunk chain.

---

Visualize Update and Delete workflows in separate slides.

Visualize the case where two transactions try to access records

Something like:
In repeatable read isolation level,

transaction A, B, C open
transaction A access an OOSed column

transaction B updates the record including the OOSed column
transaction C updates the record excluding the OOSed column

transaction A access an OOSed column
transaction B access an OOSed column
transaction C access an OOSed column

Visualize the above case.

---

Visualize the OOS delete.

OOS is currently insert/delete only, and on update, it actually inserts a new value always.

CUBRID logical update is actually a physical update in heap, and the old version goes to undo log with LSA record copy.

CUBRID logical delete is actually a physical update in heap, leaving no undo/redo LSA record copy.

Therefore, when vacuum cleans up OOS value, it must do two things:

To clean up updated stale OOS value, it must view the LSA record and extract OOS OIDs and clean up.

To clean up deleted stale OOS value, it must view the heap, and extract OOS OIDs from the heap record and clean up.

