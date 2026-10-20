# Guardrail Design Options for the Agent-Maintained CRC Go Rewrite

Status: Phase 0 options and recommendation for `refactor/go-rewrite`
Context: `docs/go-rewrite/HLD.md`, `docs/go-rewrite/AGENT_BRIEF.md`, `CLEANUP_SAFETY.md`

---

## 1. Context and Core Problem

`cloud-resource-cleanup` (`crc`) deletes and stops leftover test infrastructure across AWS, Azure, GCP, and OCI from Jenkins jobs. After the Go rewrite, **the repository will be maintained entirely by AI coding agents with no human code review**.

The current Python codebase (`crc.py` at 1,650 lines + `crc/**`) demonstrates the exact failure mode we must prevent:
- Central orchestrators grow `switch`/`if-elif` chains per cloud and resource.
- Individual cleaners re-implement tag matching, age parsing, dry-run gating, and reporting with subtle semantic drift.
- Safety invariants (e.g., AWS EBS opt-in, CloudWatch `GetMetricData` last-page `StatusCode`, Spot request cancel-before-terminate ordering, `crc_leftover_of` marker lifecycle, fail-closed age checks) live in scattered code paths and prose in `CLEANUP_SAFETY.md`.

Without human reviewers, AI coding agents naturally take the path of least resistance: appending `if cloud == "foo"` branches to `internal/engine`, calling cloud SDKs directly instead of defining narrow fakeable interfaces, skipping `internal/policy`, or modifying failing safety tests to make CI green. Prose instructions in `AGENTS.md` decay quickly and are routinely bypassed under token pressure.

Therefore, **design and architectural guardrails must be heavy and mechanically enforced**, while keeping context overhead low and error feedback immediately actionable ("positive prompt injection").

---

## 2. Industry Research Synthesis

Before defining the options for `crc`, we synthesize the primary industry models for autonomous and semi-autonomous agent-first codebases:

