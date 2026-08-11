# CBRD-27157 loaddb 잠금 학습의 현재 기준점

사용자는 PR #7588의 코드를 따라가고 두 리뷰 의견을 전달할 수 있지만, `BU_LOCK`, MVCCID self-lock, lock resource와 transaction owner를 독립적으로 설명할 배경지식은 아직 부족하다고 밝혔다. 이후 lesson은 일반적인 C/C++ source reading 능력은 전제하되, 잠금 hierarchy와 MVCC waiter protocol은 기초부터 source-backed diagram으로 가르친다.

## Evidence

사용자가 “이 부분에 대해 배경지식이 많이 부족하다”고 명시하고 학습 자료와 지속적인 teaching을 요청했다.
