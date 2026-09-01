# H2SU 리뷰 그림 설명 — "SA 모드에서는 회수가 전혀 안 됩니다 (볼륨 무한 증가 실측)"

> PR #7617 에 H2SU 님이 남긴 APPROVED 리뷰 (2026-08-21) 의 두 지적이 무엇이고, 왜 맞으며, 우리가 왜 "후속 티켓으로 분리" 대신 **이 PR 에서 고치는 쪽**으로 방향을 바꿨는지를 그림으로 설명한다.
> 한 줄 요약: **리뷰어가 PR 바이너리로 직접 실측해 보니, vacuum 이 있는 서버 모드는 flat 인데 vacuum 이 없는 SA 모드는 delete+재삽입마다 볼륨이 계속 자랐다 (320→1024MB). 원인은 "회수 주체가 vacuum 후보 경로 하나뿐" 인 설계 — 그래서 어떤 삭제 경로든 놓친 빈 페이지를 파일이 커지려는 순간 되찾는 '성장 게이트 sweep' 을 이 PR 에 추가했고, 같은 절차로 재측정해 SA 도 flat (321MB ×4) 임을 확인했다.**

## 0. 리뷰어의 실측 — 숫자가 말하는 것

동일 바이너리 (`66cd3cc` debug) · 동일 워크로드 (비압축 15KB 값 14,000행 delete→재삽입 반복). 유일한 차이는 SA vs 서버 모드:

<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="h2svg1-title">
  <title id="h2svg1-title">H2SU 실측: 서버 모드는 320MB flat, SA 모드는 매 사이클 증가해 1024MB</title>
  <text x="20" y="26" fill="currentColor" font-size="14" font-weight="bold">사이클별 물리 볼륨 크기 (du, MB) — H2SU 실측</text>
  <path d="M60 250 H730" stroke="currentColor"/>
  <path d="M60 250 V40" stroke="currentColor"/>
  <text x="46" y="254" text-anchor="end" fill="currentColor" font-size="11">0</text>
  <path d="M56 186 h4" stroke="currentColor"/>
  <text x="46" y="190" text-anchor="end" fill="currentColor" font-size="11">320</text>
  <path d="M56 122 h4" stroke="currentColor"/>
  <text x="46" y="126" text-anchor="end" fill="currentColor" font-size="11">640</text>
  <path d="M56 58 h4" stroke="currentColor"/>
  <text x="46" y="62" text-anchor="end" fill="currentColor" font-size="11">960</text>
  <rect x="90" y="186" width="40" height="64" fill="#e2574c" fill-opacity="0.45"/>
  <rect x="135" y="186" width="40" height="64" fill="#4a90d9" fill-opacity="0.45"/>
  <text x="132" y="272" text-anchor="middle" fill="currentColor" font-size="11">최초 로드</text>
  <rect x="250" y="122" width="40" height="128" fill="#e2574c" fill-opacity="0.45"/>
  <rect x="295" y="186" width="40" height="64" fill="#4a90d9" fill-opacity="0.45"/>
  <text x="292" y="272" text-anchor="middle" fill="currentColor" font-size="11">삭제+재삽입 ×1</text>
  <rect x="410" y="96" width="40" height="154" fill="#e2574c" fill-opacity="0.45"/>
  <rect x="455" y="186" width="40" height="64" fill="#4a90d9" fill-opacity="0.45"/>
  <text x="452" y="272" text-anchor="middle" fill="currentColor" font-size="11">삭제+재삽입 ×2</text>
  <rect x="570" y="45" width="40" height="205" fill="#e2574c" fill-opacity="0.45"/>
  <rect x="615" y="186" width="40" height="64" fill="#4a90d9" fill-opacity="0.45"/>
  <text x="612" y="272" text-anchor="middle" fill="currentColor" font-size="11">삭제+재삽입 ×3</text>
  <rect x="80" y="288" width="14" height="10" fill="#e2574c" fill-opacity="0.45"/>
  <text x="100" y="297" fill="currentColor" font-size="12">SA 모드 (320→640→768→1024, 계속 증가)</text>
  <rect x="430" y="288" width="14" height="10" fill="#4a90d9" fill-opacity="0.45"/>
  <text x="450" y="297" fill="currentColor" font-size="12">서버 모드 (vacuum 회수, 320 flat)</text>
