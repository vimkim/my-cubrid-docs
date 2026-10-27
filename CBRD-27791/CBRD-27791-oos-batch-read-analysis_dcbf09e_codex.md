# CBRD-27791: 큰 값 조회 비용과 OOS batch read 분석

측정·분석일: 2026-10-28, Asia/Seoul. 문장 개정일: 2026-10-28, Asia/Seoul.
독자: CUBRID 개발 경험은 있지만 이번 OOS 분석을 처음 읽는 개발자.
원측정은 Work Item 537, 이번 문장 개정은 Work Item 539다.
대상은 [CBRD-27791](https://jira.cubrid.org/browse/CBRD-27791)이며, 후속 작업은
[구현·검증 계획](CBRD-27791-oos-batch-read-plan_dcbf09e_codex.md)에서 설명한다.

## 무엇을 알아보려 했는가

OOS는 큰 값을 행의 본문 밖에 따로 저장해, 작은 컬럼만 조회할 때 큰 값을 읽는 비용을 피하는 기능이다.
그렇다면 큰 값의 내용까지 필요한 조회는 어떤가? 앞선 측정에서는 OOS가 읽는 양을 줄이고도 조회를 더 늦게 끝낸 경우가 있었다.
이번 분석은 그 결과를 다시 확인하고, 읽을 요청을 일정 범위로 모아 순서를 바꾸는 batch read를 엔진에서 검토할 근거가 있는지 조사했다.

확인한 결과는 두 가지다. 실제 SQL에서는 작은 컬럼 조회의 이득과 큰 값 조회의 비용이 함께 재현됐다.
엔진 밖에서 읽기 요청만 따로 재생한 실험에서는 제한된 범위의 순서 변경으로 시간을 줄인 경우가 있었다.
따라서 다음 단계는 엔진 안에서도 같은 이득이 남는지 검증하는 것이다.
이 문서에는 새 batch read를 구현한 뒤 SQL이 빨라졌다는 결과는 없다.

## 큰 값을 밖에 저장하면 무엇이 달라지는가

행을 담는 기본 저장 공간을 heap이라고 한다. OOS, 즉 Out-of-row Overflow Storage는 큰 값을 별도 OOS 페이지에 저장하고,
heap의 행에는 그 값을 찾아갈 참조를 둔다. 한 값이 여러 조각에 걸치면 조각을 따라 읽는다. 이 연결을 value chain이라고 한다.

작은 컬럼만 필요한 조회는 heap에서 필요한 값을 얻고 큰 값은 읽지 않아도 된다.
heap의 행이 작아지므로 같은 페이지에서 더 많은 행을 읽을 수 있다는 이득도 있다.
반면 큰 컬럼의 내용을 비교하거나 집계하려면 heap에서 참조를 얻은 뒤 OOS 페이지를 찾아가 값을 읽어야 한다.
읽는 전체 바이트가 줄어도 요청의 위치와 순서가 달라지면 대기 시간이 늘 수 있다.

이처럼 실제로 필요한 속성의 값을 그때 읽는 동작을 이 문서에서는 Resolve라고 부른다.
뒤의 batch read 후보도 이 동작을 보존해야 한다. 작은 컬럼 조회까지 큰 값을 미리 읽게 만들면 OOS의 이득을 잃기 때문이다.
확인한 함수별 동작은 [소스 근거](#부록-e-현재-소스의-책임과-보존할-조건)에 모았다.

## 실제 SQL에서 확인한 이득과 비용

두 엔진에 같은 100,000행 입력을 넣고 SQL을 실행했다. 아래는 기준 엔진에서 행이 커서 일반 heap 페이지에 담기지 않아 overflow 저장을 쓰는 입력의 결과다.
표의 기준 엔진은 OOS 통합 전 revision이고, 비교 엔진은 분석 당시 PR #7990의 OOS revision이다.
정확한 커밋과 환경은 [부록 A](#부록-a-비교한-revision과-측정-환경)에 있다.

아래 표는 모두 작업 전용 DB 파일의 OS cache 해제를 요청한 조건에서 얻은 엔진별 3회 중앙값이다.
OS cache는 운영체제가 파일 내용을 메모리에 보관해 다음 읽기에 재사용하는 기능이다.
해제 요청과 확인 방법은 다음 절에서 설명한다.

| 실제 SQL이 하는 일 | 기준 엔진 | OOS 엔진 | 이 결과가 뜻하는 것 |
| --- | ---: | ---: | --- |
| 작은 컬럼만 집계하는 Q1 | 1.88초 | 0.82초 | 큰 값을 건너뛰고 작은 heap을 읽는 이득이 있다. |
| 큰 컬럼 하나의 전체 내용을 비교하는 Q4 | 2.38초 | 5.72초 | 큰 값이 필요하면 약 2.4배 오래 기다린 경우가 있다. |
| 모든 컬럼의 내용을 읽어 checksum을 구하는 Q5 | 3.46초 | 4.12초 | 큰 값을 여러 개 읽는 경우도 따로 평가해야 한다. |

Q1은 작은 컬럼 `id`의 `SUM(id)`를 구한다. Q4는 큰 컬럼 `cold_1`의 전체 바이트를 원본과 비교해 일치하는 행 수를 센다. 값의 길이만 확인하는 조회가 아니다.
Q5도 큰 값의 실제 내용을 읽는다. 이 두 측정은 큰 결과 전체를 클라이언트에 전송하는 `SELECT *`의 시간과 구분한다.

느려진 Q4에서 OOS의 엔진 읽기 횟수는 기준보다 적었고 CPU 시간도 약간 짧았다.
따라서 CPU 계산량이나 읽기 횟수가 늘어서 느려졌다는 설명으로는 이 결과를 설명할 수 없다.
읽기 순서와 요청 방식의 영향을 더 살펴볼 이유가 여기 있다. 다만 장치 내부 cache, 요청 대기열, SSD 동작이 각각 얼마만큼 기여했는지까지 분리한 것은 아니다.
전체 SQL 표와 CPU·읽기 지표는 [부록 B](#부록-b-실제-sql-재측정-전체-결과)에 있다.

### cache 조건이 달라지면 결과도 달라진다

다음 세 조건을 같은 뜻으로 사용하면 안 된다.

| 조건 | 실제로 한 일 | 해석할 때 남는 조건 |
| --- | --- | --- |
| 작업 파일 캐시 해제 요청 | 서버를 정지한 뒤 작업 전용 DB 파일의 OS cache 해제를 요청하고 남은 양을 확인했다. | 전역 cache나 장치 내부 cache까지 초기화한 것은 아니다. |
| 단순 DB 재시작, restart-only | DB 서버를 다시 시작했다. | OS cache는 남을 수 있다. 실제 읽기와 cache hit가 섞일 수 있다. |
| 반복 조회, warm | 표본마다 서버를 시작하고 같은 SQL을 한 번 실행한 뒤 측정했다. | DB 전체가 메모리에 들어갔다는 뜻은 아니다. |

같은 overflow 입력의 Q4도 warm에서는 기준 1.23초, OOS 1.00초였다.
파일 캐시 해제 요청 조건과 결과의 방향이 반대다. 단순 재시작 조건의 OOS Q4는 1.48~4.08초 범위로 흔들렸다.
따라서 "OOS의 큰 값 조회는 항상 느리다"거나 "cache가 있으면 언제나 빠르다"는 결론을 내리지 않는다.
이번에 확인한 것은 명시한 입력·호스트·cache 조건에서의 이득과 비용이다.

## 읽기 요청만 따로 재생한 이유

실제 SQL 시간에는 행의 가시성 판단, 조건 평가, 값 해석 등 엔진의 여러 일이 함께 들어 있다.
읽는 순서와 요청 방식을 바꾼 영향만 비교하려고, 실행 중 기록한 파일 읽기 요청을 서버가 정지한 상태에서 다시 실행했다.
이것이 엔진 밖 읽기 재생, 즉 offline replay다. 실제 SQL을 돌리는 측정은 native SQL 실측이라고 부른다.

재생 도구는 기록에 있는 파일과 위치를 `os.pread`로 읽는다. 읽을 페이지를 주소순으로 정렬하거나 여러 요청을 합쳐,
원래 순서와 시간이 어떻게 달라지는지 비교한다. 이 도구는 SQL도, 새 OOS 엔진도 실행하지 않는다.
재생 시간과 실제 SQL 시간을 서로 빼서 엔진 내부 비용을 계산할 수도 없다.

### 한 번에 모을 범위를 제한했다

실제 엔진은 아직 방문하지 않은 행의 OOS 주소를 전부 알지 못한다.
전체 실행이 끝난 뒤 모든 주소를 정렬하는 대조는 이 제약을 무시한다.
그래서 이번에는 요청을 일정 범위로 나누고 각 범위 안에서만 순서를 바꾸는 모델도 시험했다.
이 한 번에 모으는 범위를 window, 모은 읽기 요청의 묶음을 batch라고 부른다.

대표 모델은 heap 페이지 읽기 64개를 기준으로 기록을 나눈다.
각 구간에서 OOS 이외의 읽기를 원래 순서로 먼저 실행한 뒤, 그 구간의 OOS 요청을 주소순으로 읽는다.
이 모델을 아래에서는 64 heap-page batch라고 부른다.
이는 행을 모으는 구현의 가능성을 살피는 모델이며, 실제 엔진의 64페이지 scan이나 일정 행 수 batch를 구현했다는 뜻이 아니다.

재생 도구는 제한된 구간 안에서도 앞으로 읽을 주소를 기록에서 미리 알고 있다.
실제 엔진에서 그 주소를 모으는 비용, 아직 보이지 않는 행을 걸러내는 비용, 필요한 값인지 판단하는 비용은 수행하지 않는다.
한 값이 여러 조각으로 나뉘면 앞 조각을 읽어야 다음 주소를 알 수 있다는 제약도 엔진 구현에서 다뤄야 한다.
이번 Q4의 큰 값은 한 조각에 들어가므로 여러 조각의 성능까지 측정한 결과는 아니다.

### 순서 변경과 요청 병합은 효과가 달랐다

인접 요청 병합은 바로 이어지는 파일 구간의 읽기를 한 요청으로 합치는 방법이다.
원래 읽을 페이지와 바이트는 유지한다. gap 읽기는 요청 사이의 빈 구간까지 함께 읽어 더 큰 요청으로 합치는 방법이다.
여기서 빈 구간은 원래 요청 목록에 없던 구간이라는 뜻이며, gap 읽기는 추가 I/O를 만든다.

아래 수치는 모두 OOS 읽기 재생의 3회 중앙값이다. 실제 SQL 시간과 구분한다.

| 재생 방식 | 재생 시간 | 원래 순서와 비교해 달라진 점 |
| --- | ---: | --- |
| 원래 요청 순서 | 4.413초 | 비교 기준이다. |
| 64 heap-page batch에서 정렬만 수행 | 3.449초 | 같은 요청 바이트를 읽고 약 21.8% 짧아졌다. |
| 같은 batch에서 인접 요청까지 병합 | 3.974초 | 요청 수는 줄었지만 정렬만 한 경우보다 느렸다. |
| 같은 batch에서 gap까지 읽어 병합 | 1.965초 | 약 55.5% 짧아졌지만 요청 바이트가 72.4% 늘었다. |

제한된 범위에서도 순서 변경을 검토할 근거는 남았다.
하지만 요청 수를 줄이면 항상 빨라진다고 볼 수는 없다. 연속된 짧은 OOS 요청 구간만 묶었을 때는 4.409초로,
원래 순서의 4.413초와 비슷했다. 수집 범위와 묶는 방식이 효과를 바꾼다.

gap 읽기는 빠른 수치와 함께 추가 읽기 비용을 평가해야 한다.
64 heap-page 모델에서는 원래 필요 없던 페이지 읽기 96,602회를 추가했다.
이 값을 제품 정책으로 채택하려면 추가 I/O가 다른 작업에 주는 영향까지 엔진에서 확인해야 한다.
모든 재생 모델의 요청량과 OS 읽기량은 [부록 C](#부록-c-읽기-재생-모델과-전체-결과)에 있다.

## 이번 결과로 결정할 수 있는 것과 남은 일

현재 엔진은 한 행에서 필요한 여러 OOS 속성을 모으고, 같은 시작 페이지를 쓰는 요청의 중복 페이지 확보를 줄인다.
여러 행을 모아 읽는 순서를 바꾸거나 연속 파일 I/O를 발행하는 기능은 아니다.
따라서 기존의 다중 속성 읽기 함수로 호출만 바꿔서는 Q4의 여러 행 읽기가 batch I/O로 바뀌지 않는다.

이번 결과는 제한된 요청 수집과 순서 변경을 엔진 안에서 검증할 근거다.
실제 구현에서는 같은 snapshot에서 보이는 행과 그 행의 참조를 사용해야 한다.
또한 다음 행으로 넘어간 뒤에도 수집한 참조와 결과가 유효해야 한다. 필요 없는 속성을 강제로 Resolve해 오류 발생 시점이나 값 공개 순서를 바꾸지 않아야 한다.
이런 정확성·동시성·값 수명 조건을 지킨 뒤 실제 SQL의 시간과 비용을 비교해야 한다.

재생 도구에서 읽은 묶음의 크기를 엔진의 메모리 사용량으로, 첫 묶음의 I/O 시간을 실제 첫 행 반환 시간으로 해석하지 않는다.
새 엔진 구현의 첫 결과 지연과 최대 메모리 사용량은 아직 측정하지 않았다.
해당 수치와 제한은 [부록 C](#부록-c-읽기-재생-모델과-전체-결과)에 설명한다.

다음 작업의 순서와 후보 비교는 [구현·검증 계획](CBRD-27791-oos-batch-read-plan_dcbf09e_codex.md)을 따른다.
이번 문서는 기존 [전체 실측](../CBRD-27788/CBRD-27788-oos-select-performance_dcbf09e_codex.md)과
[읽기 패턴 진단](../CBRD-27788/CBRD-27788-oos-cold-read-diagnosis_dcbf09e_codex.md)을 독립적으로 검토하고 재측정한 기록이다.
새 알고리즘·제품 기본값·성능 합격 기준을 확정한 문서는 아니다.

## 부록 A. 비교한 revision과 측정 환경

| 역할 | CUBRID/cubrid full SHA |
| --- | --- |
| base | `4781495f01523a3ecc5891e3377ad62cf876a1cd` |
| OOS / 재조회한 PR #7990 head | `dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67` |

두 revision을 각각 보존한 detached checkout과 독립 설치·DB를 사용했다. 추적 중인 소스 변경이 없고, 서버·CSQL·libcubrid의 hash와 원래 설정의 바이트가 일치하는지 확인했다.
측정 작업을 시작한 checkout은 `feature/oos-merge`의 `1a8cbefa4`다. 여기에는 별도 CPU 개선과 실험 도구가 포함돼 있으므로 이 checkout을 측정 엔진으로 사용했다고 표현하지 않는다.
새 엔진 수정·빌드·DB 재적재·배치 변경은 하지 않았다.

GCC 11.5.0, RelWithDebInfo, `-O2 -ggdb3 -DNDEBUG -finline-functions`, 테스트 계측 없음 조건을 유지했다.
DB/log page 16KiB, DB buffer 512MiB, query cache 0, `data_file_os_advise=0`이다.
Linux 5.14 EL9 backport 커널, XFS/NVMe의 공유 호스트다. 서버는 CPU 16~19, CSQL은 12, 관측 도구는 13, 재생 도구는 16에 고정했다.
각 SQL 표본에서 소스·CSQL·로드된 DSO의 일치, 정답과 직렬 TABLE SCAN 실행을 검사했다.

입력은 각각 100,000행인 heap/overflow 두 저장 형태다. 이 구분은 기준 엔진에서 일반 heap에 들어가는 입력과 overflow 경로를 사용하는 입력을 뜻한다. [fixture.sql](fixture.sql)은 최초 측정 입력과 byte 단위로 같다.
기준 heap 입력 평균 record 길이는 14,480B, overflow는 22,016B다.
OOS heap의 평균 행 길이는 각각 4,012B/4,040B이며 큰 값은 속성별 chain에 있다.
이번 Q4 입력의 큰 값은 한 chunk에 들어간다. multi-chunk의 주소 의존성은 소스로 분석했으며 새 runtime 성능 축으로 측정하지 않았다.

## 부록 B. 실제 SQL 재측정 전체 결과

각 행은 엔진별 3회 중앙값이다. Q1은 작은 컬럼 집계, Q4는 큰 컬럼 하나의 전체 내용 비교, Q5는 모든 컬럼의 내용을 읽는 checksum이다. Q4 파일 캐시 해제 행은 최초 재확인 묶음이며, 종료 재확인은 부록 F에 별도로 남겼다.
반복마다 엔진 실행 순서를 교대했다. warm은 표본마다 서버를 시작한 뒤 같은 SQL을 한 번 실행하고 측정했다.
OOS의 작은 heap 자체도 512MiB DB buffer보다 조금 크다. warm은 전체 DB가 메모리에 있는 조건을 뜻하지 않는다.

| layout / SQL | cache 조건 | base / OOS 초 | 해석 |
| --- | --- | ---: | --- |
| overflow Q4 | 작업 파일 캐시 해제 요청 | 2.38 / 5.72 | 읽기 대기 증상 재현 |
| overflow Q1 | 작업 파일 캐시 해제 요청 | 1.88 / 0.82 | 작은 컬럼 이득 유지 |
| overflow Q5 | 작업 파일 캐시 해제 요청 | 3.46 / 4.12 | 다중 큰 값은 다른 요청 집합 |
| heap Q4 | 작업 파일 캐시 해제 요청 | 1.29 / 1.73 | 일반 heap 대비 비용도 유지 |
| heap Q1 | 작업 파일 캐시 해제 요청 | 0.91 / 0.83 | engine read 감소를 장치 byte 감소로 일반화하지 않음 |
| overflow Q4 | restart-only | 1.80 / 1.50 | OOS 범위 1.48~4.08초, OS cache 상태 혼재 |
| overflow Q1 | restart-only | 1.43 / 0.37 | 첫 표본에 실제 OS 읽기가 남음 |
| overflow Q4 | warm | 1.23 / 1.00 | 파일 캐시 해제 조건과 반대 방향 |
| overflow Q1 | warm | 0.76 / 0.09 | 작은 heap의 이득 |

최초 Q4의 기준/OOS CPU task-clock은 2,333.30/2,266.97ms, instructions:u는 약 79.46/80.64억이었다.
engine ioread는 200,087/133,339회, OS read_bytes는 3,146.12/2,793.78MiB다. engine ioread는 엔진 지표이며, 부록 D의 trace에서 재구성한 파일 읽기 요청 수 200,089/133,341개와는 다른 지표다.
OOS의 약 3.34초 추가 지연은 CPU 시간이나 엔진 읽기 횟수가 늘어서 생긴 결과와 맞지 않는다.
CPU 증가가 주원인이 아니라는 기존 판정을 지지하지만, 장치 내부 cache·queue·SSD 동작의 기여율을 분리한 것은 아니다.

restart-only는 OS cache를 해제하지 않는다. 첫 실행에 읽기가 남은 사실을 숨기지 않고 중앙값과 범위를 함께 보존했다.
작업 파일 해제 조건에서는 서버가 정지한 뒤 등록된 작업 전용 permanent volume에만 `fsync`/`POSIX_FADV_DONTNEED`를 적용했다. `fincore`로 파일 내용이 OS cache에 남은 양을 확인했다.
전역 drop_caches나 장치 cache 초기화는 하지 않았다. tracer를 붙인 2개 실행의 시간은 위 표에서 제외했다.

## 부록 C. 읽기 재생 모델과 전체 결과

새 trace의 volume 읽기를 서버 정지 상태에서 `os.pread`로 재생했다. 각 조건을 3회 실행하고 순서를 반전·회전했다.
각 반복 묶음이 끝날 때 기준 엔진의 원래 순서도 재생했다. 한 번의 시스템 호출로 읽는 크기는 최대 1MiB이며 단순 정렬은 계속 16KiB 요청이다.
모든 재생 전에 정지한 작업 volume에만 cache 해제를 요청하고 남은 cache 양을 확인했다.

대조 방식은 다음과 같이 다르다.

- **request window**: 기록에서 연속된 32/128/512/2,048개 요청씩 모아 각 묶음을 정렬한다. 묶음 안에서 앞으로 읽을 주소도 미리 알고 있다.
- **heap-page batch**: 16/64개의 `PAGE_HEAP` 읽기 단위로 기록을 나눈다. 각 batch에서 OOS 이외의 읽기를 원래 순서로 먼저 실행한 뒤 OOS 요청을 주소순으로 읽는다.
- **OOS run**: 연속된 OOS 요청 구간만 정렬·인접 병합한다. 다른 종류의 읽기를 넘어 수집하지 않는다.
- **global**: 전체 요청을 사후 정렬하는 기존 대조다. 엔진이 즉시 사용할 수 있는 정책이 아니다.

heap-page batch는 요청을 모으는 구현의 가능성을 살피는 모델이다. 실제 엔진이 수행하는 행 가시성 판단, 조건 평가, buffer hit 처리, 참조와 값의 수명 관리는 실행하지 않는다. 기록을 나눈 경계가 실제 행 batch와 같다는 증거도 없다. 이 입력에서는 heap 페이지당 대략 3행이지만 이를 일반적인 행 수 상한으로 쓰지 않는다.

| OOS 재생 방식 | 초 중앙값 | 발행 요청 | 요청 MiB | OS read_bytes MiB |
| --- | ---: | ---: | ---: | ---: |
| 원래 순서 | 4.413 | 133,341 | 2,083.45 | 2,793.11 |
| OOS run만 인접 병합 | 4.409 | 133,337 | 2,083.45 | 2,793.11 |
| 32 request 정렬 | 3.014 | 133,341 | 2,083.45 | 3,198.80 |
| 128 request 정렬 | 2.707 | 133,341 | 2,083.45 | 3,194.91 |
| 512 request 정렬 | 2.069 | 133,341 | 2,083.45 | 3,353.89 |
| 2,048 request 정렬 | 1.977 | 133,341 | 2,083.45 | 3,308.58 |
| 128 request 정렬·인접 병합 | 3.258 | 101,291 | 2,083.45 | 3,068.58 |
| 512 request 정렬·인접 병합 | 2.576 | 100,645 | 2,083.45 | 3,214.58 |
| 128 request 정렬·gap 병합 | 1.652 | 6,555 | 3,564.30 | 3,644.78 |
| 512 request 정렬·gap 병합 | 1.514 | 4,372 | 3,588.94 | 3,647.83 |
| 16 heap-page batch 정렬 | 4.350 | 133,341 | 2,083.45 | 2,838.39 |
| 64 heap-page batch 정렬 | 3.449 | 133,341 | 2,083.45 | 2,946.62 |
| 64 heap-page batch·인접 병합 | 3.974 | 100,523 | 2,083.45 | 2,752.59 |
| 64 heap-page batch·gap 병합 | 1.965 | 3,921 | 3,592.86 | 3,621.56 |
| global 정렬 | 2.822 | 133,341 | 2,083.45 | 2,765.25 |
| global 정렬·인접 병합 | 1.446 | 100,522 | 2,083.45 | 3,579.64 |
| global 정렬·gap 병합 | 1.277 | 3,649 | 3,597.12 | 3,657.59 |

기준 엔진의 원래 순서 재생은 1.104초였다. 세 반복의 범위는 1.103~1.105초다.
64 heap-page 정렬은 원래 OOS 재생 대비 약 21.8% 짧고, 같은 batch의 gap 병합은 약 55.5% 짧다.
여기서 gap 읽기는 페이지 읽기 발생 횟수를 96,602회 추가하고 요청량을 72.4% 늘렸다. 같은 페이지를 여러 번 읽었다면 그 횟수도 따로 센 값이다. 원래 페이지와 횟수를 그대로 보존한 대조와 구분한다.
인접 병합은 같은 byte를 읽고 syscall 수를 줄여도 해당 bounded 조건에서는 더 느렸다.
global 정렬이 일부 request window보다 느린 것도 관측했다. offset 순서만으로 전체 kernel/device 동작을 예측하지 않는다.

정렬·인접 병합은 원래 페이지와 읽기 횟수를 정확히 보존하는지 검사했다. gap 읽기는 원래 페이지의 모든 읽기 발생을 포함하는지 검사했다.
선택한 모든 page 내용의 전체 SHA-256을 재생 전후 읽어 비교했고 양쪽 engine 모두 같았다.
검증용 추가 읽기는 timed replay 밖에서 수행했다.

### 메모리와 첫 결과 시간의 해석

64 heap-page 모델에서 최대 입력 묶음은 256개 요청/4MiB이고, 512-request window는 8MiB다.
이 크기는 묶음에서 선택한 I/O 범위다. 엔진이 동시에 보관해야 할 값의 메모리 사용량을 잰 것이 아니다. 재생 도구의 Python RSS에는 전체 기록과 횟수를 세는 Counter가 들어 있으므로 제품의 메모리 예산으로 쓰지 않는다.
64 heap-page 정렬의 첫 batch I/O는 약 11.0ms, 512-request 정렬은 약 18.9ms였다.
이 시간에는 주소 수집, 행 가시성 판단, 조건 평가, 값 해석이 빠져 있다. I/O만 본 참고값이며 실제 첫 행 반환 지연은 아니다.
전체 계획·무결성 검사 비용도 재생 시간에서 제외하고 기계 요약에 따로 기록했다.

## 부록 D. 읽기 기록과 재생 입력의 검증

읽기 요청을 기록한 strace에는 시작과 반환이 나뉜 unfinished/resumed 호출이 있다. 별도 파서로 이를 다시 한 호출로 맞췄다. 파일 기술자와 파일의 대응표인 FD map이 실행 전후에 모두 같고, volume 읽기가 요청한 바이트를 전부 반환했는지 확인했다. 쿼리를 실행한 worker의 요청을 골랐으며, 기록 순서와 `requests.tsv`가 완전히 같은지도 확인했다.
기준 200,089개/OOS 133,341개 요청을 재구성했고, 이전과 새 trace의 주소 패턴도 같다.
보존된 기존 진단 스크립트 3개의 hash는 게시된 기계 요약과 일치했다.

각 요청을 16KiB 페이지 읽기 단위로 풀어 같은 페이지를 읽은 횟수까지 비교했다. 이 읽기 발생 단위를 page occurrence라고 한다. 기존 입력에는 중복 page occurrence가 없었다. 정렬과 인접 병합은 선택된 페이지와 각 읽기 횟수, 요청 바이트를 보존했다. 이처럼 중복 횟수를 포함한 페이지 집합을 기계 요약에서는 page multiset으로 기록한다.
기존 global gap 병합은 96,875 page occurrence와 약 1,513.67MiB를 추가했다.
기존 `call_multiset_sha256`은 병합 전 입력을 일정 순서로 정리한 hash다. 따라서 병합 뒤 gap 읽기가 추가됐는지를 이 hash 하나로 증명할 수 없다.
새 결과에는 실제 발행 요청 hash, 발행 page multiset hash, 추가 page occurrence와 요청 바이트를 별도로 기록했다.

기록한 읽기 주소는 OS volume 파일 안의 바이트 위치인 offset이다. NVMe 장치가 사용하는 논리 블록 주소인 LBA를 직접 관측한 값은 아니다.

새 head trace는 `PAGE_OOS` 100,000회, `PAGE_HEAP` 33,339회와 소량의 BTREE/FTAB 읽기로 분류됐다.
분류는 정지 DB에서 각 선택 page의 file-I/O header를 읽어 수행했다.
이 revision의 `LOG_LSA` 8B와 header layout에 따라 pageid offset 8, ptype offset 14를 사용하고,
모든 pageid가 파일 offset/16KiB와 맞는지 검사했다.
[layout](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_io.h#L165)과
[page type](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/storage_common.h#L150)에 고정된 관측이다.

## 부록 E. 현재 소스의 책임과 보존할 조건

아래 표는 분석한 revision에서 각 함수가 맡는 일을 설명한다. 페이지를 메모리에 확보하는 동작을 fix,
확보를 해제하는 동작을 unfix라고 부른다. VPID는 volume과 페이지를 식별하는 주소다.
같은 페이지의 요청을 모으는 기능과 여러 행을 모으는 기능, 파일 읽기를 합치는 기능은 구분해야 한다.

| 위치 | 확인한 책임과 제약 |
| --- | --- |
| [heap_oos_read_grouped_payloads](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_oos.cpp#L734) | 한 행에서 요청한 OOS 속성이 2개 이상일 때만 원시 값을 받을 버퍼를 할당해 요청을 모은다. 도중에 실패해도 할당한 버퍼를 정리해야 한다. |
| [heap_attrinfo_read_dbvalues_with_oos_prefetch](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/heap_file.c#L11670) | OOS 속성 0/1개는 기존의 개별 읽기 경로를 사용한다. 여러 속성은 함께 Resolve한 뒤 `DB_VALUE`로 복사하고 원시 버퍼를 해제한다. |
| [oos_read_many](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L2854) | 요청에 처음 나타난 값의 시작 페이지인 head 순서로 같은 VPID를 찾아 묶는다. 전체 주소순 정렬이나 시스템 호출 병합은 수행하지 않는다. head를 unfix한 뒤 다음 조각인 continuation을 따라가므로 여러 OOS 페이지를 동시에 고정해 두지 않는다. |
| [oos_read](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/oos_file.cpp#L2793) | 값을 복사하기 전에 head 페이지의 존재·종류와 값의 slot·identity stamp·head index·길이를 검사한다. 다음 조각의 주소는 이전 조각을 읽어야 알 수 있다. |
| [scan_next_heap_scan](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/scan_manager.c#L5681) | 현재 snapshot에서 보이는 행을 가져와 조건을 평가하고 나머지 속성을 읽는다. watcher의 페이지가 바뀌면 COPY/retry한다. 여러 행의 요청을 모으려면 행과 속성 cache를 언제까지 유효하게 보관할지 정해야 한다. |
| [eval_data_filter](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/query/query_evaluator.c#L3460) | 조건 평가에서 필요해질 때 속성을 읽는다. 앞 조건으로 결과가 정해지는 short-circuit에서는 뒤 속성을 Resolve하지 않는다. batch도 모든 조건 속성을 미리 Resolve해 동작을 바꾸면 안 된다. |
| [page-buffer miss](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/page_buffer.c#L8480) | cache miss 때 페이지 관리 항목인 BCB를 예약하고 이중 쓰기 버퍼인 DWB를 확인한 뒤 한 페이지를 읽고 투명 데이터 암호화인 TDE 처리를 수행한다. 파일만 직접 크게 읽는 방식은 이 처리를 대신하지 못한다. |
| [fileio_read_pages](https://github.com/CUBRID/cubrid/blob/dcbf09e4f7fd02ff9c8fc6493ec8887fc2919d67/src/storage/file_io.c#L4221) | 파일의 연속 구간을 읽는 하위 함수다. 현재 호출자는 DWB 복구와 로그 경로다. 이 함수만으로 데이터 page buffer의 동시성·공개 규칙을 갖춘 batch 읽기를 제공하지는 않는다. |

Resolve와 Expand는 목적이 다르다. Resolve는 필요한 속성을 그때 조회하는 동작이다. Expand는 원시 행 전체를 요구하는 소비자를 위한 별도 동작이다. 일괄 Expand로 batch를 만들면 필요 없는 큰 값까지 읽게 되어 작은 컬럼 이득과 두 동작의 책임 구분을 잃는다.
`FILE_OOS`는 logical file이다. 위 offset은 physical volume 안의 위치이며 별도 OS OOS 파일을 관측한 것이 아니다.

여러 행의 요청을 모을 때도 어떤 행 버전의 참조인지 보존해야 한다. MVCC snapshot과 맞는 행을 읽고,
과거 버전이 필요하면 undo에 있는 그 버전의 참조를 사용해야 한다. 해제·재사용된 페이지나 slot을 다른 값으로 오해하지 않도록
값을 공개하기 전에 identity와 길이를 검사하는 순서도 보존한다.

또한 페이지 접근을 보호하는 latch와 heap watcher 규칙을 지켜야 한다.
heap의 `PEEK` 행, 필요할 때 읽어 두는 속성 cache, 임시 scratch buffer를 다음 행으로 이동한 뒤에도 그대로 빌려 쓸 수는 없다.
수집한 정보의 소유권과 유효 기간을 정하고, 정상 읽기 결과는 `DB_VALUE`의 유효 기간에 맞게 복사해야 한다.
도중 실패한 batch의 부분 값을 SQL 결과로 공개하지 않으며, 조건 평가·오류 발생 시점·취소·LIMIT의 동작도 검증해야 한다.
이 조건을 어떻게 검증할지는 구현 계획에서 다룬다.

## 부록 F. 재현 절차와 보존한 근거

2026-10-28 측정의 원시 근거 디렉터리는 다음이다. 앞선 실측·진단 디렉터리와 파일을 덮어쓰지 않았다.

```text
/mnt/nvme/data-5/tmp/CBRD-27791-20261028-h6a_kjx_
```

그 안의 `diagnose.py repro --name opening --repeats 3`으로 같은 지연을 다시 탐지할 수 있는 SQL 반복 측정을 실행했다. RED는 진단 도구가 증상 재현으로 표시한 결과다. 이 표시의 marker는 head wall >1.5배, CPU <1.2배, engine reads <0.8배다. 제품 합격 기준은 아니다.
종료 시 같은 명령을 `--name closing`으로 재실행해 base 2.36초/OOS 5.70초의 RED 판정을 다시 얻었다.
총 native 성능 표본은 60개, 별도 traced 실행은 2개, timed replay는 54개다.
이름 재사용을 거부하므로 재실행은 새 빈 artifact root에서 수행한다.

공유 가능한 입력은 [fixture.sql](fixture.sql), offline 도구는 [bounded_replay.py](bounded_replay.py),
선별 수치·artifact 이름·script fingerprint는 [기계 요약](selected-summary_dcbf09e.json)에 보존한다.
fixture와 명령을 다른 Linux 호스트로 옮길 때는 독립 source/install/DB와 registry·port·TMP·설정을 먼저 분리한다.
같은 source도 재적재 시 물리 배치가 달라질 수 있으므로 새 trace로 대조하며 기존 숫자의 정확한 재현을 보장하지 않는다.

```sh
# 두 exact revision을 별도 source/install로 준비한다. 아래는 build profile의 예다.
cmake -S "$SOURCE" -B "$BUILD" -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_INSTALL_PREFIX="$INSTALL" -DUNIT_TESTS=OFF -DUNIT_TEST_OOS=OFF
cmake --build "$BUILD" --parallel 4
cmake --install "$BUILD"
# 각 DB는 matching install의 createdb로 16KiB data/log page로 새로 만든다.
# data_buffer_size=512M, max_query_cache_entries=0, query_cache_size_in_pages=0을 설정한다.
csql -C -u dba -i fixture.sql "$DATABASE"
```

위 build 예는 원측정에서 재실행한 명령이 아니다. 실제 compile command·최적화·계측 상태는 기존 `builds.json`과 원측정 시작 전 점검으로 확인했다. 이번 문장 개정에서도 엔진 명령이나 측정을 재실행하지 않았다.
원측정 당시 DB가 준비된 호스트의 전체 재측정은 `remeasure.py`, trace 감사·분류는 `prepare_controls.py`, replay schedule은 `run_bounded.py`에 있다.

다른 환경에서 읽기 재생을 준비하려면 manifest와 `request-types.tsv`가 필요하다. manifest는 `source`, `install`, `volume_root`,
`volumes`의 `path/dev/ino/size`, `fd_map`, `request_types`를 포함한다. TSV는 captured fd·offset·size·ptype 4열이다.
도구는 해당 설치의 프로세스가 실행 중이거나 volume의 파일 식별 정보·소유자·허용 범위가 다르면 읽기와 cache 해제 요청을 거부한다.
정지한 전용 DB에서 자신의 trace와 manifest를 준비한 뒤 다음처럼 실행한다.

```sh
python3 -B bounded_replay.py --manifest head-manifest.json \
  --output fresh-h64-sort --policy heap-batch --window 64 --gap -1 --cpu 16
python3 -B bounded_replay.py --manifest head-manifest.json \
  --output fresh-h64-gap --policy heap-batch --window 64 --gap 16384 --cpu 16
```

실제 측정의 page type 2/14, 16KiB 크기에 고정된 도구다. 다른 source/layout에 무조건 적용하는 범용 DB runner가 아니다.
trace 재조립, 15개 작은 변형의 page multiplicity/gap 검사, 모든 timed trial의 요청 검증과 전후 전체 내용 hash를 확인했다.
inode가 다른 manifest는 cache advice 전에 거부되는 음성 검증도 확인했다.
종료 시 두 설정의 byte 복원, 바이너리 불변, source tracked clean과 해당 설치의 실행 프로세스 0개를 확인했다.
환경 점검의 root `compile_commands.json` 링크 누락 경고는 source 텍스트 탐색에 영향을 주지 않았고, build/install identity는 별도로 확인했다.
새 규범 설계의 채택, 엔진 단위·SQL·shell·medium 회귀나 회사 CI를 실행한 것으로 해석하지 않는다.
