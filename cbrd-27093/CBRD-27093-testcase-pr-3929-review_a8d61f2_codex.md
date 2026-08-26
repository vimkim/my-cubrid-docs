# CBRD-27093 테스트케이스 PR #3929 검토

- 검토 대상: <https://github.com/CUBRID/cubrid-testcases-private-ex/pull/3929>
- 테스트케이스 HEAD: `a8d61f27443e3c8b56bcaf94b23a8b88dff9069a`
- 관련 엔진 수정: `85b6b5743d8cd93e56542de1858b4e507e2a5f21`
- 검토일: 2026-08-26

## 한 줄 결론

이 테스트는 **알려진 수정 전 빌드와 수정 후 빌드를 실제로 구분한다.** 그러나 현재
구조로는 관찰한 `fsync`가 명시적 `;checkpoint` 때문에 실행되었다고 확정할 수
없으므로, **CBRD-27093의 checkpoint 계약을 충분히 검증하는 테스트라고 보기는
어렵다.**

즉, 방향은 맞지만 합치기 전에 관찰 범위를 checkpoint 하나로 좁히는 보완이
필요하다.

## 무엇을 확인하려는 테스트인가

CBRD-27093은 `double_write_buffer_size=0`, 즉 DWB를 끈 서버에서 checkpoint가
영구 데이터 볼륨을 `fsync`하지 않던 문제다.

정상 동작은 다음과 같다.

```text
데이터 변경
  → checkpoint 시작
  → 영구 데이터 볼륨 fsync 성공
  → checkpoint 완료 및 복구 시작점 전진
```

PR #3929의 테스트는 서버에 `strace`를 붙여 `fsync`/`fdatasync` 호출을 기록하고,
영구 데이터 볼륨 경로가 한 번 이상 나타나면 통과시킨다.

## 좋은 점

1. SQL 결과만 보는 대신 실제 시스템 호출을 관찰한다. 이 버그의 본질과 맞는
   검증 방법이다.
2. DWB를 끈 bug case와 기본 DWB 설정의 control case를 모두 둔다.
3. 추적 결과가 완전히 비어 있을 때 별도 오류로 처리한다.
4. QA 장비에 `strace`가 없을 가능성을 고려해 정적 바이너리를 포함하고 SHA-256을
   검사한다. 실제 파일은 스크립트의 SHA-256과 일치했으며, 정적 PIE x86-64
   `strace 6.3` 바이너리임을 확인했다.
5. 로컬 실행에서 알려진 수정 전/후 빌드를 다음과 같이 구분했다.

| 실행 대상 | DWB off case1 | DWB on case2 | 전체 결과 |
|---|---:|---:|---|
| 수정 전 `4cfc8370e` | 0회 | 2회 | NOK |
| 수정 적용 설치본 | 19회 | 2회 | OK |

따라서 이 테스트는 현재 알려진 CBRD-27093 수정에 대한 **회귀 감지 능력**은 있다.

## 핵심 문제: checkpoint만 촬영하지 않는다

현재 테스트는 `strace`를 먼저 시작한 뒤 대량 INSERT를 실행하고, 그 다음에
명시적 `;checkpoint`를 실행한다. 자동 checkpoint도 비활성화하지 않는다.

이를 CCTV에 비유하면 다음과 같다.

```text
현재 추적 구간

카메라 ON ── 대량 INSERT ── 자동/백그라운드 동작 ── ;checkpoint ── 카메라 OFF
             └──────── 이 전체 구간의 fsync를 모두 합산 ────────┘
```

테스트가 정말 증명해야 하는 구간은 다음과 같다.

```text
필요한 추적 구간

대량 INSERT 완료 ── 카메라 ON ── ;checkpoint ── 카메라 OFF
                                  └─ 이 구간만 판정
```

현재 방식에서는 INSERT 중 실행된 동기화, 자동 checkpoint, 다른 백그라운드 경로의
동기화도 모두 같은 숫자에 포함된다. 따라서 향후 명시적 checkpoint 경로가 다시
고장 나더라도 다른 경로가 데이터 볼륨을 한 번 동기화하면 테스트가 통과할 수 있다.

