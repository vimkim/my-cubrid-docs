# R4 그림 설명 — "비어 있지 않은 후보에도 배타 latch 비용을 전부 지불합니다" (InChiJun 코멘트 #2)

> PR #7617 리뷰 코멘트 R4 가 무엇을 지적했고, 왜 맞는 지적이며, 커밋 `50c18b7de` (2단계 판정 + per-file 검사 hoisting) 가 어떻게 고쳤는지를 그림으로 설명한다.
> 한 줄 요약: **회수 후보의 대다수는 "아직 안 빈" 페이지인데, 예전 코드는 그들에게도 가장 비싼 자물쇠 (모든 INSERT 의 관문인 OOS 통계 헤더) 를 먼저 잡고 나서야 "비었나?" 를 물었다 → 순서를 뒤집어, 싼 검사로 먼저 거르고 진짜 빈 페이지만 비싼 자물쇠를 잡게 했다.**

## 0. 후보 목록의 성질: 대다수는 "안 빈" 페이지다

회수 후보 목록 (`touched_vpids`) 에는 "청크가 **하나라도** 삭제된 페이지" 가 전부 들어온다. 한 페이지에 값 여러 개가 사는 게 보통이므로, 청크 하나가 지워져도 페이지는 대개 아직 차 있다. 즉:

<svg viewBox="0 0 760 200" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="r4svg1-title">
  <title id="r4svg1-title">후보 10개 중 실제로 빈 페이지는 소수라는 그림</title>
  <text x="20" y="30" fill="currentColor" font-size="14" font-weight="bold">회수 후보 목록 (청크가 지워진 페이지들)</text>
  <rect x="20" y="50" width="60" height="60" rx="6" fill="#4a90d9" fill-opacity="0.25" stroke="currentColor"/>
  <text x="50" y="85" text-anchor="middle" fill="currentColor" font-size="11">P1</text>
  <rect x="92" y="50" width="60" height="60" rx="6" fill="#4a90d9" fill-opacity="0.25" stroke="currentColor"/>
  <text x="122" y="85" text-anchor="middle" fill="currentColor" font-size="11">P2</text>
  <rect x="164" y="50" width="60" height="60" rx="6" fill="#3d9970" fill-opacity="0.3" stroke="currentColor" stroke-width="2"/>
  <text x="194" y="85" text-anchor="middle" fill="currentColor" font-size="11">P3 (빈)</text>
  <rect x="236" y="50" width="60" height="60" rx="6" fill="#4a90d9" fill-opacity="0.25" stroke="currentColor"/>
  <text x="266" y="85" text-anchor="middle" fill="currentColor" font-size="11">P4</text>
  <rect x="308" y="50" width="60" height="60" rx="6" fill="#4a90d9" fill-opacity="0.25" stroke="currentColor"/>
  <text x="338" y="85" text-anchor="middle" fill="currentColor" font-size="11">P5</text>
  <rect x="380" y="50" width="60" height="60" rx="6" fill="#4a90d9" fill-opacity="0.25" stroke="currentColor"/>
  <text x="410" y="85" text-anchor="middle" fill="currentColor" font-size="11">P6</text>
  <rect x="452" y="50" width="60" height="60" rx="6" fill="#3d9970" fill-opacity="0.3" stroke="currentColor" stroke-width="2"/>
  <text x="482" y="85" text-anchor="middle" fill="currentColor" font-size="11">P7 (빈)</text>
  <rect x="524" y="50" width="60" height="60" rx="6" fill="#4a90d9" fill-opacity="0.25" stroke="currentColor"/>
  <text x="554" y="85" text-anchor="middle" fill="currentColor" font-size="11">P8</text>
  <rect x="596" y="50" width="60" height="60" rx="6" fill="#4a90d9" fill-opacity="0.25" stroke="currentColor"/>
  <text x="626" y="85" text-anchor="middle" fill="currentColor" font-size="11">P9</text>
  <rect x="668" y="50" width="60" height="60" rx="6" fill="#4a90d9" fill-opacity="0.25" stroke="currentColor"/>
  <text x="698" y="85" text-anchor="middle" fill="currentColor" font-size="11">P10</text>
  <text x="20" y="145" fill="currentColor" font-size="13">파랑 = 청크는 지워졌지만 아직 다른 값이 남은 페이지 (회수 불가, 다수)</text>
  <text x="20" y="168" fill="currentColor" font-size="13">초록 = 완전히 빈 페이지 (회수 대상, 소수)</text>
