# IDEAS

## 핵심 질문

- 내가 어떤 레포에서 무슨 작업을 하고 있는지 한눈에 보고 싶다
- ~/home/ 하위 레포가 많아지면서 맥락 전환 비용이 커지고 있다
- 바이브 코딩 시 여러 레포를 병렬로 작업할 때 현황 파악이 어렵다

## 데이터 소스 후보

- 각 레포의 CLAUDE.md (Overview 섹션)
- git log (최근 커밋, 마지막 활동일)
- git status (uncommitted changes 유무)
- git remote (GitHub 등록 여부)
- GitHub 이슈 (open count)
- 레포 내 TODO, MEMORY 등
- crontab (주기적 실행 중인 레포 여부 — e.g. GoPeaceTrain)
- 실행 중인 로컬 서버/프로세스

## 떠오르는 기능

- 레포별 한 줄 요약 (CLAUDE.md 파싱)
- 최근 활동 순 정렬
- 활성/비활성 레포 구분
- 미커밋 변경사항 경고
- GitHub 원격 등록 여부 표시
- 레포별 스택 자동 감지 (package.json → Next.js, requirements.txt → Python 등)

## 유사 도구 리서치 (2026-03-15)

### AI 코딩 에이전트 오케스트레이션

| 도구 | 설명 | 비고 |
|---|---|---|
| **Vibe Kanban** (~9.4k stars) | Kanban 기반 AI 에이전트 병렬 실행. git worktree 격리, 10+ 에이전트 지원 | 가장 근접하지만 무거움 |
| **Vibe Workflow** | PRD, Tech Spec, AGENTS.md 생성 등 워크플로우 지원 | Web 기반 |

### 터미널 Git 상태 대시보드

| 도구 | 설명 | 비고 |
|---|---|---|
| **gh-dash** (수천 stars) | GitHub PR/이슈 터미널 대시보드 | gh extension, 원격 중심 |
| **DevDash** (~1.6k stars) | YAML 설정 기반 터미널 대시보드 | Go, 범용 |
| **git-scope** | 로컬 Git 저장소 전체 상태 TUI | 소규모 |
| **git-overview** | 디렉토리 재귀 스캔, Git 상태 표시 | 소규모 |

### 프로젝트 매니저

| 도구 | 설명 | 비고 |
|---|---|---|
| **Projectable** | Rust TUI 프로젝트 매니저 | git, tmux, 에디터 통합 |
| **prm** | 프로젝트별 start/stop 스크립트 환경 전환 | Shell, 미니멀 |

### 시장 갭 (차별화 포인트)

1. **로컬 통합 대시보드 부재** — git 상태 + 실행 서비스 + AI 세션을 한 화면에서 보여주는 도구 없음
2. **프로젝트 컨텍스트 스위칭** — 디렉토리 전환은 있지만 "상태 요약"을 즉시 보여주는 도구 없음
3. **에이전트 세션 모니터링** — 독립 실행 중인 Claude Code/Cursor 세션 모니터링 도구 없음
4. **경량 로컬 퍼스트** — Vibe Kanban은 무거움. TUI 수준의 가벼운 대안 없음

## 형태 후보

- 정적 HTML (가장 심플)
- localhost 웹앱 (자동 갱신)
- 터미널 TUI (경량, tmux 친화적)
- macOS 메뉴바 앱 (CursorMeter처럼)

## 현재 ~/home/ 레포 카탈로그 (21개, 2026-03-15 기준)

### 개인 도구
| 레포 | 설명 | 스택 | GitHub |
|---|---|---|---|
| GoPeaceTrain | 한탄호텔 예약 모니터링 + 텔레그램 알림 | Python | private |
| github-star-checker | GitHub 스타 변동 모니터링 | - | public |
| chrome-cookie-reader | macOS Chrome 쿠키 복호화 | Python | public |
| tab-labeler | 터미널 탭 라벨링 (멀티 Claude Code) | - | - |
| traders_checker | 이마트 상품 검색 스크래퍼 | Python | - |
| youtube-unsubscriber | YouTube 구독 관리 | React+Express | private |

### 웹앱
| 레포 | 설명 | 스택 | GitHub |
|---|---|---|---|
| kr-whisky-tracker | 트레이더스 위스키 검색/가격 | Next.js | public |
| dev-insights-dashboard | GitHub 기반 개발자 페이지 | Next.js | public |
| miniroom-demo | 도토리 월드 방꾸미기 | Next.js | public |

### Claude Code 관련
| 레포 | 설명 | GitHub |
|---|---|---|
| claude-code-tutorial | 슬래시 커맨드 튜토리얼 | public |
| claude-tutorial-playground | 튜토리얼 실습용 | public |
| claude-config | 설정 동기화 | public |
| mobile-claude-setup | iPhone SSH 접속 가이드 | public |

### 기타
| 레포 | 설명 | GitHub |
|---|---|---|
| backlog / backlog-idea-app | 아이디어 → GitHub 이슈 | public |
| cursor-docs-crawler | Cursor 문서 크롤러 | public |
| CursorMeter | Cursor 사용량 모니터 (macOS) | public |
| spring-commerce | Spring Boot 4.0 이커머스 실험 | public |
| WoojinAhn | GitHub 프로필 | public |
| dev-dashboard | (이 프로젝트) | - |
| hn-activity | (미정) | - |
| docs | (미정) | - |

## 미정

- 기술 스택
- 업데이트 주기
- 공개 여부
