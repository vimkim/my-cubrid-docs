# CBRD-27725: OOS 분리 시점 지연 대안 평가

[CBRD-27725](https://jira.cubrid.org/browse/CBRD-27725)는 [PR #7927](https://github.com/CUBRID/cubrid/pull/7927)의 승인 방식과 전체 인라인 행을 유지하는 대안을 비교하는 평가 과제이다. 관련 설계·POC 이력은 [CBRD-27089 문서](../cbrd-27089/README.md)에 있다.

- [단계별 before·after 설명 보기](before-after_4a4d069_codex.html): 파티션 선택 전의 메모리 모습과 동일한 최종 디스크 모습을 비교한다.
- [공유·삽입용 SVG](before-after_4a4d069_codex.svg): HTML과 같은 도식이다. 독립적인 이미지로 재사용하기 위해 함께 보관한다.

비교 소스는 `4a4d069c21fc19f14337efceca512b726724ecd8` 이며, after는 미채택 평가 후보이다. 문서 작성일은 2026-10-22(Asia/Seoul)이다. 새 엔진 실행이나 성능 측정 결과를 포함하지 않는다.
