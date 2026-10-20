# Owner decisions for the Go rewrite

Recorded 2026-10-20. These answer the questions at the end of
`GUARDRAIL_OPTIONS.md` and are binding for `DESIGN.md` and the implementation.

1. **Guardrail option: D (Hybrid Defense-in-Depth)** from `GUARDRAIL_OPTIONS.md`.
2. **Safety tests: strict AST hash lock.** Each `SAF-xxx` invariant in
   `CLEANUP_SAFETY.md` maps to locked Go tests in
   `internal/archtest/safety_lock.json`. Locked tests cannot be deleted,
   skipped or changed without regenerating the lock.
3. **Package READMEs: strict symbol sync.** Every package with Go files has a
   `README.md` with the four required sections, and every exported identifier
   is listed under `## Exported Types and Functions` (and vice versa).
4. **Scaffolder: yes.** Ship `cmd/newcleaner` as the deterministic way to add a
   cleaner (code, test, registration, README entry).
5. **Size budgets:** 400 lines per non-test file, 60 lines per function,
   cognitive complexity 15. Split into small helpers rather than raising limits.
6. **Guardrail changes need human approval.** Add `.github/CODEOWNERS` that
   assigns `@Schitiz` to `internal/archtest/`, `internal/archtest/safety_lock.json`,
   `.golangci.yml`, `.github/`, `CLEANUP_SAFETY.md`, `AGENTS.md`,
   `ARCHITECTURE.md`, `.cursor/rules/` and `docs/go-rewrite/DECISIONS.md`.
   Agents must never edit these after Milestone 0 is merged, except to add
   lock entries for new safety tests. A `[GUARDRAIL-UPDATE]` commit tag is not
   approval. The owner enables branch protection with required CODEOWNERS
   review on GitHub.

Refinements from review of the options:

- The read-only `Plan()` check starts as an AST check of the `Plan` method
  body and the same-package helpers it calls directly, not a full call graph.
- The `time.Since` / `time.Now` ban in providers has an explicit allowlist for
  polling and waits, and CloudWatch query windows, declared in
  `internal/archtest`.
- Do not cite sources in repo docs that you have not verified.