### 2.1 OpenAI — "Harness Engineering: Leveraging Codex in an Agent-First World" (Lopopolo, Feb 2026)
- **Source**: [openai.com/index/harness-engineering](https://openai.com/index/harness-engineering) (1M+ LOC internal product built with 0 lines of human-written code).
- **Short `AGENTS.md` as a Map, Not an Encyclopedia**: A giant instruction manual crowds out task context, causes local pattern-matching, and rots. Root `AGENTS.md` is kept to ~100 lines as a table of contents pointing into `docs/`.
- **`docs/` as the System of Record**: Structured subdirectories (`docs/design-docs/`, `docs/exec-plans/active|completed/`, `docs/QUALITY_SCORE.md`, `ARCHITECTURE.md`) store all institutional knowledge in-repo. Mechanical linters check cross-links and freshness; recurring **"doc-gardening" agents** scan for drift between docs and code.
- **Rigid Layered Architecture with Custom Linters & Structural Tests**: Strict forward-only dependency edges enforced by custom linters and structural tests. Crucially, linter error messages are written as **remediation prompts injected into agent context** (telling the agent *why* the boundary exists and *where* to move the code).
- **Golden Principles & Garbage Collection**: Opinionated mechanical rules (e.g., "use shared internal utilities rather than hand-rolled helpers", "parse at boundaries", file size limits) paired with background cleanup agents.

### 2.2 Stripe — "Minions: One-Shot, End-to-End Coding Agents" (Parts 1 & 2, 2026)
- **Source**: [stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents) and [Part 2](https://stripe.dev/blog/minions-stripes-one-shot-end-to-end-coding-agents-part-2).
- **Directory-Scoped Conditional Rules**: Unconditional global rules bloat context windows across large codebases. Nearly all agent rules at Stripe are conditionally applied by subdirectory or file glob, shared across Cursor (`.cursor/rules/*.mdc` with `globs`), Claude Code (`CLAUDE.md`), and internal minions.
- **Blueprints Interleaving Deterministic and Agentic Nodes**: Tasks are executed via state-machine "blueprints" that alternate free-form agent nodes ("Implement cleaner", "Fix failing test") with hard deterministic code nodes ("Scaffold boilerplate", "Run package linters", "Verify git diff against protected paths"). Putting LLMs into contained boxes compounds reliability.
- **Shift-Left Feedback (<5s Local Gate, Capped CI)**: A local heuristic runner executes targeted fast lints and structural checks in under 5 seconds before any git push. CI runs full suites with a strict cap (at most 2 autonomous CI repair rounds) so agents do not spin in infinite fix loops.

### 2.3 Martin Fowler & Thoughtworks — "Harness Engineering" & "Maintainability Sensors" (Böckeler, Apr–May 2026)
- **Source**: [martinfowler.com/articles/harness-engineering.html](https://www.martinfowler.com/articles/harness-engineering.html) and [martinfowler.com/articles/sensors-for-coding-agents.html](https://www.martinfowler.com/articles/sensors-for-coding-agents.html).
- **2x2 Harness Matrix**:
  - *Feedforward Guides* (steer before action) vs. *Feedback Sensors* (observe after action and trigger self-correction).
  - *Computational* (CPU-bound, deterministic, fast: compilers, AST tests, dependency rules, mutation tests) vs. *Inferential* (LLM-as-judge: semantic modularity review, rubric evaluation).
- **Maintainability Sensors for Typical AI Failure Modes**: Static enforcement of file length, function length, parameter counts, cyclomatic complexity, and module dependency rules with custom self-correction formatters.
- **Mutation Testing as the Ultimate Test-Quality Sensor**: Coverage is easily gamed by AI agents writing shallow, assertion-free tests. Incremental mutation testing catches tests that execute code without verifying safety invariants.

### 2.4 Evolutionary Architecture, ADRs & Agentic Fitness Functions (Ford et al.; InfoQ / van der Leij / duckadrift, Aug–Sep 2026)
- **Source**: *Building Evolutionary Architectures (2nd Ed.)*, [InfoQ: Agentic Fitness Functions](https://www.infoq.com/articles/agentic-fitness-functions-evolutionary-architecture/), [Architect View Master](https://www.architectviewmaster.com/blog/agentic-fitness-functions-when-the-evaluator-has-judgement/), [duckadrift](https://duckadrift.com/).
- **Two-Tier ADR Governance**:
  - *Tier 0 (Deterministic Fitness Functions)*: Hard-blocking tests that verify every ADR's structural claims, check for broken file/symbol references in ADRs, and enforce that code under governed paths cannot change without an ADR update or explicit acknowledgment.
  - *Tier 1 (Agentic Fitness Functions)*: Calibrated evaluator agents reading versioned YAML rubrics (`docs/adr/rubrics/*.yml`) and scoped diff evidence packs to detect *semantic drift* (e.g., responsibility creeping across boundaries without adding a forbidden import, or bypassing `policy.Policy` via custom string checks).

### 2.5 Cross-Tool Shared Agent Rules & ArXiv 11-Harness Study (Sep–Oct 2026)
- **Source**: [Shared Agent Rules — One Core, Tested Adapters](https://developertoolkit.ai/en/cto-scorecard-guide/shared-agent-rules/) and [ArXiv:2609.00006 — Anatomy of Eleven Coding Harnesses](https://arxiv.org/pdf/2609.00006).
- **One Core (`AGENTS.md`) + Thin Tool Adapters**: Root `AGENTS.md` (<200 lines) with a `Rules version:` canary line; `CLAUDE.md` as a symlink or `@AGENTS.md` import; `.cursor/rules/*.mdc` with path globs; deterministic CI script (`scripts/check-agent-rules.sh`) verifying adapter parity and total byte budgets (<32 KiB for Codex's `project_doc_max_bytes` chain limit).

---

## 3. Guardrail Options for CRC

Below are four concrete guardrail options tailored to `docs/go-rewrite/HLD.md` (`cmd/crc`, `internal/config`, `internal/engine`, `internal/policy`, `internal/age`, `internal/provider/{aws,azure,gcp,oci}`, `internal/notify/{slack,influx}`, `internal/report`).

---

### Option A: OpenAI "Harness Engineering" — Custom `go/packages` Structural Test Suite & System-of-Record `docs/`

#### 1. Idea and Source
Inspired directly by **OpenAI's Codex Harness Engineering** and **Martin Fowler's Computational Sensors with Self-Correction Prompts**.
All architectural enforcement lives in pure Go inside a dedicated `internal/archtest` package using standard library `go/ast`, `go/token`, and `golang.org/x/tools/go/packages`. Because it runs as part of `go test ./...`, **no agent can run unit tests without also running the full architectural, documentation, and safety-protection suite**. Every failure message prints a multi-line `REMEDIATION:` block instructing the agent how to fix the violation properly rather than working around it.

#### 2. Repository Layout
```text
/
├── README.md                          # User/Jenkins CLI reference, build, deliberate changes
├── AGENTS.md                          # ~100-line map & TOC (Rules version canary, commands, invariants)
├── CLAUDE.md -> AGENTS.md             # Symlink so Claude Code loads the exact same core
├── ARCHITECTURE.md                    # Package dependency DAG, registry model, Plan/Apply contract
├── CLEANUP_SAFETY.md                  # Canonical safety catalog with invariant IDs (SAF-001..SAF-020)
├── .golangci.yml                      # Fast standard linters (govet, staticcheck, gocognit, funlen,revive)
├── .cursor/
│   ├── rules/
│   │   └── 00-harness-map.mdc         # Always-applied thin pointer to AGENTS.md & ARCHITECTURE.md
│   └── skills/
│       └── use-modern-go/             # Existing JetBrains modern Go skill
├── docs/
│   ├── go-rewrite/                    # HLD.md, AGENT_BRIEF.md, DESIGN.md, GUARDRAIL_OPTIONS.md
│   ├── exec-plans/
│   │   ├── active/                    # Checked-in plans for multi-file changes
│   │   ├── completed/                 # Archived plans
│   │   └── tech-debt-tracker.md
│   └── QUALITY_SCORE.md               # Auto-generated package grade table
├── internal/
│   ├── archtest/                      # THE ENFORCEMENT ENGINE (runs under `go test ./...`)
│   │   ├── README.md
│   │   ├── arch_test.go               # Layering, imports, banned symbols, size limits
│   │   ├── docs_test.go               # Per-package README & heading schema validator
│   │   ├── registry_test.go           # Self-registration & Cleaner contract verifier
│   │   ├── safety_lock_test.go        # SHA-256 / AST lock on safety test cases
│   │   └── safety_manifest.json       # Locked hashes & required safety test function names
│   ├── config/
│   │   └── README.md
│   ├── age/
│   │   └── README.md
│   ├── policy/
│   │   └── README.md
│   ├── report/
│   │   └── README.md
│   ├── engine/
│   │   └── README.md
│   ├── notify/
│   │   ├── README.md
│   │   ├── slack/README.md
│   │   └── influx/README.md
│   └── provider/
│       ├── README.md
│       ├── aws/README.md
│       ├── azure/README.md
│       ├── gcp/README.md
│       └── oci/README.md
└── cmd/
    └── crc/
        └── README.md
```

#### 3. Exact Go Enforcement Mechanisms

1. **Strict Layered Dependency Matrix (`internal/archtest/arch_test.go`)**:
   Loads all packages via `packages.Load(&packages.Config{Mode: packages.NeedName | packages.NeedImports | packages.NeedSyntax | packages.NeedTypes}, "./...")` and checks an explicit allowlist DAG:
   - `internal/age` -> stdlib only.
   - `internal/config` -> stdlib, `internal/age`.
   - `internal/report` -> stdlib.
   - `internal/policy` -> stdlib, `internal/age`, `internal/config`.
   - `internal/provider` -> stdlib, `internal/config`, `internal/policy`, `internal/report`.
   - `internal/provider/<cloud>` -> `internal/provider`, `internal/policy`, `internal/age`, `internal/config`, `internal/report`, and **only** `<cloud>`'s own SDK. Cross-provider imports (e.g., `aws` importing `gcp`) and upward imports (`provider/*` importing `engine` or `notify`) fail immediately.
   - `internal/notify/{slack,influx}` -> `internal/notify`, `internal/report`, `internal/config`, and its own client library.
   - `internal/engine` -> `internal/provider` (root only, **never** `internal/provider/<cloud>`), `internal/policy`, `internal/config`, `internal/notify`, `internal/report`.
   - `cmd/crc` -> wires `internal/engine`, `internal/config`, `internal/notify/*`, and blank-imports `_ ".../internal/provider/<cloud>"`.
   - *Remediation output example*:
     ```text
     ARCH VIOLATION [LAYER-001]: package "internal/engine" imports "internal/provider/aws".
     WHY: The engine must remain 100% cloud-agnostic (HLD §2.2, §3).
     REMEDIATION: Remove the import from internal/engine. Register the cloud provider in
     internal/provider/<cloud>/register.go via provider.Register(...) in init(), blank-import it
     ONLY in cmd/crc/main.go, and interact with it through provider.Lookup() and provider.Cleaner.
     ```

2. **Anti-Switch & Registry-Only Extension Enforcement (`internal/archtest/registry_test.go`)**:
   - AST scan of `internal/engine`, `internal/policy`, `internal/config`, `internal/report`, and `cmd/crc` forbids string literals `"aws"`, `"azure"`, `"gcp"`, `"oci"` inside `switch` or `if` conditions (except in CLI flag validation tables explicitly declared in `internal/config`).
   - AST scan verifies that `provider.Register` is called **only** inside `init()` in files named `internal/provider/<cloud>/register.go`, and that every `internal/provider/<cloud>` package is blank-imported in `cmd/crc/main.go`.
   - AST scan of every struct implementing `provider.Cleaner` verifies:
     - `Plan(...)` never invokes SDK mutation methods (`Delete*`, `Terminate*`, `Cancel*`, `Stop*`, `Deallocate*`, `ScheduleKeyDeletion*`).
     - Every `<kind>.go` file in `internal/provider/<cloud>/` has a matching `<kind>_test.go` with at least `Test<Kind>_Plan` and `Test<Kind>_Apply` using a fake client interface (no live SDK concrete client construction in `_test.go`).

3. **Per-Package `README.md` Contract (`internal/archtest/docs_test.go`)**:
   - Every directory containing `.go` files MUST contain a `README.md`.
   - `docs_test.go` parses each package `README.md` AND the package's Go AST, verifying:
     1. Required headings exist: `## Purpose`, `## Exported API`, `## Safety Invariants`, `## Allowed Dependencies`.
     2. Every exported Go type/function in the package is mentioned in `## Exported API` (prevents agents adding undocumented exports or letting the README rot).

4. **File, Function, and Complexity Limits (`arch_test.go` + `.golangci.yml`)**:
   - Max 400 lines per non-test `.go` file; max 60 lines per function; max cognitive complexity 15 (`gocognit`); max 5 parameters per function.
   - Banned calls: `os.Setenv` / `os.Unsetenv` in non-test code (enforces HLD §8.2: no `MAX_AGE` env mutation), `os.Exit` / `log.Fatal` outside `cmd/crc/main.go`, `fmt.Print*` outside `cmd/crc` (enforces `log/slog`).

5. **Protected Safety Tests (`internal/archtest/safety_lock_test.go`)**:
   - `CLEANUP_SAFETY.md` defines canonical IDs (`SAF-001` through `SAF-020`).
   - `internal/archtest/safety_manifest.json` lists every required safety test function (e.g., `TestEBS_RequiresExplicitCloudAndResource`, `TestSpotRequests_CancelFailureNeverTerminates`, `TestEBS_CloudWatchPaginationUsesLastPageStatus`, `TestAge_EmptyOrZeroFailsClosed`) and the normalized AST hash of its assertions.
   - `safety_lock_test.go` verifies that every test in `safety_manifest.json` exists, does not call `t.Skip()`, and its assertion AST hash matches the manifest. Agents cannot delete, weaken, or skip a safety test without failing `TestSafetyLock`.

#### 4. CI and Pre-Commit Gates
- **Pre-commit (`.githooks/pre-commit`)**: Runs `go test ./internal/archtest/...` (~1.2s) + `golangci-lint run --new-from-rev=HEAD~1`.
- **CI (`.github/workflows/ci.yml`)**:
  1. `git diff --exit-code internal/archtest/` check (or CODEOWNERS gate) ensuring the agent did not tamper with `archtest` or `safety_manifest.json`.
  2. `go build ./cmd/crc`
  3. `go vet ./...` && `golangci-lint run`
  4. `go test -race -count=1 ./...` (which executes `internal/archtest` automatically).

#### 5. How a Future Agent Adds a New Cloud or Resource Type Step-by-Step
1. Agent reads `AGENTS.md` (100 lines) -> follows link to `ARCHITECTURE.md` §"Adding a Cleaner".
2. Creates `internal/provider/<cloud>/<kind>.go` implementing `provider.Cleaner` (`Kind()`, `Supports()`, `Plan()`, `Apply()`) against a narrow `<kind>API` interface, delegating tag/age filtering to `internal/policy`.
3. Registers the cleaner in `internal/provider/<cloud>/register.go` (and if a new cloud, adds `_ ".../internal/provider/<cloud>"` to `cmd/crc/main.go` and updates the `internal/archtest` provider list).
4. Creates `internal/provider/<cloud>/<kind>_test.go` with table-driven fake tests for `Plan` and `Apply`.
5. Updates `internal/provider/<cloud>/README.md` (`## Exported API` and `## Safety Invariants`).
6. Runs `go test ./...`. If it forgot the README update, imported a forbidden package, or called `Delete*` inside `Plan()`, `internal/archtest` fails immediately with exact remediation instructions.

#### 6. Pros, Cons, and Maintenance Cost
- **Pros**: Zero third-party architectural linter dependencies (`go test ./...` runs everything); impossible for an agent to forget to run; arbitrary Go-specific invariants (`Plan` vs `Apply` AST inspection, README-to-export sync, safety test AST locking) are trivial to express in `go/packages` and impossible in YAML linters; custom remediation messages drastically cut agent token churn.
- **Cons**: Requires writing ~500–700 lines of `internal/archtest` code during Phase 2 milestone 1.
- **Maintenance Cost**: **Very Low**. Uses only Go stdlib (`go/ast`, `go/token`) and `golang.org/x/tools/go/packages`, which never break across Go releases.

---

### Option B: Stripe "Minions" — Directory-Scoped Conditional Rules, Scaffolding Blueprints & Shift-Left declarative Linters

#### 1. Idea and Source
Inspired by **Stripe's Minions architecture** (Part 1 & Part 2, 2026) and **Shared Agent Rules adapters**.
Instead of relying on one global instruction file or custom AST test suites, this option minimizes context bloat via **directory-scoped rule files** (`AGENTS.md` per subsystem + `.cursor/rules/*.mdc` with `globs:`) and constrains agent behavior via **deterministic blueprint scripts** (`scripts/blueprint-new-cleaner.sh`, `scripts/verify-shift-left.sh`) paired with declarative off-the-shelf linters (`golangci-lint` with `depguard`, `revive`, `gocognit`, and `go-arch-lint`).

#### 2. Repository Layout
```text
/
├── README.md                          # User & Jenkins CLI docs
├── AGENTS.md                          # Ultra-minimal (<80 lines) global commands & blueprint rules
├── CLAUDE.md -> AGENTS.md             # Symlink
├── .golangci.yml                      # Heavy declarative config: depguard per-path rules, funlen, revive
├── .go-arch-lint.yml                  # Declarative component/vendor dependency graph for go-arch-lint
├── .github/
│   └── CODEOWNERS                     # Protects scripts/, .golangci.yml, *_safety_test.go
├── .cursor/
│   ├── rules/
│   │   ├── 00-core.mdc                # alwaysApply: true (<40 lines)
│   │   ├── 10-providers.mdc           # globs: ["internal/provider/**"] — SDK fake & Plan/Apply rules
│   │   ├── 20-engine-policy.mdc       # globs: ["internal/engine/**", "internal/policy/**"] — cloud-agnostic rules
│   │   ├── 30-safety-tests.mdc        # globs: ["**/*_safety_test.go", "CLEANUP_SAFETY.md"] — append-only rules
│   │   └── 40-cli-config.mdc          # globs: ["cmd/crc/**", "internal/config/**"] — Jenkins flag parity rules
│   └── skills/
│       └── use-modern-go/
├── scripts/
│   ├── blueprint-add-cleaner.sh       # Deterministic generator for new resource cleaner + test + README
│   ├── blueprint-add-provider.sh      # Deterministic generator for new cloud provider package
│   ├── shift-left-lint.sh             # <5s pre-push heuristic linter (runs only on touched packages)
│   └── check-guardrails.sh            # Shell checks for README existence & protected test diffs
└── internal/
    ├── engine/
    │   ├── README.md
    │   └── AGENTS.md                  # Local rules loaded only when agent enters internal/engine/
    ├── policy/
    │   ├── README.md
    │   └── AGENTS.md
    ├── provider/
    │   ├── README.md
    │   ├── AGENTS.md                  # Rules on Registry & Cleaner interface
    │   ├── aws/
    │   │   ├── README.md
    │   │   ├── AGENTS.md              # AWS-specific safety rules (EBS opt-in, Spot cancel order, CW last page)
    │   │   └── *_safety_test.go       # Dedicated safety test files protected from deletion/modification
    │   ├── azure/{README.md, AGENTS.md}
    │   ├── gcp/{README.md, AGENTS.md}
    │   └── oci/{README.md, AGENTS.md}
    └── notify/{README.md, slack/README.md, influx/README.md}
```

#### 3. Exact Go Enforcement Mechanisms

1. **`golangci-lint` `depguard` Per-Path Rules (`.golangci.yml`)**:
   Uses `depguard` with file globs to enforce package layering and SDK isolation:
   ```yaml
   linters-settings:
     depguard:
       rules:
         engine-cloud-agnostic:
           files: ["**/internal/engine/**"]
           allow: ["$gostd", "github.com/yugabyte/cloud-resource-cleanup/internal/config", "github.com/yugabyte/cloud-resource-cleanup/internal/policy", "github.com/yugabyte/cloud-resource-cleanup/internal/provider$", "github.com/yugabyte/cloud-resource-cleanup/internal/notify", "github.com/yugabyte/cloud-resource-cleanup/internal/report"]
           deny:
             - pkg: "github.com/yugabyte/cloud-resource-cleanup/internal/provider/"
               desc: "Engine must not import concrete cloud packages; use provider.Lookup()"
         aws-only-sdk:
           files: ["**/internal/provider/aws/**"]
           deny:
             - pkg: "github.com/Azure/"
               desc: "AWS provider cannot import Azure SDK"
             - pkg: "cloud.google.com/go/"
               desc: "AWS provider cannot import GCP SDK"
             - pkg: "github.com/oracle/oci-go-sdk"
               desc: "AWS provider cannot import OCI SDK"
   ```
2. **`go-arch-lint` Component Graph (`.go-arch-lint.yml`)**:
   Maps `cmd`, `engine`, `policy`, `age`, `config`, `report`, `notify`, and `provider/*` as components, binding each cloud SDK (`aws-sdk-go-v2`, `azcompute`, `cloud.google.com/go/compute`, `oci-go-sdk`) exclusively to its corresponding `provider/<cloud>` component.
3. **Deterministic Blueprint Scaffolder (`scripts/blueprint-add-cleaner.sh`)**:
   Instead of letting an LLM write registration and boilerplate from scratch, the agent is instructed by `.cursor/rules/10-providers.mdc` to run:
   `./scripts/blueprint-add-cleaner.sh --cloud aws --kind snapshot --supports delete`
   This deterministic node generates:
   - `internal/provider/aws/snapshot.go` with the `Cleaner` skeleton and `policy.Policy` hook wired in.
   - `internal/provider/aws/snapshot_test.go` and `snapshot_safety_test.go` skeletons.
   - Registration entry in `internal/provider/aws/register.go`.
   - Updated section in `internal/provider/aws/README.md`.
   The agent then only fills in the narrow SDK interface and `Plan`/`Apply` bodies.
4. **Shell Guardrail Gate (`scripts/check-guardrails.sh`)**:
   - Checks that every directory under `cmd/` and `internal/` with `.go` files has a non-empty `README.md` (>30 lines) and `AGENTS.md`.
   - Checks `git diff origin/refactor/go-rewrite...HEAD -- '**/*_safety_test.go'` to forbid line deletions or modifications to existing `*_safety_test.go` files (only new `*_safety_test.go` files or appended test cases are permitted unless an override flag is set by a human).
   - Verifies every `AGENTS.md` has a matching `CLAUDE.md` symlink/import and that the root-to-leaf `AGENTS.md` byte chain stays under 32 KiB.

#### 4. CI and Pre-Commit Gates
- **Pre-commit / Pre-push (`scripts/shift-left-lint.sh`)**: Runs in <5 seconds on only the Go packages touched in the working tree: `golangci-lint run --fast <changed-pkgs>`, `scripts/check-guardrails.sh`, and `go test <changed-pkgs>`.
- **CI**: Full `golangci-lint run`, `go-arch-lint check`, `scripts/check-guardrails.sh`, `go test -race ./...`.

#### 5. How a Future Agent Adds a New Cloud or Resource Type Step-by-Step
1. When the agent opens `internal/provider/aws/`, Cursor/Claude automatically injects `internal/provider/aws/AGENTS.md` and `.cursor/rules/10-providers.mdc`.
2. The rule instructs the agent to run `./scripts/blueprint-add-cleaner.sh --cloud <cloud> --kind <kind>` first (deterministic blueprint node).
3. The script scaffolds the cleaner, registration, fake interface, unit test, and README entry.
4. The agent implements the SDK calls inside the scaffolded `Plan` and `Apply` methods and fills out table-driven test cases.
5. On `git commit` / `git push`, `shift-left-lint.sh` runs `depguard`, `funlen`, `gocognit`, and `check-guardrails.sh` in <5 seconds.

#### 6. Pros, Cons, and Maintenance Cost
- **Pros**: Very low token usage per session (progressive disclosure via `.cursor/rules/*.mdc` and per-dir `AGENTS.md`); blueprint scripts eliminate registration drift and boilerplate mistakes; relies on standard declarative YAML config rather than custom AST code.
- **Cons**: Declarative YAML linters (`depguard`, `go-arch-lint`) only inspect package imports and basic metrics—they **cannot** verify semantic Go contracts like "does `Plan()` mutate cloud state?", "does every cleaner call `policy.Match()`?", or "do `README.md` documented symbols match actual exported Go types?". External binary (`go-arch-lint`) can lag behind new Go compiler versions (e.g., `go 1.24` vs `1.25` tool version skew).
- **Maintenance Cost**: **Medium**. Adding a new package requires updating `.golangci.yml` `depguard` blocks and `.go-arch-lint.yml` in sync; shell scripts and multiple `AGENTS.md` files must be kept aligned.

---

### Option C: Evolutionary Architecture — ADRs + Deterministic Fitness Functions + Agentic Fitness Rubrics + Mutation Testing

#### 1. Idea and Source
Inspired by **Ford et al. (*Building Evolutionary Architectures*)**, **InfoQ / van der Leij's "Agentic Fitness Functions"** (Aug–Sep 2026), **duckadrift**, and **Thoughtworks' Maintainability Sensors (Mutation Testing)** (May 2026).
This option treats architecture as a set of versioned **Architecture Decision Records (`docs/adr/ADR-*.md`)** where every ADR is paired with:
1. **Tier 0 (Deterministic Fitness Function)**: An executable Go test (`internal/fitness/adr_NNN_test.go`) and ADR integrity checker (`governed_paths` in YAML frontmatter).
2. **Tier 1 (Agentic Fitness Function)**: A structured YAML rubric (`docs/adr/rubrics/ADR-*.yml`) evaluated in CI by an independent, read-only judge agent (`claude -p` or `codex exec --sandbox read-only`) that inspects the git diff for **semantic boundary drift** (e.g., re-implementing tag filtering inside a cleaner instead of calling `internal/policy`, or breaking Spot cancel-before-terminate ordering).
3. **Mutation Testing Sensor (`go-mutesting` / `gremlins`)**: Prevents agents from writing high-coverage but assertion-free tests on `internal/policy`, `internal/age`, and safety-critical cleaners.

#### 2. Repository Layout
```text
/
├── README.md
├── AGENTS.md                          # Map pointing to docs/adr/ and fitness suite
├── CLAUDE.md -> AGENTS.md
├── CLEANUP_SAFETY.md
├── docs/
│   ├── adr/
│   │   ├── index.md                   # Auto-verified index of all ADRs
│   │   ├── 001-initiator-self-registration.md
│   │   ├── 002-cleaner-plan-apply-split.md
│   │   ├── 003-centralized-policy-fail-closed-age.md
│   │   ├── 004-aws-ebs-opt-in-and-cloudwatch-detach-age.md
│   │   ├── 005-aws-spot-cancel-terminate-leftover-markers.md
│   │   ├── 006-multi-cloud-leftover-disk-semantics.md
│   │   └── rubrics/                   # Tier 1 Agentic Fitness Rubrics
│   │       ├── boundary-fidelity.yml
│   │       ├── policy-centralization.yml
│   │       └── destructive-safety-order.yml
│   └── go-rewrite/
│       ├── HLD.md
│       └── DESIGN.md
├── internal/
│   ├── fitness/                       # Tier 0 Deterministic Fitness Functions
│   │   ├── README.md
│   │   ├── adr_frontmatter_test.go    # Verifies ADR index, governed_paths, symbol refs, ADR-ACK
│   │   ├── adr_001_registry_test.go   # Enforces ADR-001 (init() registration, zero engine cloud refs)
│   │   ├── adr_002_plan_apply_test.go # Enforces ADR-002 (Plan is read-only, Apply never called in dry-run)
│   │   ├── adr_003_policy_test.go     # Enforces ADR-003 (every cleaner imports & calls internal/policy)
│   │   └── adr_004_006_safety_test.go # Enforces safety invariant test presence & mutation score floor
│   └── ... (config, age, policy, engine, provider/*, notify/*, report — each with README.md)
└── scripts/
    ├── run-agentic-rubrics.sh         # Tier 1 read-only judge evaluating diff against docs/adr/rubrics/*.yml
    └── run-mutation-sensor.sh         # Runs incremental mutation testing on internal/policy, internal/age, etc.
```

#### 3. Exact Go Enforcement Mechanisms

1. **Machine-Checkable ADR Frontmatter (`internal/fitness/adr_frontmatter_test.go`)**:
   Every ADR in `docs/adr/NNN-*.md` has YAML frontmatter:
   ```yaml
   ---
   id: ADR-003
   status: Accepted
   governed_paths:
     - "internal/policy/**"
     - "internal/age/**"
     - "internal/provider/*/*.go"
   required_symbols:
     - "internal/policy.Policy.Match"
     - "internal/age.Duration.IsOld"
   fitness_test: "internal/fitness/adr_003_policy_test.go"
   rubric: "docs/adr/rubrics/policy-centralization.yml"
   ---
   ```
   `adr_frontmatter_test.go` deterministically checks (with zero LLM calls):
   - Every `governed_path`, `fitness_test`, `rubric`, and `required_symbol` actually exists in the Go codebase (no stale ADRs).
   - Every Go package under `internal/` is governed by at least one `Accepted` ADR and has a `README.md` linking to its governing ADRs.
   - If a commit modifies `internal/policy/**` or `internal/engine/**`, the commit message or PR body must contain `ADR-ACK: ADR-003` (or update the ADR).

2. **Tier 0 Deterministic Fitness Tests (`internal/fitness/adr_*_test.go`)**:
   Uses `arch-go` or `go/packages` to map each ADR directly to a Go test:
   - `TestADR001_InitiatorPattern`: Verifies `internal/engine` only calls `provider.Lookup` and never imports `internal/provider/<cloud>`.
   - `TestADR002_PlanApplySplit`: Verifies every `Cleaner` implementation has `Plan` and `Apply`, and `engine.Run` checks `cfg.DryRun` before calling `Apply`.
   - `TestADR003_PolicyCentralization`: Verifies every concrete `Cleaner` struct holds or receives `policy.Policy` and calls `policy` methods rather than `regexp.Compile` or `time.Since` directly in `internal/provider/<cloud>/*.go` (banning ad-hoc age/regex filtering in providers!).

3. **Mutation Testing Gate (`scripts/run-mutation-sensor.sh`)**:
   Runs `gremlins` (a fast Go mutation testing tool) on `internal/age`, `internal/policy`, and the safety-critical functions in `internal/provider/aws` (`disk.go`, `spot_instance_requests.go`). Enforces a **minimum mutation kill score of 85%**. If an agent deletes an assertion or writes a dummy test that only exercises lines without asserting safety outcomes, mutant survivors fail the build.

4. **Tier 1 Agentic Fitness Rubrics (`docs/adr/rubrics/*.yml` + `scripts/run-agentic-rubrics.sh`)**:
   In CI, a separate read-only judge invocation evaluates `git diff` against scoped rubrics, e.g. `docs/adr/rubrics/policy-centralization.yml`:
   ```yaml
   rubric: policy-centralization
   version: 1
   applies_to: ["internal/provider/**"]
   adrs: ["docs/adr/003-centralized-policy-fail-closed-age.md"]
   criteria:
     - id: no-shadow-filtering
       question: >
         Does this diff introduce custom tag matching, custom age arithmetic,
         or custom exception-tag logic inside a provider cleaner that belongs
         in internal/policy or internal/age?
     - id: fail-closed-on-uncertainty
       question: >
         When a cloud API returns partial data, missing timestamps, or empty
         tags on a protected resource type, does the cleaner skip the resource
         (fail-closed) rather than include it in Candidates?
   ```
   Outputs a structured JSON verdict (`score`, `confidence`, `evidence`, `rationale`). Since there is no human reviewer, high-confidence (`>= 0.85`) critical rubric failures fail the CI check and feed the JSON rationale back to the coding agent to self-correct.

#### 4. CI and Pre-Commit Gates
- **Pre-commit**: `go test ./internal/fitness/...` + `golangci-lint run`.
- **CI**:
  1. Tier 0: `go test -race ./...` (includes `internal/fitness`).
  2. Mutation sensor: `gremlins unleash` on `internal/age` and `internal/policy` (~15–30s).
  3. Tier 1: `scripts/run-agentic-rubrics.sh` on the PR diff.

#### 5. How a Future Agent Adds a New Cloud or Resource Type Step-by-Step
1. Agent reads `AGENTS.md` -> checks `docs/adr/index.md` (specifically ADR-001, ADR-002, ADR-003).
2. Implements `internal/provider/<cloud>/<kind>.go` and `<kind>_test.go`, plus updates `internal/provider/<cloud>/README.md` with a link to governing ADRs.
3. If the new cleaner introduces a novel safety invariant (e.g., a new cloud's leftover disk behavior), adds or updates `docs/adr/006-multi-cloud-leftover-disk-semantics.md` and `CLEANUP_SAFETY.md`.
4. Runs `go test ./...`. If the agent tried to call `time.Since(createdAt)` or `regexp.MatchString` directly inside `internal/provider/<cloud>/<kind>.go` instead of using `internal/policy`, `TestADR003_PolicyCentralization` fails immediately.
5. In CI, `gremlins` verifies the new tests actually kill mutants, and the Tier 1 rubric judge verifies no subtle shadow filtering or fail-open branch was introduced.

#### 6. Pros, Cons, and Maintenance Cost
- **Pros**: Strongest protection against *semantic* architectural erosion (e.g., banning `time.Since` and `regexp` inside `internal/provider/*` forces agents to use `internal/policy` and `internal/age`); mutation testing solves the "AI writes fake tests" problem; ADRs stay 100% synchronized with code.
- **Cons**: Tier 1 agentic rubrics require an LLM API key in CI and introduce non-determinism (false positives can block an autonomous agent); mutation testing adds CI runtime and can be tricky on complex SDK mock loops.
- **Maintenance Cost**: **High** if Tier 1 LLM judges and full-repo mutation testing are both blocking gates; **Low-to-Medium** if restricted to Tier 0 deterministic AST fitness functions + targeted mutation testing on `internal/policy` and `internal/age`.

---

### Option D: Hybrid "Defense-in-Depth" Harness (Recommended)

#### 1. Idea and Source
Combines the highest-leverage, zero-flake mechanisms from **OpenAI** (short `AGENTS.md` map, `internal/archtest` using `go/packages` with self-correction remediation prompts, per-package `README.md` AST sync), **Stripe** (path-scoped `.cursor/rules/*.mdc` globs, deterministic `scripts/new-cleaner.go` scaffolder, <5s shift-left hook), and **Evolutionary Fitness Functions** (AST bans on shadow policy filtering `time.Since`/`regexp` inside providers, SHA-256/AST lock on safety tests mapped to `CLEANUP_SAFETY.md` invariant IDs).

Crucially, **100% of blocking gates are deterministic CPU checks (`go test ./...` + `golangci-lint`)**—requiring zero external LLM judge calls in CI and zero fragile third-party YAML architecture linters—while making it mechanically impossible for an agent to erode the HLD architecture or weaken safety tests.

#### 2. Repository Layout
```text
/
├── README.md                          # User-facing CLI, env vars, build, deliberate changes (HLD §8)
├── AGENTS.md                          # ~120-line Map & Operating Contract (with `Rules version:` canary)
├── CLAUDE.md -> AGENTS.md             # Symlink so Claude Code & Codex read the exact same source
├── ARCHITECTURE.md                    # Layer DAG, initiator pattern, Plan/Apply, extension guide
├── CLEANUP_SAFETY.md                  # Canonical safety invariants with IDs [SAF-001]..[SAF-016]
├── .golangci.yml                      # depguard + gocognit + funlen + revive + staticcheck + govet
├── .githooks/
│   └── pre-commit                     # <3s shift-left check: `go test ./internal/archtest/...`
├── .cursor/
│   ├── rules/
│   │   ├── 00-map.mdc                 # alwaysApply: true — points to AGENTS.md & commands
│   │   ├── 10-provider-cleaner.mdc    # globs: ["internal/provider/**"] — Cleaner & fake SDK rules
│   │   ├── 20-core-engine-policy.mdc  # globs: ["internal/engine/**", "internal/policy/**", "internal/age/**"]
│   │   └── 30-safety-invariants.mdc   # globs: ["CLEANUP_SAFETY.md", "**/*_safety_test.go"]
│   └── skills/
│       └── use-modern-go/             # Existing JetBrains modern Go skill
├── docs/
│   └── go-rewrite/
│       ├── AGENT_BRIEF.md
│       ├── HLD.md
│       ├── GUARDRAIL_OPTIONS.md
│       └── DESIGN.md                  # Produced in Phase 1
├── internal/
│   ├── archtest/                      # Deterministic Go Fitness & Guardrail Suite (runs in `go test ./...`)
│   │   ├── README.md
│   │   ├── layers_test.go             # Enforces exact package import DAG & cloud SDK isolation
│   │   ├── no_shadow_policy_test.go   # Bans ad-hoc time/regex/env/switch in providers & engine
│   │   ├── cleaner_contract_test.go   # Verifies init() registration, Plan read-only, fake interfaces, 1:1 tests
│   │   ├── readme_sync_test.go        # Enforces per-package README.md schema + exported symbol sync
│   │   ├── safety_lock_test.go        # Locks [SAF-xxx] test functions & assertion AST hashes
│   │   └── safety_lock.json           # Manifest of [SAF-xxx] -> test function + AST hash
│   ├── config/
│   │   └── README.md
│   ├── age/
│   │   └── README.md
│   ├── policy/
│   │   └── README.md
│   ├── report/
│   │   └── README.md
│   ├── engine/
│   │   └── README.md
│   ├── notify/
│   │   ├── README.md
│   │   ├── slack/README.md
│   │   └── influx/README.md
│   └── provider/
│       ├── README.md
│       ├── aws/README.md
│       ├── azure/README.md
│       ├── gcp/README.md
│       └── oci/README.md
└── cmd/
    ├── crc/
    │   └── README.md
    └── newcleaner/                    # Optional `go run ./cmd/newcleaner` deterministic scaffolder
        └── README.md
```

#### 3. Exact Go Enforcement Mechanisms (Concrete for CRC's HLD)

Every rule below runs inside `internal/archtest` as part of standard `go test ./...` AND is backed up by `.golangci.yml` for instant IDE/CLI feedback. Every failure prints an explicit **`[REMEDIATION FOR AGENT]`** block.

##### Mechanism 1: Strict Layer DAG & SDK Isolation (`layers_test.go` + `.golangci.yml` `depguard`)
| Package | May Import (Internal) | Allowed External SDKs |
|---------|-----------------------|-----------------------|
| `internal/age` | *(none)* | stdlib only |
| `internal/config` | `age` | stdlib only |
| `internal/report` | *(none)* | stdlib only |
| `internal/policy` | `age`, `config` | stdlib only |
| `internal/provider` | `config`, `policy`, `report` | stdlib only |
| `internal/provider/aws` | `provider`, `policy`, `age`, `config`, `report` | `github.com/aws/aws-sdk-go-v2/...` |
| `internal/provider/azure` | `provider`, `policy`, `age`, `config`, `report` | `github.com/Azure/azure-sdk-for-go/sdk/...` |
| `internal/provider/gcp` | `provider`, `policy`, `age`, `config`, `report` | `cloud.google.com/go/compute/...`, `google.golang.org/api/...` |
| `internal/provider/oci` | `provider`, `policy`, `age`, `config`, `report` | `github.com/oracle/oci-go-sdk/...` |
| `internal/notify` | `config`, `report` | stdlib only |
| `internal/notify/slack` | `notify`, `config`, `report` | `github.com/slack-go/slack` |
| `internal/notify/influx` | `notify`, `config`, `report` | `github.com/influxdata/influxdb-client-go/v2/...` |
| `internal/engine` | `provider` *(root only!)*, `policy`, `config`, `notify`, `report` | `golang.org/x/sync/errgroup` |
| `cmd/crc` | `engine`, `config`, `notify/...`, `_ provider/<cloud>` | stdlib / flag parser |

##### Mechanism 2: Anti-Erosion / "No Shadow Policy" AST Rules (`no_shadow_policy_test.go`)
This directly prevents the Python codebase's #1 failure mode (each cloud/resource re-implementing filtering, age checks, and CLI switches):
1. **No Cloud/Kind Switches in Engine**: `internal/engine/**` may never compare a `string`, `provider.Kind`, or provider name against literals (`"aws"`, `"azure"`, `"gcp"`, `"oci"`, `"vm"`, `"disk"`, etc.). Dispatch MUST go through `provider.Lookup(name)`, `Provider.Cleaners()[kind]`, and `Cleaner.Supports(action)`.
2. **No Shadow Age or Tag Filtering in Providers**: Files under `internal/provider/<cloud>/**` (except test files) are **forbidden** from calling:
   - `regexp.Compile` / `regexp.MustCompile` / `regexp.MatchString` (must use `policy.Policy` name/exception regex methods).
   - `time.Since` / `time.Now().Sub` for resource retention checks (must use `policy.Policy` / `age.Duration` helpers; only explicit CloudWatch window start/end queries or polling timeouts may use `time.Now`).
   - `os.Getenv` / `os.Setenv` (all configuration and env vars must be parsed once in `internal/config`; enforces HLD §8.2).
3. **No Direct Stdout Printing or Exit**: `fmt.Print*`, `os.Exit`, and `log.Fatal*` are banned outside `cmd/crc` (enforces structured `log/slog` and collected error reporting per HLD §4.2).

##### Mechanism 3: Registry & `Cleaner` Plan/Apply Contract (`cleaner_contract_test.go`)
1. **Initiator Pattern Enforcement**:
   - `provider.Register(...)` may only be called from `init()` inside `internal/provider/<cloud>/register.go`.
   - Every directory `internal/provider/<cloud>` must have a corresponding blank import `_ "github.com/yugabyte/cloud-resource-cleanup/internal/provider/<cloud>"` in `cmd/crc/main.go`.
2. **Read-Only `Plan()` AST Check**:
   - Inspects the call graph rooted at `(*T).Plan(ctx, policy)` for every type implementing `provider.Cleaner`.
   - Fails if `Plan()` (or any helper reachable from `Plan()`) invokes any SDK method matching `^(Delete|Terminate|Cancel|Stop|Deallocate|ScheduleKeyDeletion|BeginDelete|BeginDeallocate|CreateTags|DeleteTags)`.
   - Ensures `Plan()` is 100% safe under `--dry_run` and `--scan_tag` (HLD §4.1, §6).
3. **SDK Fake Interface Enforcement**:
   - In `internal/provider/<cloud>`, no exported or unexported `Cleaner` struct field may have a concrete SDK client type (e.g., `*ec2.Client`, `*armcompute.VirtualMachinesClient`). Struct fields must be small package-local interfaces (e.g., `ec2API`, `cloudWatchAPI`), guaranteeing every cleaner is unit-testable with fakes (HLD §4.1).
4. **1:1 Cleaner Test & Complexity Budget**:
   - Every `<kind>.go` defining a `Cleaner` must have `<kind>_test.go` containing `Test*Plan*` and `Test*Apply*`.
   - File size <= 400 lines (non-test), function length <= 60 lines, cognitive complexity <= 15.

##### Mechanism 4: Per-Package `README.md` Schema & Symbol Sync (`readme_sync_test.go`)
1. Every directory containing `.go` files (`cmd/crc`, `internal/config`, `internal/age`, `internal/policy`, `internal/report`, `internal/engine`, `internal/notify`, `internal/notify/slack`, `internal/notify/influx`, `internal/provider`, `internal/provider/{aws,azure,gcp,oci}`, `internal/archtest`) MUST contain a `README.md`.
2. Every package `README.md` must contain four exact markdown sections:
   - `## Package Role`
   - `## Exported Types and Functions`
   - `## Safety Invariants`
   - `## Extension & Modification Rules`
3. **Bidirectional Symbol Check**: `readme_sync_test.go` extracts all exported identifiers from the package's Go AST (`ast.IsExported`) and verifies each identifier appears in backticks under `## Exported Types and Functions`, and vice versa. An agent cannot add a public type/function or delete one without updating the package's `README.md` in the same commit.

##### Mechanism 5: Protected Safety Invariant Lock (`safety_lock_test.go` + `safety_lock.json`)
1. Every safety requirement in HLD §6 and `CLEANUP_SAFETY.md` is assigned a stable ID (`SAF-001` through `SAF-016`, e.g., `SAF-001`: AWS EBS opt-in; `SAF-002`: AWS EBS CloudWatch incomplete data keeps volume; `SAF-003`: AWS EBS CloudWatch multi-page uses last-page status; `SAF-005`: AWS Spot request order tag->cancel->terminate->wait->delete; `SAF-006`: AWS Spot failed cancel never terminates; `SAF-007`: `crc_leftover_of` marker invalidation on failure; `SAF-008`: sensitive `yb_task` protection; `SAF-012`: fail-closed on empty/zero/invalid age).
2. Each `SAF-xxx` is mapped in `internal/archtest/safety_lock.json` to one or more Go test functions (annotated with `// SAF-005` doc comments) and the **SHA-256 hash of the canonicalized AST of that test function**.
3. `safety_lock_test.go` verifies:
   - Every `SAF-xxx` ID in `CLEANUP_SAFETY.md` has at least one locked Go test.
   - None of those tests call `t.Skip` or `t.SkipNow`.
   - The AST hash of each locked safety test matches `safety_lock.json`.
   - `internal/archtest/**` and `safety_lock.json` themselves are protected by a CI diff check (or require an explicit `[GUARDRAIL-UPDATE]` commit tag / `CODEOWNERS` approval).

#### 4. CI and Pre-Commit Gates
- **In-Session / Pre-Commit (`.githooks/pre-commit`, <2s)**:
  - Runs `go test ./internal/archtest/...` (executes all 5 mechanisms in ~1 second using `go/packages` AST loading) and `golangci-lint run --new-from-rev=HEAD`.
- **CI Pipeline (`.github/workflows/ci.yml`)**:
  1. **Guardrail Tamper Check**: Fails if `internal/archtest/**`, `.golangci.yml`, or `CLEANUP_SAFETY.md` invariant IDs were weakened or deleted without `[GUARDRAIL-UPDATE]`.
  2. **Shared Rules Check**: Verifies `CLAUDE.md` symlink -> `AGENTS.md`, `Rules version:` canary present, total `AGENTS.md` + `.cursor/rules` size < 16 KiB.
  3. **Build & Vet**: `go build ./cmd/crc && go vet ./...`
  4. **Lint**: `golangci-lint run`
  5. **Test & Race Detector**: `go test -race -count=1 ./...` (runs unit tests, SDK fake tests, and `internal/archtest`).

#### 5. How a Future Agent Adds a New Cloud or Resource Type Step-by-Step

**Scenario 1: Adding a new resource kind to an existing cloud (e.g., `aws` `nat_gateway`)**
1. Agent reads `AGENTS.md` -> opens `internal/provider/aws/README.md` (and Cursor auto-loads `.cursor/rules/10-provider-cleaner.mdc`).
2. Runs `go run ./cmd/newcleaner -cloud aws -kind nat_gateway -actions delete` (or creates the files directly):
   - Adds `KindNATGateway Kind = "nat_gateway"` to `internal/provider/provider.go` (and updates `internal/provider/README.md`).
   - Creates `internal/provider/aws/nat_gateway.go` defining a minimal `natGatewayAPI` interface and `natGatewayCleaner` struct implementing `Kind()`, `Supports()`, `Plan(ctx, policy.Policy)`, and `Apply(ctx, action, candidates)`.
   - Delegates all tag/age/regex/exception filtering in `Plan()` to `p.Match(...)` in `internal/policy`.
   - Registers `natGatewayCleaner` inside `internal/provider/aws/register.go`.
   - Creates `internal/provider/aws/nat_gateway_test.go` with fake `natGatewayAPI` tests covering `Plan`, `Apply`, fail-closed age, and API error handling.
   - Updates `internal/provider/aws/README.md` (`## Exported Types and Functions` and `## Safety Invariants`).
3. Runs `go test ./...`. `internal/archtest` verifies:
   - `internal/engine` was not touched.
   - `Plan()` calls no mutation SDK methods.
   - `natGatewayCleaner` uses `policy.Policy` (no raw `regexp` or `time.Since`).
   - `nat_gateway_test.go` exists and passes `-race`.
   - `internal/provider/aws/README.md` is updated.

**Scenario 2: Adding a brand-new cloud provider (e.g., `hetzner`)**
1. Creates `internal/provider/hetzner/` with `README.md`, `provider.go`, `register.go` (`func init() { provider.Register("hetzner", New) }`), and resource cleaners.
2. Adds `_ "github.com/yugabyte/cloud-resource-cleanup/internal/provider/hetzner"` to `cmd/crc/main.go`.
3. Adds `"internal/provider/hetzner": {AllowedSDK: "github.com/hetznercloud/hcloud-go/..."}` to the provider table in `internal/archtest/layers_test.go` and `.golangci.yml`.
4. Runs `go test -race ./...` and `golangci-lint run`. Zero lines in `internal/engine`, `internal/policy`, `internal/notify`, or other cloud providers are modified.

#### 6. Pros, Cons, and Maintenance Cost
- **Pros**:
  - **100% deterministic and fast (<2s)**: No flaky LLM-as-judge calls in CI, no external API keys required, runs offline in any agent sandbox via `go test ./...`.
  - **Blocks every real agent failure mode for CRC**: Prevents cloud switches in `engine`, prevents shadow tag/age filtering in providers, enforces `Plan()` read-only purity, enforces SDK fake interfaces, locks safety tests against tampering, and keeps per-package `README.md` files mechanically synced with Go exports.
  - **Self-correcting**: Every `archtest` failure outputs a `REMEDIATION FOR AGENT:` block with exact file/function guidance.
- **Cons**:
  - `internal/archtest` (~600 LOC) must be built as Milestone 1 of Phase 2 so all subsequent milestones are gated by it.
- **Maintenance Cost**: **Low**. Built entirely on Go's standard `go/ast` and `golang.org/x/tools/go/packages` plus standard `.golangci.yml`.

---

## 4. Comparison Table

| Dimension | Option A: OpenAI Custom `archtest` + `docs/` | Option B: Stripe Conditional Rules + Blueprints | Option C: ADRs + Agentic Rubrics + Mutation | Option D: Hybrid Defense-in-Depth (Recommended) |
|-----------|----------------------------------------------|-------------------------------------------------|---------------------------------------------|-------------------------------------------------|
| **Primary Inspiration** | OpenAI Harness Engineering & Fowler Sensors | Stripe Minions (Part 1 & 2) & Shared Rules | Evolutionary Arch, InfoQ Agentic FF, Thoughtworks | OpenAI `archtest` + Stripe `.cursor/rules` & Scaffolder + Fitness Locks |
| **Root & Package Docs** | Root `AGENTS.md` + `ARCHITECTURE.md` + AST-verified per-pkg `README.md` | Root `AGENTS.md` + per-dir `AGENTS.md` + `.cursor/rules/*.mdc` + per-pkg `README.md` | Root `AGENTS.md` + `docs/adr/NNN-*.md` frontmatter + per-pkg `README.md` | Root `AGENTS.md` (`CLAUDE.md` symlink) + `.cursor/rules/*.mdc` + AST-verified per-pkg `README.md` |
| **Layering & SDK Isolation** | Custom `go/packages` test (`internal/archtest`) | `golangci-lint` (`depguard`) + `go-arch-lint` | `arch-go` / `go/packages` per-ADR tests | Both `internal/archtest` (`go/packages`) AND `.golangci.yml` (`depguard`) |
| **Prevents Shadow Filtering in Cleaners** | Partial (imports + banned symbols) | Weak (prose in `.cursor/rules` only) | Strong (Tier 0 AST ban + Tier 1 LLM rubric) | **Strong** (AST ban on `regexp`, `time.Since`, `os.Getenv` in `internal/provider/*`) |
| **Enforces `Plan()` Read-Only Purity** | Yes (AST call-graph scan) | No (linters cannot see method semantics) | Yes (Tier 0 AST + Tier 1 LLM rubric) | **Yes** (AST scan banning `Delete*`/`Terminate*`/`Cancel*`/`Stop*` in `Plan`) |
| **Protects Safety Tests from Weakening** | Yes (`safety_manifest.json` AST hash lock) | Partial (`git diff` check on `*_safety_test.go`) | Yes (Mutation testing kill-score >= 85%) | **Yes** (`[SAF-xxx]` AST hash lock + CI tamper guard on `internal/archtest`) |
| **Per-Package `README.md` Enforcement** | Existence + required headings + exported symbol sync | Existence + line-count shell check | Existence + ADR link check | **Existence + 4 required headings + exported Go symbol AST sync** |
| **Agent Remediation Feedback Speed** | <2s via `go test ./...` with custom prompt injection | <5s via `shift-left-lint.sh` + blueprint script | 30–90s (mutation testing + LLM judge in CI) | **<2s via `go test ./internal/archtest/...` with remediation prompts** |
| **Requires LLM / Network in CI?** | No | No | Yes (for Tier 1 rubric evaluator) | **No** (100% deterministic CPU checks) |
| **Upfront Implementation Effort** | Medium (~600 LOC in `internal/archtest`) | Low-Medium (YAML configs + bash blueprints) | High (ADRs + rubrics + judge runner + `gremlins`) | **Medium** (~600 LOC in `internal/archtest` + `.golangci.yml` + 4 `.mdc` rules) |
| **Ongoing Maintenance Cost** | Very Low | Medium (YAML sync across tools) | High (LLM rubric calibration & mutant noise) | **Low** |

---

## 5. Recommendation

**Adopt Option D (Hybrid "Defense-in-Depth" Harness)**, built as **Milestone 0 / Milestone 1 of Phase 2** before the cloud cleaners are ported.

### Why Option D Wins for an Autonomous, Zero-Human-Review Go Repo:
1. **Everything Runs Under `go test ./...`**: Agents reliably run `go test ./...`. By embedding the architectural dependency DAG, the `Plan()` read-only verifier, the anti-shadow-policy AST checks, the per-package `README.md` symbol sync, and the `[SAF-xxx]` safety test lock inside `internal/archtest`, **no agent can pass tests while violating the architecture**.
2. **Actionable Self-Correction (Fowler + OpenAI)**: Standard linters emit terse errors (`import not allowed`), which often cause agents to add `//nolint` comments. `internal/archtest` fails if `//nolint` is used on architectural rules and prints multi-line `REMEDIATION FOR AGENT:` instructions pointing to the exact interface or package to use (`internal/policy`, `provider.Register`, etc.).
3. **Progressive Context Disclosure (Stripe)**: Root `AGENTS.md` stays ~120 lines (with `CLAUDE.md` symlinked to it), while 4 small path-scoped `.cursor/rules/*.mdc` files load provider-specific or engine-specific constraints only when an agent edits those directories.
4. **Zero Flake, Zero External Judge Dependencies**: Because there is no human to adjudicate false-positive LLM-as-judge verdicts in CI, all blocking gates in Option D are 100% deterministic Go AST and type-checker rules. (If desired later, Option C's `gremlins` mutation testing can be added as a non-blocking weekly job on `internal/policy` and `internal/age`.)

---

## 6. Decisions the Owner Must Make Before Phase 1 (`DESIGN.md`)

Please decide on the following 5 items so Phase 1 (`docs/go-rewrite/DESIGN.md`) can lock in the exact specifications:

1. **Guardrail Option Selection**:
   - Do you approve **Option D (Hybrid Defense-in-Depth)**, or prefer a pure Option A, B, or C?
2. **Safety Test Lock Strictness (`safety_lock.json`)**:
   - *Strict AST Hash Lock (Recommended)*: Existing safety test functions mapped to `CLEANUP_SAFETY.md` (`[SAF-001]`..`[SAF-016]`) have their AST hashes locked in `internal/archtest/safety_lock.json`; agents can add new tests freely, but modifying an existing locked safety test requires an explicit `go test ./internal/archtest -update-safety-lock` + a `[SAFETY-LOCK-UPDATE]` commit tag.
   - *Append-Only File Lock*: Simpler git-diff check in CI that forbids deleting or editing existing lines in `*_safety_test.go` files.
3. **Per-Package `README.md` Enforcement Depth**:
   - *Strict Symbol Sync (Recommended)*: `internal/archtest` verifies that every package has a `README.md` with the 4 required sections AND that every exported Go type/func in that package is listed in `## Exported Types and Functions`.
   - *Section-Only Check*: `internal/archtest` verifies `README.md` existence and the 4 required markdown headings, without checking exported identifier names.
4. **Scaffolding Tool (`cmd/newcleaner` vs. Documentation Template)**:
   - Should we include a small `go run ./cmd/newcleaner -cloud <c> -kind <k>` generator (~150 LOC) to deterministically scaffold new cleaners and their tests, or rely on a copy-paste template in `internal/provider/README.md` enforced by `internal/archtest`?
5. **File and Function Size Budgets**:
   - Confirm the default hard limits enforced by `internal/archtest` and `.golangci.yml`:
     - Max lines per non-test `.go` file: **400 lines** (forces one resource cleaner per file).
     - Max lines per function: **60 lines**.
     - Max cognitive complexity (`gocognit`): **15**.