</svg>

같은 데이터를 지웠다 다시 넣기만 하는데 SA 는 매번 볼륨이 자란다 — 회수가 안 되고 있다는 직접 증거다.

## 1. 왜 SA 에서만 새나? — 회수 주체가 하나뿐이었다

이 PR (원래 범위) 의 회수는 **vacuum 이 삭제하면서 모은 후보 목록**에서 출발한다. 그런데:

- SA 모드에는 vacuum daemon 이 없다 — eager 경로 (`heap_oos_delete_unreferenced`) 가 청크를 지우지만, 후보 수집도 회수도 하지 않는다 (당시엔 "살아 있는 트랜잭션 안이라 회수 불가" 로 주석에 스코프 제외를 명시했었다).
- 서버 모드에서도 **MVCC 비활성 클래스 (카탈로그)** 의 삭제는 같은 eager 경로라 회수가 없다.

"그래도 bestspace 힌트로 재사용되지 않나?" — 여기가 핵심이다. 힌트 저장소는 용량이 작다:

<svg viewBox="0 0 760 250" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="h2svg2-title">
  <title id="h2svg2-title">14,000개의 빈 페이지 대비 힌트 저장소 용량이 턱없이 작아 대부분을 잊는 구조</title>
  <rect x="20" y="40" width="330" height="170" rx="10" fill="#e2a144" fill-opacity="0.12" stroke="currentColor"/>
  <text x="185" y="66" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">삭제가 만든 빈 페이지: ~14,000개</text>
  <text x="185" y="88" text-anchor="middle" fill="currentColor" font-size="12">(15KB 값 = 페이지당 1개꼴이라 행 수만큼)</text>
  <text x="185" y="130" text-anchor="middle" fill="currentColor" font-size="26">▦ ▦ ▦ ▦ ▦ ▦ ▦ ▦</text>
  <text x="185" y="162" text-anchor="middle" fill="currentColor" font-size="26">▦ ▦ ▦ ▦ ▦ ▦ …</text>
  <path d="M354 125 H420" stroke="currentColor" stroke-width="2"/>
  <path d="M420 125 l-9 -5 v10 z" fill="currentColor"/>
  <rect x="424" y="40" width="316" height="76" rx="10" fill="#4a90d9" fill-opacity="0.15" stroke="currentColor"/>
  <text x="582" y="64" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">힌트 저장소 (전부 메모리·소용량)</text>
  <text x="582" y="86" text-anchor="middle" fill="currentColor" font-size="12">해시 캐시 상한 1,000 · 헤더 best[10]</text>
  <text x="582" y="105" text-anchor="middle" fill="currentColor" font-size="12">재시작하면 소멸</text>
  <rect x="424" y="134" width="316" height="76" rx="10" fill="#e2574c" fill-opacity="0.15" stroke="currentColor"/>
  <text x="582" y="158" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">기억 못 한 ~13,000개 페이지</text>
  <text x="582" y="180" text-anchor="middle" fill="currentColor" font-size="12">재삽입이 캐시 미스 → file_alloc 이 파일 확장</text>
  <text x="582" y="199" text-anchor="middle" fill="currentColor" font-size="12">빈 페이지는 그대로 남음 = 볼륨 증가</text>
  <text x="380" y="238" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">"한 번 잊힌 빈 페이지를 다시 찾아 주는 주체" 가 없었다 — 이것이 진짜 구멍</text>
</svg>

즉 H2SU 의 지적은 단순 "SA 미지원" 이 아니라, **회수가 후보 목록이라는 운에 의존하는 한 보장이 아니다** 라는 구조 비판으로 읽어야 한다.

## 2. 우리의 답 — 후속 분리 대신 이 PR 에서 수정: 성장 게이트 sweep

