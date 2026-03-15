# CLAUDE.md — cclanes

## Overview

~/home/ 하위 로컬 레포들의 현황을 한눈에 보는 CLI 도구.
바이브 코딩 시 병렬 작업의 컨텍스트 전환 비용을 줄이는 것이 목적.

## Status

v1 구현 완료. `cclanes` CLI로 레포별 작업 현황 요약 출력.

## cclanes CLI

```bash
python3 cclanes.py            # LLM 요약 포함 전체 스캔
python3 cclanes.py --raw      # LLM 없이 raw 데이터
python3 cclanes.py --days 7   # 최근 7일 내 활동만
```

Alias: `alias cclanes="python3 ~/home/cclanes/cclanes.py"`
Slash command: `/lanes`

## Key Insight

기존 도구들은 각각 git 상태, GitHub PR, 에이전트 오케스트레이션만 다룸.
"로컬 레포 전체의 상태 + 실행 서비스 + AI 세션을 경량으로 한눈에 보는 도구"는 부재.

## Principles

- 아이디어가 먼저, 구현은 나중. 충분히 구체화된 후 개발 시작.
- 초기에는 가볍게. 오버엔지니어링 금지.
- ~/home/ 하위 레포들의 CLAUDE.md, git 상태 등을 데이터 소스로 활용.
