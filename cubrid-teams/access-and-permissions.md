# CUBRID Microsoft Teams 연동 권한 및 아키텍처 기준

- **작성일**: 2026-11-23 (Asia/Seoul)
- **대상 독자**: Teams 채널 수집기, 알림 봇, PR 리뷰 캘린더를 개발·유지보수하는 개발자 및 에이전트
- **근거 범위**:
  - `cubrid-teams-dev2-vimkim-bot` (`/home/vimkim/gh/cubrid-teams-dev2-vimkim-bot`, commit `6923193`)
  - `cubrid-dev2-pr-calendar` (`/home/vimkim/gh/cubrid-dev2-pr-calendar`, commit `867128a`)
  - `cubrid-teams-dev2bot` (`/home/vimkim/gh/cubrid-teams-dev2bot`)
  - `cubrid-teams-automation` (`/home/vimkim/gh/cubrid-teams-automation/main`)
  - 로컬 비공개 권한 카탈로그 및 점검 기록 (`~/.local/share/vimkim-bot/permission-catalog.json`, `decisions.tsv`, `registration.json`, `personal/api-permission-withdrawal-result.json`)
- **검증 한계**: 본 문서는 사내 테넌트 실측 결과와 공식 Microsoft 문서 기준을 구분합니다. 팀 소유자 동의 기반 RSC(`ChannelMessage.Read.Group`)의 실제 `200 OK` 허용 여부는 아직 테넌트 설치 전이므로 미검증(Open)입니다.

---

## 1. 핵심 결론 (TL;DR)

| 작업 | 담당 도구 | 현재 방식 | 실행 주체 | 브라우저 필요 | 왜 이 방식을 쓰는가 |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **채널 글·답글 읽기 (크롤링)** | `cubrid-teams-dev2-vimkim-bot` (`read`) | **Playwright 헤드리스 브라우저** | `dhkim@cubrid.com` 웹 세션 | **O** | Graph API 채널 읽기는 테넌트 관리자(`ChannelMessage.Read.All`) 또는 팀 소유자 RSC(`ChannelMessage.Read.Group`) 허가가 필수라, 추가 승인 없이 동작하는 브라우저 세션 사용 |
| **스레드 댓글 쓰기 (`dhkim` 명의)** | `cubrid-teams-dev2-vimkim-bot` (`reply --transport graph`) | **Microsoft Graph API** (`ChannelMessage.Send`) | `dhkim@cubrid.com` 위임 토큰 | **X** | `ChannelMessage.Send`는 일반 사용자(`User`) 동의만으로 허용되어 관리자·팀 소유자 승인 없이 API로 직접 작성 가능 |
| **정기 알림 발송·`@dev2bot` 멘션 응답** | `cubrid-teams-dev2bot` | **Teams Bot Framework API** | `dev2bot` 앱 자체 계정 | **X** | 등록된 일반 봇은 쓰기·채널 목록·`@멘션` 단건 수신이 기본 허용됨 (단, 일반 채널 글·과거 이력 읽기는 API 자체가 없어 불가) |

1. **본인 계정 권한(Delegated)만으로는 승인 없이 채널 글을 읽을 수 없습니다.**
   - Microsoft Graph에서 채널 **쓰기(`ChannelMessage.Send`)** 는 일반 사용자(`User`) 동의로 가능하지만, 채널 **읽기(`ChannelMessage.Read.All`)** 는 Delegated 권한조차 테넌트 관리자(`Admin`) 승인이 필수입니다.
2. **일반 봇(`@dev2bot` 모델)은 과거 글 조회와 비멘션 글 수집이 불가합니다.**
   - 일반 Teams 봇은 채널에서 `@멘션`된 실시간 메시지만 수신하며, PR 공지처럼 멘션 없는 일반 게시글과 답글 이력을 조회할 수 없습니다.