</svg>

문제는 **소수를 골라내는 검사를, 다수에게 가장 비싼 비용을 물리고 나서야** 했다는 점이다.

## 1. AS-IS: 판정 순서가 거꾸로

예전 코드의 후보 1개당 처리 순서 (리뷰어가 코드 라인까지 짚은 그대로):

<svg viewBox="0 0 760 300" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="r4svg2-title">
  <title id="r4svg2-title">AS-IS: 비싼 단계들을 다 지나고 나서야 emptiness 를 검사하는 순서</title>
  <text x="20" y="28" fill="currentColor" font-size="14" font-weight="bold">AS-IS — 후보 1개당 (빈 페이지든 아니든):</text>
  <rect x="20" y="45" width="330" height="44" rx="8" fill="#e2a144" fill-opacity="0.2" stroke="currentColor"/>
  <text x="185" y="63" text-anchor="middle" fill="currentColor" font-size="12">① 파일테이블 헤더 fix (sticky first page 조회)</text>
  <text x="185" y="80" text-anchor="middle" fill="currentColor" font-size="12">② 파일테이블 헤더 fix 또 (is_numerable 조회)</text>
  <rect x="20" y="103" width="330" height="44" rx="8" fill="#e2574c" fill-opacity="0.25" stroke="currentColor" stroke-width="2"/>
  <text x="185" y="121" text-anchor="middle" fill="currentColor" font-size="12" font-weight="bold">③ OOS 통계 헤더 — 무조건 대기 WRITE latch</text>
  <text x="185" y="138" text-anchor="middle" fill="currentColor" font-size="12">(모든 INSERT 의 관문에서 직렬화!)</text>
  <rect x="20" y="161" width="330" height="38" rx="8" fill="#e2a144" fill-opacity="0.2" stroke="currentColor"/>
  <text x="185" y="184" text-anchor="middle" fill="currentColor" font-size="12">④ 후보 페이지 조건부 WRITE fix</text>
  <rect x="20" y="213" width="330" height="38" rx="8" fill="#3d9970" fill-opacity="0.2" stroke="currentColor"/>
  <text x="185" y="236" text-anchor="middle" fill="currentColor" font-size="12" font-weight="bold">⑤ 이제서야: "비었나?" 판정</text>
  <path d="M354 232 L470 232" stroke="currentColor" stroke-width="2"/>
  <path d="M470 232 l-9 -5 v10 z" fill="currentColor"/>
  <rect x="474" y="205" width="266" height="54" rx="8" fill="none" stroke="currentColor" stroke-dasharray="5 4"/>
  <text x="607" y="228" text-anchor="middle" fill="currentColor" font-size="12">대다수: "안 비었네" → skip</text>
  <text x="607" y="246" text-anchor="middle" fill="currentColor" font-size="12">①-④ 비용은 이미 다 지불함</text>
  <text x="380" y="285" fill="currentColor" font-size="13" font-weight="bold">→ 삭제된 청크 수에 비례해 INSERT 관문(③)이 두들겨 맞는다</text>
</svg>

특히 ③ 이 아프다. OOS 통계 헤더는 **모든 INSERT 가 빈자리를 찾을 때 잡는 관문**인데, 회수기가 "안 빈 페이지" 를 확인하러 올 때마다 이 관문을 배타로 잡으니, vacuum 이 삭제를 많이 할수록 INSERT 지연이 커진다. 리뷰어가 CBRD-26824 를 인용한 이유: 바로 이 헤더/bestspace 경로의 문제로 INSERT 가 164ms → 890ms 로 튄 **실측 전례**가 있어서, 이 우려는 이론이 아니라 재발 위험이다.

