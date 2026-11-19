https://jira.cubrid.org/browse/CBRD-28023

## Purpose

- `cubrid diagdb` 는 OOS 파일의 유형 이름을 `OUT_OF_LINE_OVERFLOW_STORAGE` 로 출력합니다. 기능 이름은 Out-of-row Overflow Storage(OOS)입니다. OOS는 큰 가변 길이 값을 테이블 행(heap 레코드) 밖의 별도 파일에 저장하는 기능입니다.
- 사용자가 보는 출력 문자열을 릴리스 뒤에 바꾸면 그 출력을 읽는 스크립트와 테스트 답안이 함께 깨집니다. 그래서 `feature/oos-merge` 가 `develop` 에 병합되기 전에 바꿉니다.
- AS-IS: diagdb가 OOS 파일 유형을 `OUT_OF_LINE_OVERFLOW_STORAGE` 로 출력합니다.
- TO-BE: diagdb가 OOS 파일 유형을 `OOS` 로 출력합니다.

## Implementation

- `src/storage/file_manager.c` 의 `file_type_to_string (FILE_OOS)` 가 `"OOS"` 를 반환합니다. 출력 문자열만 바뀌고 동작은 바뀌지 않습니다.
- `OOS` 를 고른 이유는 다음과 같습니다.
  - 다른 유형 이름은 enum 이름에서 `FILE_` 을 뺀 형태입니다. 예를 들어 `FILE_HEAP` 은 `HEAP`, `FILE_BTREE_OVERFLOW_KEY` 는 `BTREE_OVERFLOW_KEY` 입니다.
  - diagdb가 이미 출력하는 `OOS for HFID`, SQL `SHOW HEAP OOS`, CBRD-27350이 `cubrid spacedb` 에 추가할 `OOS` 행과 이름이 같습니다.
  - `diagdb -d2` 파일 목록의 유형 칸은 22자입니다. 이전 이름(28자)이나 `OUT_OF_ROW_OVERFLOW_STORAGE`(27자)는 이 칸을 넘어서 그 행만 오른쪽으로 밀립니다. `OOS` 는 다른 행과 줄이 맞습니다.

## Remarks

- 함께 바꾼 테스트는 `cubrid-testcases-private-ex` 의 `shell/_36_damson/cbrd_23608_tde/tbl_enc_08`, `tbl_enc_14` 답안과 `shell/_06_issues/_26_1h/cbrd_26527/cases/cbrd_26527.sh` 의 주석 2줄입니다. `cubrid-testcases` 에는 옛 문자열이 없습니다.
- 큰 값이 OOS로 옮겨진 테이블이 있는 데이터베이스에서 `cubrid diagdb -d1` 이 `type = OOS` 를 출력하는 것을 확인했습니다. `-d2` 파일 목록의 `OOS` 행도 다른 행과 줄이 맞습니다.
- TDE shell 테스트 `tbl_enc_08`, `tbl_enc_14` 가 새 답안으로 통과합니다.
- 엔진 소스, 단위 테스트, 스크립트에는 옛 문자열이 남아 있지 않습니다.
