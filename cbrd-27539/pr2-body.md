https://jira.cubrid.org/browse/CBRD-27539

## Purpose

- #8751에서 루트 `AGENTS.md`와 `src/AGENTS.md`를 바로잡은 뒤, AI 코딩 도구가 읽는 나머지 문서(모듈별 `AGENTS.md` 21개, `src/storage/docs/`, 설치 문서)를 같은 기준으로 정비합니다.
- AS-IS: 모듈 문서에 없는 파일·함수·빌드 타깃이 적혀 있고, 일부는 `src/AGENTS.md`와 반대로 지시합니다(예: 에러 코드를 `dbi_compat.h`에도 추가). 절차 문서는 글자 그대로 따르면 틀립니다(예: `ER_LAST_ERROR`를 새 코드로 바꾸면 `er_set ()`이 그 코드를 거부합니다).
- TO-BE: 모든 문서가 현재 코드와 맞고, 문서끼리 충돌할 때의 우선순위가 정해져 있으며, 등록·순서·호환성 절차를 그대로 따라도 올바른 결과가 나옵니다.

## Implementation

- 루트 `AGENTS.md`: 문서 간 충돌 규칙(코드와 빌드 파일 우선)을 추가했습니다. `build.sh` `clean`이 `-b`와 `-p`를 모두 지운다는 경고, DB를 띄우는 테스트 전에 `$CUBRID`·`$CUBRID_DATABASES`를 임시 경로로 지정하라는 안내, `ctest`는 `add_test`한 모듈만 실행한다는 설명과 `--no-tests=error` 권장, PR 정적 검사가 이름이 바뀐 파일을 건너뛴다는 주의, `tc/pr-<N>` 브랜치 수명 주기를 넣었습니다.
- `src/AGENTS.md`: 에러 코드 절차(sentinel 의미, 두 `cubrid.msg`의 `Last Error` 이동), 복구 인덱스 절차(enum·alias 위치, `RV_fun[]`, `RCV_IS_*`, page-less 레코드, TDE 사용자 데이터 분류 `LOG_MAY_CONTAIN_USER_DATA`, 동기 redo, 복제 레코드), XASL 절차(`xts_sizeof_*`, `xasl_spawner` 복사, 스트림 버전 없음)의 빠진 단계를 채웠습니다.
- 모듈 `AGENTS.md`(base, storage, transaction, query, xasl, optimizer, parser, object, compat, sp, method, broker, communication, connection, executables, loaddb, monitor, thread, `pl_engine`, `unit_tests`, `unit_tests/oos`): 틀린 파일·심볼·타깃·역할을 고치고, `src/AGENTS.md`와의 충돌을 없애고, 실제 코드와 맞지 않는 전면 금지 규칙을 실제 조건으로 바꿨습니다. 순서가 중요한 등록 절차(네트워크 요청, `OPERATOR_TYPE`, utility map, CAS 함수 코드)에는 "끝에 추가" 같은 규칙을 명시하고, 쉽게 낡는 파일 목록과 숫자는 줄였습니다.
- `README.md`: 대상 없는 `./build.sh` 대신 `./build.sh -m release build`를 안내하고, 대상을 생략하면 빌드·설치 디렉터리를 먼저 지운다는 점을 적었습니다. `docs/install_build_requirements.md`: 일회용 컨테이너용 절차임을 밝히고, CMake tarball로 `/usr`을 덮어쓰지 않게 바꿨습니다. `src/storage/docs/` 3개는 낡은 함수 언급과 OOS 안내만 고쳤습니다.
- 코드 주석만 수정(동작 변경 없음): `error_code.h`의 낡은 `dbi_compat.h` 안내 삭제, `execute_statement.c`의 serial 최솟값 주석(`-e36` → `DB_SERIAL_MIN`) 정정.

## Remarks

- 엔진 동작, CMake 설정, SQL 동작은 바꾸지 않았습니다.
- 문서가 아니라 코드를 고쳐야 하는 항목은 분리했습니다: [CBRD-28388](https://jira.cubrid.org/browse/CBRD-28388)(ctest 미등록), [CBRD-28409](https://jira.cubrid.org/browse/CBRD-28409)(PR 검사의 rename 누락), [CBRD-28410](https://jira.cubrid.org/browse/CBRD-28410)(PL Gradle JDBC), [CBRD-28411](https://jira.cubrid.org/browse/CBRD-28411)(`build.sh -h`, `pl_unittest`, 죽은 코드). 이 문서들은 현재 동작을 설명하므로, 해당 이슈가 해결되면 관련 문구도 함께 갱신해야 합니다.

### Test Plan

- `git diff --check`: 공백·개행 오류 없음.
- 변경한 Markdown 28개의 상대 링크와 앵커가 모두 실제 파일·헤딩을 가리키는지 검사: 통과.
- 주장 검증: 수정본을 만든 agent와 별개인 reviewer 2명이 추가·변경된 모든 주장을 `ca5c2153ed`의 코드와 대조했습니다. 지적 11건을 코드로 재확인한 뒤 모두 반영했습니다.
- 감사 근거(교차 검증한 문제 107건, 실제 작업 시험 8건): [agents-meta-audit.md](https://github.com/vimkim/my-cubrid-docs/blob/main/cbrd-27539/agents-meta-audit.md)