3. **테넌트 관리자 승인 없이 브라우저를 제거할 수 있는 유일한 공식 경로는 RSC(`ChannelMessage.Read.Group`)입니다.**
   - `ChannelMessage.Read.Group`은 테넌트 전역(`*.All`)이 아니라 앱이 설치된 **특정 팀 내부로만 한정되는 Application RSC 권한**입니다.
   - 테넌트 IT 관리자가 아니라 **해당 팀의 소유자(Team Owner)** 1회 설치 동의로 부여되며, 봇 웹훅 서버 없이도 Microsoft Graph REST API(`GET /messages`, `/replies`, `/delta`)로 직접 풀(Pull) 조회가 가능합니다.
   - 단, `dhkim@cubrid.com`이 `Team 2nd`의 일반 멤버인 경우 개인 테스트 팀에서 먼저 테넌트 RSC 허용 여부를 검증한 뒤, 성공 시 `Team 2nd` 소유자에게 1회 설치를 요청해야 합니다.

---

## 2. CUBRID 테넌트 권한 실측표 및 식별자

### 2.1 권한 실측표 (2026-11-16 실측 / 2026-11-23 재확인)

| 접근 방식 / Scope | 유형 | 승인 주체 (`permission-catalog.json` 실측) | CUBRID 테넌트 현재 상태 | 채널 글·답글 읽기 가능 여부 |
| :--- | :--- | :---: | :---: | :---: |
| `ChannelMessage.Send` | Delegated | `User` (본인 로그인 동의) | ✅ 동의됨 (`auth graph-status` 확인) | ❌ 쓰기 전용 |
| `Team.ReadBasic.All` / `Channel.ReadBasic.All` | Delegated | `User` | 사용 가능 (목록 메타데이터만) | ❌ 본문 불가 |
| `Chat.Read` / `ChatMessage.Send` | Delegated | `User` | 사용 가능 (1:1·그룹 채팅 한정) | ❌ 팀 채널 불가 |
| `User.Read` / `User.ReadBasic.All` | Delegated | `User` | ✅ 동의됨 (`auth graph-status` 확인) | ❌ 프로필 조회용 |
| `ChannelMessage.Read.All` | Delegated | **`Admin`** (테넌트 관리자 필수) | ❌ 미승인 | ❌ 관리자 승인 없이는 불가 |
| `ChannelMessage.Read.All` (및 `Team/Channel/Chat/Files.Read.All`) | Application (전역) | **`Admin`** (테넌트 관리자 필수) | ❌ 미승인 (`2026-11-16` 실호출 `401`) | ❌ 관리자 승인 없이는 불가 |
| **`ChannelMessage.Read.Group`** (RSC) | Application (팀 한정) | **Team Owner** (설치 시 팀 단위 동의) | ⏳ PoC 미설치 (`2026-11-23` 사전 호출 `401`) | ✅ 설치 성공 시 표준 채널 전체 조회 |
| Teams Web Playwright 세션 | 브라우저 세션 | 본인 MFA 로그인 | ✅ 동작 중 (`dhkim@cubrid.com`) | ✅ 본인이 볼 수 있는 채널 전체 |

- **커스텀 앱 사이드로딩 상태** (`2026-11-23` `teams status` 실측, `dhkim@cubrid.com`): `Sideloading: enabled`
- **Microsoft Graph 메시지 API 과금 정책**: 기존 Teams 메시지 API의 Model A/B 종량 과금은 **2025-08-25부로 폐지되어 무료**입니다.

### 2.2 운영 식별자 (비비밀 메타데이터)

> 토큰, private key, client secret 등 비밀값은 Git에 절대 기록하지 않고 `~/.config/`, `~/.local/share/`(mode `0600`/`0700`)에만 보관합니다.

