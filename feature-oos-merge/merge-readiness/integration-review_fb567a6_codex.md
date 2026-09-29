# develop 통합 후보 검토

대상: `fb567a629cdb390fff920542173fa36f454c74a0`. 기준: `1ec35f86c5e43b9ca86d81e202c68899f8ce4f21`. 통합한 develop: `f1bd99ed43a134383bc0be1d766a6f121601a499`.

## Standards

새 통합에서 발생한 규칙 위반 또는 수정이 필요한 구조 문제는 발견하지 않았다. 두 부모를 유지한 실제 merge commit이며 remerge diff는 비어 있다. grammar의 FILL_FACTOR와 기존 OOS FORCE_OUTLINE이 함께 유지됐다. 새 tuple-layout 소스는 세 빌드 대상에 등록돼 있다. 큰 tuple-format·crypto·broker·B-tree 변경은 develop에서 들어온 변경이다.

검토 범위는 통합 변경이며, develop의 11개 커밋 전체를 처음부터 다시 검토했다는 뜻은 아니다. 코드 검토 스킬이 참조한 docs/agents/issue-tracker.md는 이 작업 트리에 없다. 현재 실행 계약과 명시된 기존 통합 합의를 직접 기준으로 삼았다.

## Spec

새 통합 결함은 발견하지 않았다. 첫 부모는 기존 OOS head, 두 번째 부모는 고정한 develop이다. gha-ci.yml은 develop과 같으며 PR 유효 diff에 나타나지 않는다. CBRD-27407의 aggregate result handler, tuple/list 구현, 할당·재개 처리는 유지된다. query_executor.c의 추가 차이는 기존 OOS heap-fetch 인자 처리다.

CCI gitlink는 develop의 79d0888c26a2543d31f53eb7b6c9738db110fff4와 같다. 빌드가 만든 CCI win/cci_version.h의 working-tree 변경은 커밋에 포함하지 않았다. 핵심 OOS heap·chain·vacuum·unit-test 파일은 첫 부모에서 변경하지 않았다.

## 검증과 한계

- debug_gcc/release_gcc 빌드·설치 완료. release CTest도 35/35 통과, 140.40초. CMake를 준비된 런타임 환경으로 다시 구성한 뒤 CTest 35/35 통과, 160.56초.
- 최초 CTest는 구성 당시 CUBRID_DATABASES가 비어 있어 fixture setup에서 실패했다. 그 기록을 보존하고 환경 재구성 후 실행했다. 테스트 실행기 소스 변경은 없다.
- git diff --check는 query_hash_join.c의 두 trailing-whitespace 줄을 보고한다. 두 줄 모두 develop의 453da49c81에서 온 그대로이며 통합 소유 변경이 아니다. 별도의 무관한 서식 수정을 추가하지 않았다.
- 원래 feature-oos-merge의 AGENTS.md 변경 hash는 4e618a56f5eb2ed5bbef4839eeef6edc3609b8ff454c506f92fbc2f245c321b4로 유지됐다.
- 전체 QA·최종 head CI·선행 기능 PR·rollback/vacuum 데이터 손실 조건은 별도 미완료 항목이다.

Standards: 통합 소유 지적 0건. Spec: 새 통합 지적 0건. 전체 기술적 머지 준비 완료를 의미하지 않는다.
