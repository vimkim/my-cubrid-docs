# SP 내부 DML 제한 설계 검증

Created: 2026-11-11. Last modified: 2026-11-11 (Asia/Seoul).

| File | What it contains | Created | Last modified | Why it was created |
| --- | --- | --- | --- | --- |
| [report.md](report.md) | 원안의 불충분성, 보강 모델의 조건부 결과와 변형 검출을 구분한 기술 논문 | 2026-11-11 | 2026-11-11 | CAS와 XASL 정보만으로 두 제한 규칙을 적용할 수 있는지 판단 |
| [evidence/statechart.md](evidence/statechart.md) | 바깥 참조 테이블 검사를 제거했을 때의 최단 반례 | 2026-11-11 | 2026-11-11 | 잘못된 설계에서 실제로 위반을 찾는지 설명 |
| [verify/SKILL.md](verify/SKILL.md) | 검증 실행과 소스 동기화 절차 | 2026-11-11 | 2026-11-11 | 후속 구현 검토 시 모델의 가정과 실제 코드의 차이를 유지 |

보고서의 근거를 재현하기 위해 `SpDmlGuard.tla`, `check.py`, `view.mjs`를 보존한다. `evidence/results.json`은 원래 실행의 결과와 해시다. `evidence/no-overlap-check.cfg`와 `evidence/chart.mmd`는 반례 그림의 입력과 출력이다. 원문 로그와 후속 실행 출력은 `.scratch/`에 로컬 자료로 보존하고 Git 추적 대상에서 제외한다.

기존 CAS 가시 XASL 정보만으로 제한을 적용하는 원안은 소스 근거상 불충분하다. 유한 모델 검사는 정확한 입력과 실행 경계를 가정한 보강 알고리즘을 대상으로 한다. 여덟 변형의 `PASS`는 예상 위반 검출을 뜻한다. [기술 보고서](report.md)는 이 세 결과와 남은 구현 계약을 구분한다.

## 준비

Python 3.9 이상과 Java 8 이상을 사용한다. TLA+ tools 릴리스 1.7.4의 jar를 준비한다. 이 릴리스에 포함된 TLC는 실행 로그에 `2.19`로 표시된다.

```sh
mkdir -p "$HOME/.cache/tlaplus"
curl --fail --location https://github.com/tlaplus/tlaplus/releases/download/v1.7.4/tla2tools.jar \
  --output "$HOME/.cache/tlaplus/tla2tools-1.7.4.jar"
```

검사기는 jar의 SHA-256을 검사한다.

```text
936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88
```

다른 위치에 설치했다면 `TLA2TOOLS`에 jar의 절대 경로를 지정한다. `JAVA`로 Java 실행 파일을 선택할 수 있다.

## 검사

`my-cubrid-docs` 저장소 루트에서 실행한다.

```sh
python3 code-analysis/sp-dml-guard/check.py
```

정상 모델 한 개와 잘못된 변형 여덟 개의 검사가 모두 `PASS`여야 한다. 정상 모델에서는 모든 불변식이 성립해야 한다. 변형에서는 지정한 불변식 위반이 나와야 `PASS`다. 결과 폴더에는 config, 원문 로그, 상태 파일과 `summary.json`이 남는다. 결과 폴더는 기본으로 시스템 임시 디렉터리에 만든다.

결과를 지정한 새 폴더에 남기려면 실행한다.

```sh
python3 code-analysis/sp-dml-guard/check.py --out /tmp/sp-dml-check-review
```

기존 폴더는 덮어쓰지 않는다. 도구 설치 후 검사 전체에 300초 제한을 적용한다. 시간 초과나 예상하지 않은 TLC 결과는 실패다.

## 모델 범위

테이블 식별자는 `t1`, `t2`, `t3` 세 개다. 의미상 문장 열 종류와 최대 세 단계 활성 문장 스택을 검사한다. 준비와 실행을 분리하고 준비된 문장을 여러 조상 아래 재실행한다. 정상 복귀와 임의 깊이 오류 복귀도 검사한다. 준비 동작 자체는 실행 스택에 들어가지 않는다.

문장은 SELECT, DML, CALL을 구분한다. DML에는 한 테이블 쓰기, 다른 테이블 읽기와 함께 쓰기, 두 대상 쓰기, SELECT XASL을 쓰는 클라이언트 DML의 대표 형태가 있다. INSERT, UPDATE, DELETE, MERGE가 동일한 접근 집합을 갖는다면 같은 모델 문장으로 추상화한다.

`active`는 의미상 실행 조상이다. `frames`는 제안한 검사기가 보유한 메타데이터 스택이다. `prepared`는 재사용 가능한 준비 결과다. 안전성은 실제 `active`와 실제 쓰기 대상을 기준으로 판정한다. 검사기의 허용 결정은 `frames`와 관측 메타데이터를 사용한다. 두 경로를 나누어 메타데이터와 수명 오류를 드러낸다.

정상 모델은 정확한 `kind`, `refs`, `writes`가 매 실행에 제공된다고 가정한다. 세대 변경과 재컴파일 후에도 이 계약이 성립한다는 가정이다. 실제 추출, 캐시 프로토콜, 스키마 변경, view, partition, 원격 테이블, 트리거 부수 쓰기, 준비 시 평가, fetch 중 추가 실행은 모델이 검증하지 않는다. 내부 scan은 독립적인 SQL 프레임으로 만들지 않는다. 중첩 실행은 SP 내부 SQL 또는 그 실행 체인에 속하는 제한 대상 SQL로 해석한다.

모델은 한 클라이언트의 동기 재진입 체인과 준비 결과 한 개를 다룬다. 실행 진입 전에 쓰기 가능 여부를 판정한다. 행·래치·MVCC·실제 데이터 변경은 다루지 않는다. 시간 속성이나 무한 재귀에 대한 증명도 아니다. 이 모델의 반례는 제안 설계의 잘못된 변형에 관한 것이며 현재 엔진에서 실행한 SQL 재현 결과가 아니다.

## 시각화

[statechart 결과](evidence/statechart.md)는 바깥 테이블 검사를 제거한 변형의 최단 반례를 보여 준다. `/statechart` 스킬로 모델을 읽고 새 결과 폴더에 다시 생성한다. 이 저장소에 기록한 모델과 config, view를 입력으로 사용한다. 머신마다 달라지는 스킬 도구 경로는 저장하지 않는다.