| 항목 | 값 | 비고 |
| :--- | :--- | :--- |
| Tenant ID | `5164a237-c257-4417-8e1c-ec219eeff7b4` | CUBRID Microsoft 365 테넌트 |
| `Team 2nd` Group / Team ID | `cb868053-a165-439a-afe7-3205a18b8212` | 팀 단위 범위 |
| `0. 일반` Channel ID | `19:ff558641976c4510b0d9250a384bae08@thread.skype` | 일반 채널 |
| `1. 공지` Channel ID | `19:15f4df7fbe734a5abd311d90f870ea32@thread.skype` | 공지 채널 |
| `2. 개발` Channel ID | `19:1448747d9467462f8b65bb95d2d3ba8c@thread.skype` | 개발 채널 |
| `3. PR 공지` Channel ID | `19:c0d936c34e634e3a90eb6e6c43a35fb6@thread.skype` | PR 캘린더 수집 대상 |
| `6. dev2bot` Channel ID | `19:6000dcbfcbad4b519daaf3fc63533059@thread.skype` | `dev2bot` 알림 수신 채널 |
| Entra 앱 `dev2bot` (`appId`) | `18eddb4b-dc1a-4cad-995a-c436b4cfb5aa` | 운영 중인 Teams-managed 알림 봇 |
| Entra 앱 `vimkim-bot` (`appId`) | `993986dd-1c92-4924-a637-1d04e1f03e17` | 인증서 기반 읽기 앱 (`requiredResourceAccess: []`, 인증서 유효기간 `2026-11-16` ~ `2027-11-16`) |
| Entra 앱 `vimkim-bot-user` (`appId`) | `ef00638b-1fb8-437e-b5c3-157393ba366c` | Delegated `ChannelMessage.Send` / `User.ReadBasic.All` 용 퍼블릭 클라이언트 |

---

## 3. 저장소 및 도구 책임 경계

| 저장소 / 도구 | 경로 | 역할 및 경계 |
| :--- | :--- | :--- |
| `cubrid-teams-dev2bot` | `/home/vimkim/gh/cubrid-teams-dev2bot` | Team 2nd 정기 알림(`6. dev2bot`)과 `@dev2bot` 멘션 명령 응답. PM2 + devtunnel 사용. PR 수집기와 독립 유지 |
| `cubrid-teams-dev2-vimkim-bot` | `/home/vimkim/gh/cubrid-teams-dev2-vimkim-bot` | 개인 Teams Web 세션 기반 채널/스레드 읽기(`read`)와 Graph/브라우저 답글(`reply`). 원본 증거·경고 보존, 해석 금지 |
| `cubrid-teams-automation` | `/home/vimkim/gh/cubrid-teams-automation/main` | Playwright CLI 세션 관리 및 로그인 대시보드(`teams_reader.py`) 제공 |
| `cubrid-dev2-pr-calendar` | `/home/vimkim/gh/cubrid-dev2-pr-calendar` | `3. PR 공지` 수집(`sync`) + GitHub PR 상태 조회 + SQLite 카탈로그 + 대시보드/Pages API 제공 |

---

## 4. 아키텍처 트레이드오프 및 2026-11-20 장애 교훈

### 4.1 수집 방식 비교

| 방식 | 안정성 | 사전 조건 | 주요 한계 |
| :--- | :---: | :--- | :--- |
| **Playwright 개인 세션** (현재) | 중 (하드닝 후) | 본인 MFA 로그인 1회 | 가상 스크롤 한계(`oldest_reached: false`), 캐시 의존, Service Worker/세션 만료 위험 |
| **RSC Graph Pull** (`ChannelMessage.Read.Group`) | **상** | 팀 소유자(Owner) 1회 설치 동의 | 테넌트가 팀 소유자 RSC를 허용해야 함. 비공개/공유 채널은 별도 추가 필요, 웹훅 구독(`403`) 불가(Pull은 가능) |
| **RSC 봇 웹훅 푸시** | 중 | 팀 소유자 동의 + 공개 HTTPS 엔드포인트(`devtunnel`) | 다른 봇이 작성한 메시지는 웹훅으로 전달되지 않음; 인바운드 터널 의존 |
| **테넌트 전역 Graph 앱** (`ChannelMessage.Read.All`) | 상 | **회사 Entra 관리자 승인** | 회사 전체 팀 접근 권한으로 인해 일반 개발자 프로젝트에서 승인 받기 어려움 |

> **비공식 경로 배제 원칙**: Teams Web/First-party 내부 토큰을 탈취하거나 비공개 웹 API를 직접 호출하는 방식은 계정 보안·테넌트 정책 위반 및 예고 없는 깨짐 위험 때문에 사용하지 않습니다.

