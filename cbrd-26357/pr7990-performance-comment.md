PR #7990의 develop 머지 전 성능 평가를 기존 측정으로 정리했습니다([보고서](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-26357/pr7990-performance-evaluation.md)). 수치는 서버 CPU 명령어 수(`instructions:u`)이며, +는 PR이 develop보다 더 쓴다는 뜻입니다.

- **OOS 값이 없는 일반 테이블:** 최종 측정 head `2c38bef05b`와 develop `2e67e1d948`의 scan, 조건 scan, UPDATE 차이는 −2.0%~+1.2%입니다. 처음 보고해 주신 +7~10%는 #8299로 없어졌습니다.
- **OOS의 이득:** develop에서 overflow였던 22KB 행에서 작은 컬럼만 읽으면 명령어가 38~72% 줄고, 페이지 읽기는 200,087에서 20,003으로 줄었습니다(`67220b7e2`).
- **OOS의 손해:** 같은 행의 모든 컬럼을 읽으면 +6.05%로 잠정 목표(2%) 밖입니다. [CBRD-28064](https://jira.cubrid.org/browse/CBRD-28064)에서 줄이겠습니다. 파일 캐시가 빈 상태의 큰 값 조회 지연은 [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791)에서 다룹니다.
- **기준 2(4~16KB 전체 읽기):** 기본 임계값에서는 +2.8~+69.5%이고, 승인 때 받아 주신 대로 [CBRD-28062](https://jira.cubrid.org/browse/CBRD-28062)(#8632) 파라미터로 처리합니다. 기본값은 측정 후 11.5 전에 정합니다.
- **커밋 지연:** 행 하나 UPDATE+COMMIT 3000회의 `fdatasync`는 develop 3011회, PR 3006회로 #8434의 추가 flush는 없습니다.
- **UPDATE 재기록:** 작은 컬럼 UPDATE의 손해는 [CBRD-27230](https://jira.cubrid.org/browse/CBRD-27230)(#8559)으로 guava에 포함하겠습니다.

측정 head `2c38bef05b`와 현재 head `71993ddb63`의 차이(develop 동기화 2번과 CBRD-28254 수정)는 측정한 경로를 바꾸지 않는다고 판단했습니다. 추정이며 현재 head에서 다시 재지는 않았습니다. 측정하지 않은 항목과 한계는 보고서 7절에 있습니다.
