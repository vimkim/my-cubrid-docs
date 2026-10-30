# CBRD-27785 보고서 학습 진행표

팀원에게 읽기 최적화의 변경 이유, 실행 경로와 근거의 한계를 설명하기 위한 진행표다.
설명한 범위와 남은 범위를 기록한다. 체크 표시는 설명을 제공했다는 뜻이며,
학습자의 이해나 발표 준비가 검증됐다는 뜻은 아니다.

작성일과 수정일은 2026-10-30, Asia/Seoul이다.
학습 대상은 `CUBRID/CUBRID`의 `f1b99031c0402d521a785815f107be7a83b27717`이다.
주교재는 [읽기 최적화 코드 해설서](CBRD-27785-code-walkthrough_f1b99031c_codex.md)다.
[질문집](CBRD-27785-learning-questions_f1b99031c_codex.md)은 이전 질문형 진행의 응답과 교정 기록을 보존한다.
전체 학습 작업은 work-tracker 620번으로 추적한다.

## 현재 진행 방식

2026-10-30의 요청에 따라 `pstack-teach`로 질문 없이 설명한다.
한 번에 한 주제를 짧게 설명하고, 사용자가 요청한 깊이와 방향을 따른다.
되묻기, 퀴즈와 재답변 검사를 진행하지 않는다.

설명이 끝난 항목을 체크하고 다음 항목으로 이동한다.
추가 설명이 필요해지면 관련 항목을 다시 열고 이유를 남긴다.
새 주제는 현재 목표에 필요한 경우에만 추가한다.
이후 shared reader와 UPDATE revision은 이 진행표의 범위에 포함하지 않는다.

<a id="teaching-todo"></a>
## 학습 TODO

- [x] T01. 일반 값도 공통 reader를 거치며 OOS 전용 scratch를 별도 helper로 분리한 이유를 설명한다.
- [x] T02. 지역 scratch와 동적 메모리 할당, stack 예약 크기와 실행 instructions 개수를 구분한다.
- [x] T03. 배열 선언의 블록 위치만으로 생성된 stack frame 축소를 보장할 수 없음을 설명한다.
- [x] T04. helper 반환 후 지역 scratch의 수명이 끝나는 문제와 Resolve·변환을 같은 수명에 묶는 이유를 설명한다.
- [x] T05. 일반 inline bytes와 임시 OOS bytes의 수명, COPY 요청과 type handler의 기존 계약을 설명한다.
- [ ] T06. record의 `HAS_OOS`, 개별 필드의 `IS_OOS`, 요청한 OOS 속성 수에 따른 scalar·grouped 선택을 설명한다.
- [ ] T07. 기존 record layout 재사용, offset 폭과 길이 계산, collection의 물리 순서 처리를 설명한다.
- [ ] T08. 일반·without-OID·lazy 읽기와 index-key 소비자의 연결 및 변경 범위를 설명한다.
- [ ] T09. NULL·기본값·구 representation·pending owner와 오류 시 정리가 유지되는 경로를 설명한다.
- [ ] T10. 코드 diff와 성능 비교의 기준 revision, instructions와 경과 시간, 테스트 및 측정 범위의 한계를 설명한다.
- [ ] T11. 앞의 내용을 팀 발표 순서로 정리하고, 예상 질문에 대한 설명을 준비한다.

## 다음에 이어갈 위치

다음 항목은 T06의 record·필드 flag와 grouped 선택이다.
T05의 inline 문자열 COPY 질문은 철회하고, record bytes와 OOS scratch의 수명 차이 및
COPY 요청이 모든 타입의 실제 복사 여부를 보장하지는 않는다는 내용을 설명했다.

## 지금까지 답변에서 확인한 내용

질문형으로 진행하던 시기의 기록이며, 앞으로 퀴즈를 계속한다는 뜻은 아니다.

- 일반 읽기마다 동적 메모리 할당을 한 것은 아니라는 구분을 학습자가 직접 설명했다.
- 조건문 안으로 배열 선언을 옮겨도 stack frame 축소가 보장되지는 않는다는 결론을 답했다.
  `implementation-defined`라는 표준 용어와 컴파일러의 코드 생성 선택은 구분해 설명했다.
- helper 반환 후 지역 scratch의 주소를 계속 사용하는 수명 문제를 답했다.

기존 보고서의 성능 결과는 이 학습 진행표의 새 실측이 아니다.
설명한 항목 수를 이해도 점수나 성능 검증 결과로 해석하지 않는다.