수정 적용 실행에서 case1이 19회를 기록한 것도 추적 구간이 명시적 checkpoint보다
훨씬 넓다는 사실을 보여 준다. 기존의 checkpoint 격리 실험에서는 수정 후 영구
base 볼륨 동기화가 4회 관찰되었다.

## 추가로 놓칠 수 있는 오류

### 1. DWB가 실제로 꺼졌는지 확인하지 않는다

설정 변경 명령이 실패해도 테스트는 계속된다. 이 경우 수정 전 빌드에서도 이미
정상인 DWB 활성 경로를 실행하여 잘못 통과할 수 있다.

서버 기동 후 `cubrid paramdump`로 유효한 `double_write_buffer_size=0`을 확인하고,
DWB 파일이 생성되지 않았음도 확인하는 편이 안전하다.

### 2. INSERT와 checkpoint 실패를 무시한다

두 `csql` 명령의 종료 상태와 출력이 버려진다. 명시적 checkpoint가 실패해도 그
전에 다른 경로에서 `fsync`가 한 번 기록되었다면 테스트가 통과할 수 있다.

### 3. 실패한 fsync도 성공으로 센다

현재 판정은 경로만 추출하므로 다음 호출도 1회로 계산한다.

```text
fsync(10</path/to/db>) = -1 EIO (Input/output error)
```

이슈의 요구사항은 `fsync`를 **시도**하는 것이 아니라 영구 볼륨 동기화를
**성공**시키는 것이다. 따라서 syscall 반환값이 성공인 행만 계산해야 한다.

### 4. tracer 준비 확인이 충분하지 않다

서버에는 많은 thread가 있지만 현재 대기는 첫 `attached` 문자열이 나타나면 끝난다.
시간 제한까지 준비가 확인되지 않아도 `strace` 프로세스가 살아 있으면 테스트를
계속한다. checkpoint를 실행하는 thread가 아직 attach되지 않았다면 잘못 실패할 수
있다.

### 5. 빈 trace 판정 기준이 너무 넓다

현재는 어떤 파일이든 sync 호출 하나만 있으면 tracer가 정상이라고 본다. 원래
검증 계획처럼 active log의 성공한 sync를 trace-health anchor로 함께 확인해야
데이터 볼륨 경로 해석 실패와 제품 결함을 구분할 수 있다.

## 권장 수정 순서

1. DWB off case에서 자동 checkpoint 조건을 비활성화한다.
2. DB를 시작한 뒤 유효 파라미터가 `double_write_buffer_size=0`인지 확인한다.
3. DWB 파일이 없음을 확인한다.
4. 대량 INSERT를 완료하고 성공 여부를 확인한다.
5. 그 다음 `strace`를 attach하고, 필요한 server thread가 추적되는 상태인지
   확인한다.
6. 추적 구간에서는 명시적 `;checkpoint`만 실행하고 성공 여부를 확인한다.
7. 정확한 영구 base 볼륨 경로에 대한 **성공한** `fsync`/`fdatasync`가 1회
   이상인지 검사한다.
8. active log의 성공한 sync도 1회 이상인지 검사하여 trace가 유효함을 확인한다.

판정 흐름은 다음처럼 단순하게 만들 수 있다.

```text
DWB=0 확인
  → workload 성공
  → tracer 준비 확인
  → explicit checkpoint 성공
  → active log sync 성공 확인
  → permanent base volume sync 성공 확인
  → OK
```

## 최종 판단

PR #3929는 CBRD-27093을 겨냥한 올바른 관찰 방법을 사용하고, 실제 수정 전/후도
구분한다. 따라서 버릴 테스트는 아니다.

다만 현재 결과가 말해 주는 것은 “추적 중 어느 경로에선가 데이터 볼륨 sync가
발생했다”까지다. “명시적 checkpoint가 데이터 볼륨 sync를 성공시켰다”를 말하려면
위 보완이 필요하다. **현재 상태는 부분 검증이며, checkpoint 격리와 오류 검사를
추가한 뒤 충분한 회귀 테스트가 된다.**
