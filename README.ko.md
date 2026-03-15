🇺🇸 [English](README.md)

# cclanes

> "지금 뭘 하고 있었지?" — 병렬 바이브코딩을 위한 레포별 작업 요약 CLI

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![No Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-green)](pyproject.toml)

---

## Demo

```
$ cclanes
📋 캐시 19개 / 새 분석 2개
레포                          마지막 활동        요약
──────────────────────────  ────────────  ────────────────────────────────────────
cclanes               방금            cclanes CLI 구현 완료
kr-whisky-tracker           11일 전         위스키 정렬 기능 구현
GoPeaceTrain                10시간 전        한탄호텔 예약 모니터링 시작
```

## Why "lanes"?

수영장의 레인처럼 — 각 레포는 하나의 레인이고, 그 안의 작업(Claude Code 세션, 커밋, 브랜치)은 훈련 중인 선수입니다. 당신은 풀사이드의 감독이고, cclanes는 전광판입니다. 모든 레인의 진행 상황을 한눈에 보여줘서, 다음에 어디에 집중할지 바로 판단할 수 있습니다.

## Features

- 🔍 **레포 자동 스캔** — `~/home/*` 하위 Git 레포를 자동으로 탐색
- 🤖 **LLM 한 줄 요약** — `claude` CLI를 통해 Haiku가 레포별 작업 내용을 요약
- ⚡ **스마트 캐싱** — 변경된 레포만 재분석, 나머지는 캐시 활용
- 📝 **수동 메모** — 15분 유효 메모로 즉석 컨텍스트 기록
- 🎛️ **레포 제외/포함** — 불필요한 레포를 영구 제외하거나 복구
- 📊 **Raw 모드** — LLM 없이 git 데이터만 빠르게 확인

## 빠른 시작

### 사전 요구사항

- Python 3.10+
- [`claude` CLI](https://docs.anthropic.com/en/docs/claude-code) (LLM 요약에 사용, `--raw` 모드에서는 불필요)

### 설치

```bash
# 클론
git clone https://github.com/WoojinAhn/cclanes.git
cd cclanes

# alias 등록 (선택)
echo 'alias cclanes="python3 ~/home/cclanes/cclanes.py"' >> ~/.zshrc
source ~/.zshrc
```

### 사용법

```bash
cclanes                          # LLM 요약 포함 전체 스캔
cclanes --raw                    # LLM 없이 raw 데이터
cclanes --days 7                 # 최근 7일 내 활동만
cclanes --memo <repo> "message"  # 수동 메모 저장
cclanes --exclude repo1,repo2    # 영구 제외
cclanes --include repo1          # 제외 해제
```

## Claude Code 슬래시 커맨드

cclanes를 Claude Code의 `/lanes` 슬래시 커맨드로 등록할 수 있습니다:

```bash
# 커맨드 파일 생성
mkdir -p ~/.claude/commands
cat > ~/.claude/commands/lanes.md << 'EOF'
---
description: Show per-repo "what was I working on" summaries across ~/home/
argument-hint: [--raw] [--days N]
allowed-tools: Bash
---

Run the `cclanes` CLI to show per-repo work summaries.

Flags (passed as-is to the script):
- `--raw`: No LLM summary — show raw git + session data only (fast)
- `--days N`: Only show repos with activity in the last N days

```bash
python3 ~/home/cclanes/cclanes.py $ARGUMENTS 2>&1
```

After the command completes, present the output as-is to the user.
EOF
```

이후 Claude Code 세션에서 `/lanes`를 입력하면 실행됩니다.

## 설정

### `~/.cclanes/config.json`

영구 제외 레포 목록 등 설정이 저장됩니다.

```json
{
  "exclude": ["docs", "hn-activity"]
}
```

### `.cclanes` 메모 파일

`--memo`로 저장한 메모는 각 레포 루트에 `.cclanes` 파일로 생성됩니다. 15분이 지나면 자동으로 무시됩니다.

## 작동 원리

```
~/home/* 레포들
    │
    ├─ git log / status ──────┐
    ├─ Claude Code 세션 히스토리 ┤──→ 캐시 (변경 감지) ──→ claude CLI (Haiku) ──→ 정렬된 테이블 출력
    └─ .cclanes 수동 메모 ──────┘
```

1. `~/home/` 하위 디렉토리를 스캔하여 Git 레포를 식별
2. 각 레포에서 git log, git status, Claude Code 세션 히스토리, 수동 메모를 수집
3. 이전 캐시와 비교하여 변경된 레포만 `claude` CLI로 요약 요청
4. 최근 활동 순으로 정렬하여 테이블 출력

## 기술 스택

| 구분 | 선택 | 이유 |
|---|---|---|
| 언어 | Python 3.10+ | stdlib만으로 충분, 설치 간편 |
| 외부 의존성 | 없음 | pip install 불필요 |
| LLM | `claude` CLI (Haiku) | 이미 설치된 도구 활용, 빠르고 저렴 |
| 데이터 저장 | JSON 파일 캐시 | DB 불필요, 단순 |

## License

[MIT](LICENSE)