## 2. TO-BE: 2단계 판정 — 싼 검사로 먼저 거른다

수정 (`50c18b7de`) 은 순서를 뒤집는다:

<svg viewBox="0 0 760 330" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="r4svg3-title">
  <title id="r4svg3-title">TO-BE: 1단계 저비용 필터로 다수를 거르고, 통과자만 2단계에서 비싼 자물쇠를 잡는다</title>
  <text x="20" y="28" fill="currentColor" font-size="14" font-weight="bold">TO-BE — 2단계 판정:</text>
  <rect x="20" y="45" width="340" height="96" rx="10" fill="#3d9970" fill-opacity="0.15" stroke="currentColor" stroke-width="2"/>
  <text x="190" y="68" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">1단계 — 저비용 선별 (헤더 안 건드림)</text>
  <text x="190" y="90" text-anchor="middle" fill="currentColor" font-size="12">후보를 조건부 READ 로 fix (대기 0)</text>
  <text x="190" y="108" text-anchor="middle" fill="currentColor" font-size="12">PAGE_OOS 인가? + 비었나? + LSA 게이트 선검사</text>
  <text x="190" y="126" text-anchor="middle" fill="currentColor" font-size="12">하나라도 탈락 → 그 자리에서 skip</text>
  <path d="M364 93 H480" stroke="currentColor" stroke-width="2"/>
  <path d="M480 93 l-9 -5 v10 z" fill="currentColor"/>
  <text x="422" y="84" text-anchor="middle" fill="currentColor" font-size="11">통과 (소수)</text>
  <rect x="484" y="45" width="256" height="96" rx="10" fill="#e2a144" fill-opacity="0.2" stroke="currentColor" stroke-width="2"/>
  <text x="612" y="68" text-anchor="middle" fill="currentColor" font-size="13" font-weight="bold">2단계 — 확정 판정</text>
  <text x="612" y="90" text-anchor="middle" fill="currentColor" font-size="12">OOS 통계 헤더 WRITE latch</text>
  <text x="612" y="108" text-anchor="middle" fill="currentColor" font-size="12">조건부 WRITE fix + 세 조건 재검증</text>
  <text x="612" y="126" text-anchor="middle" fill="currentColor" font-size="12">→ file_dealloc (자체 sysop 커밋)</text>
  <path d="M190 145 V190" stroke="currentColor" stroke-dasharray="5 4" stroke-width="2"/>
  <path d="M190 190 l-5 -9 h10 z" fill="currentColor"/>
  <rect x="60 " y="194" width="260" height="46" rx="8" fill="none" stroke="currentColor" stroke-dasharray="5 4"/>
  <text x="190" y="214" text-anchor="middle" fill="currentColor" font-size="12">대다수 (안 빈 페이지) 의 총비용:</text>
  <text x="190" y="232" text-anchor="middle" fill="currentColor" font-size="12" font-weight="bold">조건부 READ fix 단 1회</text>
  <rect x="420" y="194" width="320" height="46" rx="8" fill="none" stroke="currentColor" stroke-dasharray="5 4"/>
  <text x="580" y="214" text-anchor="middle" fill="currentColor" font-size="12">per-file 불변 검사 (sticky page·numerable) 와 dedupe 는</text>
  <text x="580" y="232" text-anchor="middle" fill="currentColor" font-size="12" font-weight="bold">배치 진입 시 1회로 hoisting (후보마다 ✕)</text>
  <text x="20" y="285" fill="currentColor" font-size="13" font-weight="bold">효과: INSERT 관문 (통계 헤더) 을 건드리는 것은 "진짜 빈 페이지" 뿐 —</text>
  <text x="20" y="307" fill="currentColor" font-size="13" font-weight="bold">빈 페이지는 소수이고, 어차피 dealloc 이라는 큰 일을 하러 가는 길이라 비용이 묻힌다.</text>
