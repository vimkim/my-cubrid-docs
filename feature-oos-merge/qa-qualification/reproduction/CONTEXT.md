# OOS QA Investigation Vocabulary

OOS QA 실패 조사에서 사용하는 용어다. OOS 저장 동작의 규범적 용어는
[OOS-CONTEXT.md](/home/vimkim/gh/cubrid-oos-context/OOS-CONTEXT.md)를 따른다.

## Language

**OOS 관련 실패 후보**:
OOS의 직접 영향 또는 OOS 통합의 간접 영향이 의심되지만 인과관계가 아직 확정되지 않은 QA 실패다.
_Avoid_: OOS 결함, OOS 원인 확정

**OOS 직접 영향**:
OOS-backed 값의 저장, 읽기, 수명 또는 복제 동작이 실패 원인에 관여하는 영향이다.
_Avoid_: Feature 브랜치 실패만을 근거로 한 OOS 영향

**OOS 통합의 간접 영향**:
OOS 통합이 변경한 공통 동작에서 생긴 영향으로, 실패한 데이터가 OOS-backed 값일 필요는 없다.
_Avoid_: 직접 OOS 영향, 누락된 upstream 수정