처음 계획은 "스코프 제외로 문서화돼 있으니 후속 티켓 분리" 답글이었다. 그러나 위 구조 비판을 받아들여, **어떤 삭제 경로든 (vacuum 이든 eager 든) 놓친 빈 페이지를 되찾는 backstop** 을 이 PR 에 넣었다 (`132163dab`). 아이디어는 단순하다:

> **파일이 커지려는 바로 그 순간이, 빈 페이지를 찾아볼 가장 좋은 순간이다.**

<svg viewBox="0 0 760 330" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="h2svg3-title">
  <title id="h2svg3-title">성장 게이트 sweep: 새 페이지를 할당하기 전에 카운터를 보고, sector bitmap 을 커서부터 훑어 첫 빈 페이지를 회수해 재사용</title>
  <rect x="20" y="30" width="220" height="52" rx="10" fill="#4a90d9" fill-opacity="0.15" stroke="currentColor"/>
  <text x="130" y="52" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">INSERT: 빈자리가 없네,</text>
  <text x="130" y="71" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">새 페이지 할당해야겠다</text>
  <path d="M130 86 V120" stroke="currentColor" stroke-width="2"/>
  <path d="M130 120 l-5 -9 h10 z" fill="currentColor"/>
  <rect x="20" y="124" width="220" height="56" rx="10" fill="#e2a144" fill-opacity="0.2" stroke="currentColor" stroke-width="2"/>
  <text x="130" y="147" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">성장 게이트 (단일 관문)</text>
  <text x="130" y="168" text-anchor="middle" fill="currentColor" font-size="12">미회수 삭제 카운터 &gt; 0 인가?</text>
  <path d="M244 152 H320" stroke="currentColor" stroke-width="2"/>
  <path d="M320 152 l-9 -5 v10 z" fill="currentColor"/>
  <text x="282" y="143" text-anchor="middle" fill="currentColor" font-size="11">예</text>
  <rect x="324" y="110" width="240" height="84" rx="10" fill="#3d9970" fill-opacity="0.15" stroke="currentColor" stroke-width="2"/>
  <text x="444" y="134" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">sweep: sector bitmap 을</text>
  <text x="444" y="154" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">커서 위치부터 순회</text>
  <text x="444" y="176" text-anchor="middle" fill="currentColor" font-size="12">첫 빈 페이지 발견 → 회수 → 즉시 중단</text>
  <path d="M568 152 H640" stroke="currentColor" stroke-width="2"/>
  <path d="M640 152 l-9 -5 v10 z" fill="currentColor"/>
  <rect x="644" y="124" width="100" height="56" rx="10" fill="#4a90d9" fill-opacity="0.15" stroke="currentColor"/>
  <text x="694" y="147" text-anchor="middle" fill="currentColor" font-size="12">그 페이지를</text>
  <text x="694" y="166" text-anchor="middle" fill="currentColor" font-size="12">재사용 (성장 0)</text>
  <path d="M130 184 V240" stroke="currentColor" stroke-dasharray="5 4" stroke-width="2"/>
  <path d="M130 240 l-5 -9 h10 z" fill="currentColor"/>
  <text x="70" y="215" fill="currentColor" font-size="11">아니오 (순수 insert)</text>
  <rect x="20" y="244" width="220" height="48" rx="10" fill="none" stroke="currentColor" stroke-dasharray="5 4"/>
  <text x="130" y="264" text-anchor="middle" fill="currentColor" font-size="12">sweep 없이 바로 새 페이지 할당</text>
  <text x="130" y="282" text-anchor="middle" fill="currentColor" font-size="12">(적재 성능 회귀 없음)</text>
  <text x="390" y="230" fill="currentColor" font-size="12" font-weight="bold">진실은 디스크에 있다: bitmap + "페이지가 비었나" 는</text>
  <text x="390" y="250" fill="currentColor" font-size="12" font-weight="bold">디스크가 알고 있으므로, 카운터·커서를 잃어도</text>
  <text x="390" y="270" fill="currentColor" font-size="12" font-weight="bold">페이지는 절대 잃지 않는다 (재시작 시 boot rule 이 1회 무조건 sweep)</text>