</svg>

## 3. "1단계에서 비었다고 했는데 2단계에서 왜 또 검사해?" — 재검증이 핵심 안전장치

1단계와 2단계 사이에는 자물쇠가 없는 짧은 틈이 있다. 그 틈에 INSERT 가 그 페이지를 다시 채울 수 있다. 그래서 **1단계는 힌트일 뿐이고, 구속력 있는 판정은 항상 헤더 latch 아래의 2단계 재검증**이다:

<svg viewBox="0 0 760 210" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="r4svg4-title">
  <title id="r4svg4-title">1단계와 2단계 사이의 틈에 재충전이 끼어들어도 2단계 재검증이 잡아낸다</title>
  <path d="M30 60 H730" stroke="currentColor" stroke-width="2"/>
  <circle cx="120" cy="60" r="6" fill="#3d9970"/>
  <text x="120" y="40" text-anchor="middle" fill="currentColor" font-size="12">1단계: "비었음" (READ)</text>
  <circle cx="390" cy="60" r="6" fill="#4a90d9"/>
  <text x="390" y="40" text-anchor="middle" fill="currentColor" font-size="12">틈: INSERT 가 재충전!</text>
  <circle cx="620" cy="60" r="6" fill="#e2574c"/>
  <text x="620" y="40" text-anchor="middle" fill="currentColor" font-size="12">2단계: 재검증 (latch 아래)</text>
  <path d="M620 72 V120" stroke="currentColor" stroke-dasharray="5 4" stroke-width="2"/>
  <path d="M620 120 l-5 -9 h10 z" fill="currentColor"/>
  <rect x="470" y="124" width="270" height="60" rx="8" fill="#3d9970" fill-opacity="0.12" stroke="currentColor"/>
  <text x="605" y="148" text-anchor="middle" fill="currentColor" font-size="12" font-weight="bold">"안 비었네" → dealloc 안 함, skip</text>
  <text x="605" y="168" text-anchor="middle" fill="currentColor" font-size="12">재충전된 페이지는 안전하게 계속 사용됨</text>
  <text x="30" y="150" fill="currentColor" font-size="12">1단계가 뭐라고 했든 최종 결정은</text>
  <text x="30" y="170" fill="currentColor" font-size="12">항상 헤더 latch 아래에서만 내린다.</text>
</svg>

이 구조 덕분에 기존 안전성 논증 (헤더 latch 직렬화, insert latch 연속성, sysop-postpone 순서) 은 한 글자도 약해지지 않는다 — 1단계가 싸게 내린 "탈락" 판정은 어차피 2단계도 똑같이 내렸을 판정이고, 1단계가 잘못 통과시킨 것은 2단계가 걸러낸다. 추가된 비용은 **진짜 빈 페이지에 한해 fix 가 1회 더 (READ 후 WRITE)** 인데, 빈 페이지는 소수이고 dealloc 비용에 비하면 무시할 수준이다.

## 4. 정리 — 지적 vs 반영

| InChiJun 지적 | 반영 (`50c18b7de`) |
|---|---|
| non-empty 후보도 통계 헤더 배타 latch 비용을 전부 지불 | 1단계 조건부 READ 선별 — 탈락자는 **헤더를 아예 안 건드림** |
| 판정 순서: 비싼 것 먼저, emptiness 마지막 | 순서 반전: 싼 검사 (타입·emptiness·LSA) 먼저, 통과자만 비싼 단계 |
| `file_get_sticky_first_page` / `file_is_numerable` 을 후보마다 재조회 | 파일 단위 불변값이므로 **배치 진입 시 1회**로 hoisting |
| CBRD-26824 류 INSERT 지연 회귀 위험 | 헤더 접촉 = 빈 페이지 확정분만 + (R3 로) heap latch 밖 + 배치 1회 — 삼중 완화 |

답글 초안은 이 표를 그대로 서술하고, R3 반영 (`b43950a38`) 과 결합해 삼중으로 완화됐음을 덧붙인다.
