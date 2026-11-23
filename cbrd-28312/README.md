# CBRD-28312

[CBRD-28312](https://jira.cubrid.org/browse/CBRD-28312): [OOS] 서버 측 INSERT·UPDATE가 행마다 레코드 버퍼와 OOS 부가 자료를 glibc malloc/free로 할당·해제한다. Parent: [CBRD-26978](https://jira.cubrid.org/browse/CBRD-26978). Related PR: none yet.

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [alloc-benchmark.md](alloc-benchmark.md) | Release A/B measurement and LBR profile attribution of per-row allocation cost on `ed394047b5` | 2026-11-23 | 2026-11-23 | Record the evidence behind registering CBRD-28312 |
