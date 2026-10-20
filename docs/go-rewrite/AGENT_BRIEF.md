# Brief for the implementing agent

You are rewriting this repository (Python, `crc.py` + `crc/**`) in Go on
branch `refactor/go-rewrite`. Read these first, in order:

1. `docs/go-rewrite/HLD.md` — constraints, invariants, architecture shape.
2. `CLEANUP_SAFETY.md` — safety behaviour that must survive.
3. `README.md` — user-facing features and CLI.
4. `crc.py`, then every module under `crc/`, then `tests/`.

## Rules

- Work only on branch `refactor/go-rewrite`. Commit and push there with
  clear messages. Never force-push, rewrite history, or touch other branches.
- Do not call real cloud APIs, Slack or InfluxDB. No credentials are needed;
  use fakes in tests.
- Keep the Python code untouched. Go code lives alongside it.
- Go code: before writing or editing each Go file, use the `use-modern-go`
  skill in `.cursor/skills/use-modern-go`
  (`sh .cursor/skills/use-modern-go/scripts/run-tool.sh list --go-version 1.24`)
  and follow the guidelines it returns. Source:
  https://github.com/JetBrains/go-modern-guidelines
- Where HLD.md and the Python code disagree, HLD.md wins only for the items
  listed in its section 8 (deliberate changes). Everywhere else, match the
  Python behaviour and note any ambiguity in DESIGN.md under "Open questions".

## Phase 1 — design (this run, unless told otherwise)

Produce `docs/go-rewrite/DESIGN.md`. Write no Go code in this phase.
DESIGN.md must contain:

1. Final package layout and the exported types/interfaces with signatures.
2. How provider and per-resource self-registration works (`init()`), and how
   `cmd/crc` wires it.
3. The policy/filter model and how each Python module's filtering maps onto it.
   Call out every place where Python modules differ from each other today.
4. A table mapping each Python module to its Go package/file, with the
   safety invariants it carries.
5. SDK choices with module paths and versions, and the SDK-facing interfaces
   each provider defines for testability.
6. CLI flag table: every flag from `get_argparser()`, its Go type, and how the
   Python-literal / JSON decoding works.
7. Error handling, concurrency, logging and exit-code rules.
8. Test plan: each Python test file and test case mapped to a Go test.
9. Implementation order (milestones) small enough to verify one at a time.
10. Open questions for the human reviewer.

## Phase 2 — implementation (separate run, after DESIGN.md is approved)

Implement DESIGN.md milestone by milestone. After each milestone run
`go build ./...`, `go vet ./...` and `go test -race ./...` and fix failures
before moving on. Finish with a Go section in README.md covering build, usage
and the deliberate behaviour changes.
