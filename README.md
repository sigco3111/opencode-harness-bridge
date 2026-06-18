# opencode-harness-bridge

> **OpenCode 하니스 브릿지** — Claude Code/Codex 하니스를 OpenCode로 안전하게 이주

[![v1.0.0](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/sigco3111/opencode-harness-bridge/releases/tag/v1.0.0)
[![Python 3.11–3.14](https://img.shields.io/badge/python-3.11--3.14-green.svg)](https://github.com/sigco3111/opencode-harness-bridge)
[![94 tests](https://img.shields.io/badge/tests-94%20passing-brightgreen.svg)](https://github.com/sigco3111/opencode-harness-bridge)
[![zero deps](https://img.shields.io/badge/runtime%20deps-zero-blue.svg)](https://github.com/sigco3111/opencode-harness-bridge)
[![MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

<a id="english"></a>

> **OpenCode harness bridge** — Safely migrate Claude Code/Codex harnesses to OpenCode.

---

## 왜 이게 필요한가? / Why?

2026년 현재 AI 코딩 에이전트 하니스는 **3가지 진영**으로 나뉘어 있어요:

| 진영 / Vendor | 설정 위치 | 형식 | 대표 하니스 |
|---|---|---|---|
| **Anthropic** | `~/.claude/`, `.claude/`, `CLAUDE.md` | JSON + Markdown | Claude Code |
| **OpenAI** | `~/.codex/`, `.codex/`, `AGENTS.md` | TOML + Markdown | Codex CLI |
| **OpenSource** | `~/.config/opencode/`, `opencode.json` | JSON + Markdown | OpenCode + oh-my-openagent |

**문제**: 한 도구에서 다른 도구로 갈아타려면?
- 1년치 `CLAUDE.md`를 Codex/OpenCode로 옮기려면?
- 9개 specialist role을 다시 정의하려면?
- hooks, MCP, skills를 안전하게 변환하려면?
- secrets는 절대 안 새어야 하는데?

**해결**: `opencode-harness-bridge`는 **3+1 tier 안전 정책** + **3-way 변환** + **양방향 drift 감지**로 메타 마이그레이션을 자동화합니다.

In 2026, AI coding agent harnesses are split into **3 camps** (Anthropic / OpenAI / OpenSource). Switching tools means migrating rules, agents, hooks, MCP, and skills — without losing a year of work, and without leaking secrets. This bridge does it with a 3+1 tier safety model, a 3-way converter, and bidirectional drift detection (`migrate maintain`).

---

## 3+1-Tier 안전 정책 / 3+1-Tier Safety Model

[`danyuchn/claude-codex-harness-sync`](https://github.com/danyuchn/claude-codex-harness-sync)의 정책을 차용 + OpenCode 타겟 1티어 추가:

| Tier | 의미 / Meaning | 예시 / Example |
|---|---|---|
| `auto-apply-after-confirmation` | 안전, 사용자 확인 후 자동 적용 / Safe, apply after user confirms | `CLAUDE.md` → `AGENTS.md` 이름 변경 |
| `model-assisted-manual` | 의미 변환 필요, 모델이 설명·승인 받은 후 적용 / Semantic translation, model explains + awaits approval | hooks (이벤트 스키마 다름), `@import` (Codex 미지원) |
| `user-owned-secret-step` | API 키/토큰 — 모델 절대 안 만짐, placeholder만 / Secrets handled by user only | `OPENAI_API_KEY`, GitHub PAT, MCP keys |
| `opencode-incompatible` *(신규)* | OpenCode로 자동 변환 불가, 수동 작업 / Cannot auto-convert, manual work required | Claude `mcp__*` 도구 allowlist → OpenCode `tools` 매핑 |

---

## 변환 범위 / Conversion Scope

| 자산 / Asset | Claude Code → OpenCode | Codex → OpenCode | 상태 / Status |
|---|---|---|---|
| 글로벌 지시문 / Global instructions | `~/.claude/CLAUDE.md` → `~/.config/opencode/opencode.json` + `AGENTS.md` | `~/.codex/AGENTS.md` → 동일 | ✅ v0.2.0+ |
| 프로젝트 지시문 / Project instructions | `CLAUDE.md`, `CLAUDE.local.md` → `AGENTS.md` | `AGENTS.md` → 동일 | ✅ v0.2.0+ |
| 에이전트 / Agents | `.claude/agents/*.md` → `opencode.json` `agent` 객체 | `.codex/agents/*.toml` → 동일 | ✅ v0.2.0+ |
| 훅 / Hooks | `.claude/settings.json` `hooks` → `opencode.json` `hooks` | `.codex/hooks/*.py` → shell wrapper | ⚠️ model-assisted |
| 스킬 / Skills | `.claude/skills/*` → `~/.config/opencode/command/*` + `.opencode/skills/*` | `.agents/skills/*` → 동일 | ✅ v0.2.0+ |
| MCP | `.claude/settings.json` `mcpServers` → `opencode.json` `mcp` | `~/.codex/config.toml` `mcp_servers` → 동일 | ✅ v0.2.0+ |
| 메모리 / Memory | `~/.claude/projects/*/memory/` → `~/wiki/` (선택) | `~/.codex/memories/` → 동일 | ⚠️ model-assisted |
| 규칙 / Rules | `.claude/rules/`, `@imports` → nested `AGENTS.md` | Codex native | ⚠️ model-assisted |
| 시크릿 / Secrets | ❌ 절대 안 옮김 (placeholders only) | 동일 | ✅ 항상 safe |
| **Drift 감지 / Maintain** | `migrate maintain` (양방향 비교, report-only) | 동일 | ✅ v0.4.0+ |

---

## 빠른 시작 / Quick Start

### 설치 / Install

```bash
# v1.0.0 (PyPI 미배포 — GitHub 직접)
pip install git+https://github.com/sigco3111/opencode-harness-bridge.git@v1.0.0
```

또는 OpenCode 마켓플레이스에서:
```bash
# command/ 와 skill/ 이 marketplace.json을 통해 자동 발견됨
# OpenCode 인앱 명령으로 /opencode-harness-bridge 사용 가능
```

### 사용 / Usage (5+1 단계 파이프라인)

```bash
# 1. 인벤토리 (현재 하니스 스캔)
opencode-harness-bridge inventory --source claude-code
# → 마크다운 리포트: 어디에 뭐가 있는지

# 2. 분류 (옛 → 새 매칭 + 안전 tier)
opencode-harness-bridge classify --source claude-code --target opencode
# → JSON: 각 자산의 tier (auto/model-assisted/user-owned/opencode-incompatible)

# 3. 변환 (안전 tier 1만 자동, 나머지는 plan만)
opencode-harness-bridge convert --source claude-code --target opencode --dry-run
# → 변환 계획 + 안전 알림

# 4. 적용 (사용자 확인 후)
opencode-harness-bridge convert --source claude-code --target opencode --apply-safe

# 5. 검증
opencode-harness-bridge validate ~/.config/opencode/
# → opencode.json syntax 체크 + 3+1-tier 정책 점검

# 6. 유지보수 (v0.4.0+: report-only drift 감지)
opencode-harness-bridge maintain --source claude-code --target-dir ~/.config/opencode
# → added / modified / removed / unchanged / manual_steps 리포트 (no apply)
```

### `--format` 옵션

대부분의 명령은 `--format {markdown|json}` 지원:
```bash
# 사람이 읽을 수 있는 마크다운
opencode-harness-bridge maintain --source claude-code --format markdown

# 파이프 가능한 단일 라인 JSON (jq, 스크립트용)
opencode-harness-bridge maintain --source claude-code --format json | jq .added
```

---

## Public API (Python)

`opencode_harness_bridge.__init__`에서 7개 심볼 노출 (v1.0.0 frozen):

```python
from opencode_harness_bridge import (
    migrate,                    # high-level orchestrator (inventory + classify + plan)
    maintain,                   # report-only drift detection (v0.4.0+)
    HarnessAsset,               # discovered asset dataclass
    MigrationPlan,              # bundle of assets + target + timestamp
    SafetyTier,                 # 4-tier StrEnum (auto/model/user/opencode-incompatible)
    MaintenanceItem,            # single drift entry (added/modified/removed/manual) — v0.4.0+
    MaintenanceReport,          # full drift report — v0.4.0+
)
```

Example:
```python
from opencode_harness_bridge import migrate, maintain

plan = migrate(source="claude-code", target="opencode", workspace="~/proj")
report = maintain(plan=plan, target_dir="~/.config/opencode")
print(f"{len(report.added)} added, {len(report.modified)} modified")
```

---

## 다른 PC에서 작업 / Working from another PC

빈 워크스페이스에서 시작:

```bash
# 1. 클론
git clone https://github.com/sigco3111/opencode-harness-bridge.git
cd opencode-harness-bridge

# 2. 개발 설치 (Python 3.11+ 필요)
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# 3. (선택) pre-commit 훅 설치
pip install pre-commit
pre-commit install

# 4. (선택) 테스트용 Claude Code 하니스 만들기
mkdir -p /tmp/fake-claude-harness/{.claude/agents,.claude/skills}
echo '# My Claude Rules' > /tmp/fake-claude-harness/CLAUDE.md
echo '{"mcpServers": {...}}' > /tmp/fake-claude-harness/.claude/settings.json

# 5. 동작 확인 (94 tests + ruff + mypy 모두 통과해야 함)
opencode-harness-bridge --version       # → 1.0.0
opencode-harness-bridge --help
pytest -q                                # → 94 passed
ruff check src tests                     # → All checks passed
mypy src                                 # → no issues found
```

### v1.0.0 모듈 구조 (현재 상태)

| 모듈 | 역할 |
|---|---|
| `models.py` | `HarnessAsset`, `MigrationPlan`, `SafetyTier` 도메인 타입 |
| `safety/tiers.py` | 4-tier 분류기 (auto/model/user/opencode-incompatible) |
| `audit/inventory.py` | Claude Code / Codex 하니스 스캔 (pathlib, zero-deps) |
| `audit/classify.py` | inventory → 4-tier 분류 |
| `converters/claude_code_to_opencode.py` | Claude Code → OpenCode 변환기 |
| `converters/codex_to_opencode.py` | Codex → OpenCode 변환기 (v0.3.0+) |
| `sync.py` | `maintain()` 양방향 drift 감지 (v0.4.0+) |
| `cli.py` | 6개 서브 명령 (inventory/classify/convert/validate/maintain/--version) |
| **OpenCode plugin** | `command/`, `skill/`, `.github/plugin/marketplace.json` (v1.0.0+) |

---

## 로드맵 / Roadmap

| 버전 / Version | 목표 / Goal | 상태 / Status |
|---|---|---|
| **v0.1.0** | Phase 0: 스켈레톤 + 4-tier 정책 + 인벤토리 스텁 | ✅ 출시됨 / Shipped (2026-06-17) |
| **v0.2.0** | Claude Code → OpenCode 변환기 + 30+ 테스트 + 실제 fixture | ✅ 출시됨 / Shipped (2026-06-17) |
| **v0.3.0** | Codex → OpenCode 변환기 (opencode-trading과 통합) | ✅ 출시됨 / Shipped (2026-06-17) |
| **v0.4.0** | 양방향 동기화 (`migrate maintain` — claude-codex-harness-sync 차용) | ✅ 출시됨 / Shipped (2026-06-18) |
| **v1.0.0** | OpenCode 마켓플레이스 등록, 안정화 (GA) | ✅ 출시됨 / Shipped (2026-06-18) |

v1.0.0 이후 계획은 GitHub Issues / Discussions 에서 추적.

---

## 디렉토리 구조 / Directory Structure

```
opencode-harness-bridge/
├── README.md
├── LICENSE                            # MIT
├── CHANGELOG.md                       # Keep-a-Changelog format
├── pyproject.toml                     # setuptools, zero runtime deps
├── .gitignore
├── .pre-commit-config.yaml            # ruff + hygiene hooks (v1.0.0+)
├── command/                           # OpenCode marketplace plugin (v1.0.0+)
│   └── opencode-harness-bridge.md
├── skill/                             # OpenCode marketplace plugin (v1.0.0+)
│   └── harness-convert/
│       └── SKILL.md
├── src/opencode_harness_bridge/
│   ├── __init__.py                    # 공개 API (7 심볼)
│   ├── __main__.py                    # python -m 진입점
│   ├── cli.py                         # argparse 6개 서브 명령
│   ├── models.py                      # HarnessAsset, MigrationPlan, SafetyTier
│   ├── exceptions.py                  # OpenCodeHarnessBridgeError 계층 (5 예외)
│   ├── sync.py                        # maintain() report-only drift (v0.4.0+)
│   ├── audit/
│   │   ├── __init__.py
│   │   ├── inventory.py               # .claude / .codex 스캔
│   │   └── classify.py                # inventory → 4-tier 분류
│   ├── converters/
│   │   ├── __init__.py
│   │   ├── claude_code_to_opencode.py # CLAUDE.md, .claude/ → opencode.json
│   │   ├── codex_to_opencode.py       # .codex/ → opencode.json (v0.3.0+)
│   │   └── shared.py                  # 공통 TOML/JSON/Markdown 유틸
│   └── safety/
│       ├── __init__.py
│       ├── tiers.py                   # 4-tier 분류 로직
│       └── secrets.py                 # API key/token 감지 (정규식 기반)
├── tests/
│   ├── conftest.py                    # 가짜 .claude / .codex fixture 빌더
│   ├── fixtures/
│   │   ├── sample-claude-harness/     # 10 파일, 6 자산 종류
│   │   ├── sample-claude-harness-with-secret/  # S6: SecretLeakError
│   │   ├── sample-claude-harness-malformed-settings/  # S7
│   │   ├── sample-codex-harness/      # 5 자산 종류
│   │   ├── sample-codex-harness-with-secret/  # S12
│   │   └── sample-codex-harness-malformed-toml/  # S14
│   ├── test_models.py                 # 6 tests
│   ├── test_safety_tiers.py           # 11 tests
│   ├── test_inventory_classify.py     # inventory + classify 통합
│   ├── test_inventory_real.py         # real Claude fixture
│   ├── test_inventory_codex.py        # real Codex fixture (8 tests)
│   ├── test_converters.py             # dispatcher
│   ├── test_converters_shared.py      # shared helpers
│   ├── test_claude_to_opencode_real.py # Claude → OpenCode
│   ├── test_codex_to_opencode_real.py # Codex → OpenCode (8 tests)
│   ├── test_cli.py                    # 5 subcommands + smoke
│   ├── test_cli_real.py               # subprocess-based CLI tests
│   ├── test_maintain.py               # sync.maintain() 8 tests (v0.4.0+)
│   └── test_release_readiness.py      # 8 invariants for v1.0.0+ (v1.0.0+)
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                     # matrix 3.11–3.14, ruff + mypy + pytest
│   │   └── release.yml                # tag push → build + GitHub Release (v1.0.0+)
│   └── plugin/
│       └── marketplace.json           # OpenCode marketplace manifest (v1.0.0+)
└── .pre-commit-config.yaml            # ruff + hygiene (v1.0.0+)
```

---

## 의존성 / Dependencies

- **runtime**: zero (모든 파싱은 stdlib — `tomllib`, `json`, `pathlib`, `re`, `dataclasses`, `enum`, `argparse`)
- **dev**: `pytest>=8`, `ruff`, `mypy`, `build>=1.0`, `twine>=5` (+ 선택: `pre-commit`)
- **Python**: 3.11, 3.12, 3.13, 3.14 (CI에서 모두 테스트)
- **이 프로젝트는 어디에도 의존하지 않습니다** — Claude Code나 Codex가 설치 안 돼도 동작 (pathlib로 파일 스캔만)

This project has **zero runtime dependencies**. It scans the filesystem with stdlib `pathlib`/`json`/`tomllib` — neither Claude Code nor Codex needs to be installed.

---

## 시그니처 시리즈 / Signature Series

- `sigco3111/md-doctor` — markdown 파일 진단
- `sigco3111/cron-doctor` — cron 표현식 진단
- `sigco3111/kakao-summary` — 카카오톡 메시지 요약
- `sigco3111/opencode-trading` — TradingCodex → OpenCode 어댑터 (도메인 특화)
- **`sigco3111/opencode-harness-bridge` — Claude/Codex → OpenCode 마이그레이션 (메타)**

"sigco3111" GitHub 조직의 **OpenCode 도메인 어댑터** 시리즈 2번째.

---

## 기여 / Contributing

기여 환영합니다. 새 변환기 추가 시:
1. `src/opencode_harness_bridge/converters/<source>_to_opencode.py` 작성
2. `tests/fixtures/sample-<source>-harness/` 에 테스트 fixture 추가
3. `tests/test_<source>_to_opencode.py` 단위 테스트 (5~10개)
4. `tests/test_release_readiness.py` 의 invariant 통과 확인
5. `docs/decisions/000X-<converter-name>.md` ADR 작성
6. PR — `feat(converter): add <source>-to-opencode converter` 형식

Contributions welcome. For new converters:
1. Add `<source>_to_opencode.py` under `converters/`
2. Add test fixture under `tests/fixtures/sample-<source>-harness/`
3. Add 5~10 unit tests
4. Verify `tests/test_release_readiness.py` invariants pass
5. Write an ADR under `docs/decisions/`
6. PR with `feat(converter): add ...` style commit

릴리스 프로세스: `v*` 태그 푸시 → `.github/workflows/release.yml` 자동 트리거 → 테스트 + sdist+wheel 빌드 → GitHub Release 첨부. PyPI 배포는 v1.0.0 범위 밖.

---

## 감사의 말 / Credits

- **[danyuchn/claude-codex-harness-sync](https://github.com/danyuchn/claude-codex-harness-sync)** (MIT) — 3-tier 안전 정책 + audit/classify/validate 3-phase 구조 + `migrate maintain` 차용
- **[oh-my-openagent](https://github.com/code-yeongyu/oh-my-openagent)** — OpenCode 에이전트 스쿼드 시스템 + `command/` `skill/` marketplace 컨벤션
- **[monarchjuno/tradingcodex](https://github.com/monarchjuno/tradingcodex)** (Apache-2.0) — Codex 하니스 구조 참고
- **[opencode-market](https://github.com/CKGrafico/opencode-market)** / **[opencode-marketplace](https://github.com/NikiforovAll/opencode-marketplace)** / **[opencode-registry](https://github.com/juliendf/opencode-registry)** — OpenCode 마켓플레이스 컨벤션
- 시그니처 OSS 시리즈: `md-doctor`, `cron-doctor`, `kakao-summary`, `opencode-trading`와 동일 패턴

---

## 라이선스 / License

MIT — see [LICENSE](LICENSE).