</svg>

설계 포인트 세 가지:

| 포인트 | 내용 | 이유 |
|---|---|---|
| **카운터는 힌트** | `oos_delete` 가 체인 하나 지울 때마다 per-파일 카운터 +1 (메모리 전용) | 게이트는 0/비0 만 판정 — 틀려도 (abort 등) 헛 스캔 1바퀴가 최대 비용 |
| **incremental (커서)** | sweep 은 첫 회수 성공에서 멈추고 커서를 저장, 다음 성장이 이어감 | 삭제 burst 의 회수 비용이 "혜택 받는 insert 들"에 잘게 분산 — 한 insert 가 폭탄을 맞지 않음 |
| **boot rule** | 재시작으로 카운터·커서가 사라진 파일은 첫 성장 때 무조건 1바퀴 sweep | 힌트 유실의 대가가 "페이지 손실"이 아니라 "스캔 1바퀴"가 되도록 |

이 backstop 은 삭제의 출처를 가리지 않는다 — vacuum 이 놓친 것, eager/SA 가 지운 것, 에러로 버려진 후보, **이 PR 이전부터 쌓여 있던 부채**까지 전부 "파일이 커지기 전에" 회수된다. 그래서 SA/서버 분기 코드가 하나도 없다.

## 3. 재측정 — 리뷰어의 절차 그대로

H2SU 절차 (비압축 15KB × 14,000행, delete+재삽입 ×3, `du` 데이터 볼륨) 재현:

| 라운드 | AS-IS SA (H2SU 실측) | TO-BE SA | TO-BE 서버 (vacuum 정착 후) |
|---|---|---|---|
| 최초 로드 | 320MB | 321MB | 321MB |
| ×1 | 640MB | **321MB** | **321MB** |
| ×2 | 768MB | **321MB** | **321MB** |
| ×3 | 1024MB | **321MB** | **321MB** |

- 무결성: 매 라운드 `COUNT(*)` = 14,000, 최종 값 등치 검사 14,000.
- 서버에서 vacuum daemon 이 삭제 블록을 다 소비하기 전에 재삽입을 시작하면 (경주), 그 구간만큼만 유계 성장 후 flat — 아직 커밋/소비되지 않은 삭제의 페이지를 회수하지 않는 것은 LSA 게이트의 **의도된 보수성**이다 (안전이 먼저).

## 4. 두 번째 지적 — 관측성 (spacedb/diagdb)

`cubrid spacedb` / `diagdb` 가 OOS 공간을 표시하지 못해, 이런 누수가 나도 DBA 가 표준 도구로 진단할 수 없다는 부수 지적. **맞지만 이 PR 이 만든 문제가 아니고**, 기존 티켓 **CBRD-26871** 이 추적 중이다. 다만 "회수가 실제로 일어났는지" 를 릴리스 빌드에서 검증할 수단이 그 티켓에 달려 있으므로, 우선순위 상향 의견에 동의하고 JIRA 에 남기기로 했다.

## 5. 답글이 왜 이 내용인가

| H2SU 지적 | 답글의 대응 |
|---|---|
| SA 볼륨 무한 증가 (실측) | "후속 분리" 를 철회하고 **이 PR 에서 수정** — 성장 게이트 sweep (`132163dab`) 소개 + 동작 원리 요약 |
| 실측 절차의 가치 | 그 절차를 그대로 A/C 재측정에 채택했음을 표로 제시 (AS-IS/TO-BE 대비) |
| 서버 모드 검증 | vacuum 정착 후 flat + 경주 시 유계 수렴의 이유 (LSA 게이트 보수성) 를 정직하게 명시 |
| spacedb/diagdb 관측성 | CBRD-26871 이 티켓 오브 레코드, 우선순위 상향 동의 |

특히 첫 줄에서 "처음엔 후속 분리로 답하려 했다"고 밝히는 것은 일부러다 — 리뷰가 설계를 바꿨음을 인정하는 것이 리뷰어의 실측 노력에 대한 가장 정확한 감사 표현이기 때문이다.