### 4.2 2026-11-20 장애 요약 및 Playwright 하드닝 (`6923193`)

- **발생 경위**: `2026-11-20 15:03:37 KST` 정시 동기화 중 스레드(`1794881903246`) 딥링크가 `teams.cloud.microsoft/v2/?meetingjoin=true&...`로 리다이렉트될 때 Teams Service Worker(`serviceworker.js`)가 **0바이트 HTTP 200**(`<html><head></head><body></body></html>`)을 반환했습니다.
- **고착 원인**: `browser_worker.py`의 `run()`이 `page.goto()` 전에 `identity()`를 호출했는데, 영구 브라우저 탭이 빈 페이지에 그대로 남아 있어 이후 매 정시(`16:00`~`11-23 13:00`)마다 30초 폴링 후 `IDENTITY_UNVERIFIED`로 중단되었습니다. 또한 `catalog.py`의 `sync()`가 Teams 실패 시 `refresh_github()`까지 건너뛰어 캘린더 전체 갱신이 멈췄습니다.
- **조치 (`6923193`)**:
  - `IDENTITY`가 로그인 화면(`login.microsoftonline.com`, `login.live.com`, 비밀번호 입력)은 그대로 `session_required`로 반환하되, 빈 문서 또는 15초 이상 아바타가 로드되지 않는 Teams 탭을 감지하면 Service Worker를 해제하고 `https://teams.cloud.microsoft/v2/`로 1회 자동 복구 이동하도록 수정했습니다.
  - `run()`의 읽기 스크립트에서도 `page.goto(source_url)` 직후 빈 문서가 감지되면 Service Worker를 해제하고 1회 재시도하도록 보강했습니다.

---

## 5. RSC(`ChannelMessage.Read.Group`) 참고 사양 및 현재 결정

`dhkim@cubrid.com`이 `Team 2nd`의 일반 멤버이고 팀 소유자 동의 절차 없이 운영하는 방향을 택했으므로, 임시 로컬 PoC 파일은 삭제하고 Playwright 하드닝(`6923193`) + 독립 GitHub 갱신 경로로 확정했습니다. 추후 `Team 2nd` 소유자 협조가 가능해질 때를 대비해 검증 기준만 남겨 둡니다.

1. **사전 베이스라인 실측 (`2026-11-23 14:48 KST`)**
   - `vimkim-bot` (`993986dd-1c92-4924-a637-1d04e1f03e17`) 인증서로 `msal` client credentials 토큰 발급은 정상 동작함(`token_acquired: true`).
   - 팀 설치 전 `GET /v1.0/teams/cb868053-a165-439a-afe7-3205a18b8212/channels/19:c0d936c34e634e3a90eb6e6c43a35fb6@thread.skype/messages?$top=5` 호출은 예상대로 `401 Unauthorized` (`Identity of the caller could not be established.`) 반환.
2. **향후 RSC 전환 시 최소 Teams 앱 매니페스트 사양 (봇·웹훅 불필요)**
   - `manifestVersion`: `1.16`
   - `webApplicationInfo`: `id = 993986dd-1c92-4924-a637-1d04e1f03e17` (`vimkim-bot`), `resource = https://RscBasedStoreApp`
   - `authorization.permissions.resourceSpecific`: `[{"name": "ChannelMessage.Read.Group", "type": "Application"}]`
3. **향후 적용·원복 절차 (참고용)**
   - **1단계(정책 확인)**: 본인 소유 테스트 팀에 앱을 업로드하고 *"이 팀의 채널 메시지 읽기"* 동의 후 `GET .../messages` `200 OK` 여부 확인.
   - **2단계(`Team 2nd` 적용)**: 1단계 성공 시 `Team 2nd` 소유자에게 1회 설치를 요청한 뒤 `3. PR 공지` Graph Pull로 전환.
   - **원복**: Teams의 **팀 관리 → 앱**에서 앱을 제거하는 즉시 해당 팀의 RSC 읽기 권한이 회수됨.
