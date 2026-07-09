불변식 — 틀려도 안전한 방향으로만 틀린다. 루프가 쓰는 record 크기 추정치는 항상 실제 이상이다 (비교 기준 header 크기를 루프 시작 시점 값으로 고정). 예: 실제 record 는 이미 3.9KB 로 줄었는데 추정치가 4.1KB 면 컬럼 하나를 더 내보낼 수 있다 — 비용은 약간의 추가 OOS I/O 뿐. 반대로 덜 내보내서 페이지에 못 들어가는 일은 없다. PostgreSQL 도 TOAST 로 내보낼 때 같은 보수적 추정을 쓴다

<- what? I thought the estimation was correct. Why the diff happens? I don't understand. Review the code and explain.
If so, this is a bug and do not mention. Write bug in my-cubrid-jira

---

오늘 특히 검토받고 싶은 것
① Demotion 정책 (DB_PAGESIZE/4 gate + largest-first) 과 그 불변식이 타당한가
② Vacuum 연동의 안전성 — OOS slot 재사용 시나리오 (CBRD-26950) 에 대한 방어 설계
③ 성능 측정 시나리오 S1–S7 이 OOS 의 가치와 비용을 공정하게 드러내는가

<- remove these awkward parts. I don't have things to be reviewed yet.
