# CRC Go Rewrite — High-Level Design

Status: draft for the implementing agent. This document fixes constraints,
invariants and the architectural shape. The detailed design (exact types,
SDK versions, file-by-file plan) belongs in `docs/go-rewrite/DESIGN.md`,
which the implementing agent writes.

Source of truth for current behaviour: the Python code on `main`
(`crc.py`, `crc/**`), `README.md`, `CLEANUP_SAFETY.md`, and `tests/**`.

---

## 1. What CRC is

A CLI run from Jenkins (`cloud-resource-cleanup-triggers` repo) that deletes
or stops leftover test cloud resources across AWS, Azure, GCP and OCI, gated by
tags, name regexes, resource state and age. It supports dry-run, Slack
notifications, InfluxDB metrics and a read-only `--scan_tag` mode.

Today it is a single 1650-line `crc.py` orchestrator with a `CRC` class that
switches on `cloud` and `resource` strings, plus one Python class per
cloud/resource that each re-implement tag filtering, age checks, dry-run and
reporting slightly differently.

## 2. Goals

1. Rewrite in Go as a single static binary, `crc`.
2. Make the core cloud-agnostic. Adding a cloud or a resource type must not
   touch the engine, the CLI, or other providers.
3. Preserve every safety behaviour in `CLEANUP_SAFETY.md` (section 6).
4. Keep the Jenkins CLI contract working without edits to the triggers repo
   (section 7).
5. Port the existing safety tests to Go; parity with them is the acceptance bar.

Non-goals: new resource types, a long-running service, a UI.

## 3. The "initiator" pattern (provider self-registration)

Interpretation: the user asked for an "initiator pattern". We implement it as
self-registration in `init()`, the same model `database/sql` drivers and
`image` decoders use:

```go
// internal/provider/aws/register.go
func init() {
    provider.Register("aws", New) // New is a provider.Factory
}

// cmd/crc/main.go
import (
    _ "github.com/yugabyte/cloud-resource-cleanup/internal/provider/aws"
    _ "github.com/yugabyte/cloud-resource-cleanup/internal/provider/azure"
    _ "github.com/yugabyte/cloud-resource-cleanup/internal/provider/gcp"
    _ "github.com/yugabyte/cloud-resource-cleanup/internal/provider/oci"
)
```

The engine only ever sees `provider.Lookup(name)` and the interfaces below.
Within a provider, each resource kind registers itself with that provider the
same way, so a provider is a small registry of `Cleaner`s.

If a narrower or different meaning of "initiator" was intended, change this
section before implementation starts.

## 4. Architecture

```
cmd/crc/                  CLI: flag parsing, legacy-format decoding, wiring
internal/config/          Typed run config + validation (no env mutation)
internal/engine/          Runner: select cleaners, run, collect Report
internal/policy/          Shared filter logic: tags, notags, exception tags,
                          name/exception regex, states, age, custom age tag,
                          max age, sensitive yb_task, managed-node skip hooks
internal/age/             Duration type, parsing of {'days','hours'}, is-old
internal/provider/        Registry, Provider, Cleaner, Resource, Kind types
internal/provider/aws/    EC2, EBS, EIP, keypair, VPC, KMS, spot requests,
                          snapshot; CloudWatch; region discovery
internal/provider/azure/  VM, spot VM, disk, public IP, NIC
internal/provider/gcp/    VM, spot VM, disk, IP
internal/provider/oci/    VM, spot VM, disk/boot volume
internal/notify/          Notifier interface; slack/ and influx/ sinks
internal/report/          Report model consumed by notifiers and stdout
```

### 4.1 Core interfaces (sketch; agent finalises)

```go
type Kind string // "vm", "disk", "ip", "keypair", "vpc", "kms", "nic",
                 // "spot_instance_requests", "spot_instances", "snapshot"

type Action string // "delete", "stop"

type Provider interface {
    Name() string
    Cleaners() map[Kind]Cleaner
}

type Factory func(ctx context.Context, cfg config.Provider) (Provider, error)

type Cleaner interface {
    Kind() Kind
    Supports(Action) bool
    // Plan lists and filters. Read-only. Must be safe under dry-run.
    Plan(ctx context.Context, p policy.Policy) ([]Candidate, error)
    // Apply executes the action for planned candidates. Never called in dry-run.
    Apply(ctx context.Context, a Action, cs []Candidate) (Result, error)
}

type Candidate struct {
    ID, Name, Region, State, Type, ConsoleURL string
    Tags      map[string]string
    CreatedAt time.Time
    Related   []Candidate // e.g. NICs, leftover disks reported separately
}
```

Plan/Apply split gives dry-run for free and makes Slack/Influx reporting one
code path. Cleaners whose safety depends on step ordering (AWS spot requests,
spot VMs with leftover disks) keep that ordering inside `Apply`; the engine
does not reorder.

Each provider talks to its SDK through small interfaces it owns (for example
`ec2API` with just the methods used), so tests use fakes rather than live
clouds.

### 4.2 Execution model

- `context.Context` everywhere; SIGINT/SIGTERM cancels.
- Regions processed with bounded concurrency (`errgroup` with a limit).
  Per-region and per-resource errors are collected, not swallowed; the
  process exits non-zero if any destructive step failed, matching Jenkins'
  expectation that failures fail the build.
- Unreachable regions are logged and skipped (current AWS behaviour), but
  auth failures on region listing still fail the run.
- Structured logging with `log/slog`; text to stderr, optional file.

## 5. Resource matrix (must match `main`)

| Cloud | Kinds | Stop |
|-------|-------|------|
| AWS   | disk, ip, keypair, vm, vpc, kms, spot_instance_requests, snapshot | vm |
| Azure | disk, vm, ip, nic, spot_instances | vm |
| GCP   | disk, ip, vm, spot_instances | vm |
| OCI   | vm, disk, spot_instances | — (confirm against code) |

## 6. Safety invariants to preserve

Every item below is current behaviour in `CLEANUP_SAFETY.md` or the code and
must survive the rewrite, with a Go test where the Python suite has one.

- AWS EBS is opt-in: only runs with explicit `--cloud aws --resource disk`.
- AWS EBS `--detach_age` via CloudWatch metrics; incomplete or failed metric
  answers keep the volume. Multi-page `GetMetricData` uses last-page status.
  CreateTime floor rules as documented.
- GCP disk detach age via `last_detach_timestamp`.
- AWS spot instance requests: filtering on request tags; untagged requests
  skipped; order is tag DoT=false volumes, cancel, terminate, wait for EBS
  `available`, delete volumes. Failed cancel never terminates. `crc_leftover_of`
  and `crc_leftover_tag_*` marker scheme, invalidation on failure, and the
  region sweep for tagged leftovers, exactly as documented.
- Sensitive `yb_task` values protect volumes (same list as `crc/aws/disk.py`).
- Leftover disks: Azure `delete_option=Detach`/unset, GCP `autoDelete=false`
  after the zone op completes, OCI attached block volumes after `TERMINATED`.
- Skip managed members: GKE/MIG on GCP, OKE/instance pools on OCI.
- Spot modules: custom age tag absent means use `--age`; present but empty,
  unparseable, invalid or zero means skip the resource.
- GCP/OCI `spot_instances` require explicit `--cloud gcp|oci`.
- `--scan_tag` is read-only and forces dry-run.
- KMS requires key description and user ARN; pending window 7..30 days.

## 7. CLI contract

Keep every flag name and short alias from `crc.py get_argparser()` so the
Jenkins triggers keep working unchanged. Dict and list flags
(`--filter_tags`, `--exception_tags`, `--notags`, `--age`, `--detach_age`,
`--max_age`, `--influxdb`, `--resource_states`, `--name_regex`,
`--exception_regex`) are currently passed as Python literals, e.g.
`"{'test_task': ['stress-test']}"`. The Go CLI must accept both that form and
JSON. Write a small, tested literal decoder; do not shell out to Python.

Environment variables stay the same (`AWS_*`, `AZURE_CREDENTIALS_*`,
`GOOGLE_APPLICATION_CREDENTIALS`, OCI config, `SLACK_BOT_TOKEN`,
`INFLUXDB_TOKEN`).

## 8. Deliberate behaviour changes

These are decisions, not accidents. Document each in the Go README.

1. Fail closed on age. `is_old({})` returning true is removed. Every
   destructive cleaner requires a positive age (or a cleaner-specific
   equivalent such as detach age). Non-spot modules that fail open on a bad
   custom age tag today will skip instead.
2. No `MAX_AGE` environment mutation. `--max_age` is a config value passed to
   the policy. It caps custom age tags only and must not shorten `--age` or
   `--detach_age` floors.
3. `--cloud all --resource all` currently always raises on aws+disk. The Go
   CLI rejects unsupported combinations up front with a clear error, before
   any API call, instead of failing mid-run.
4. Azure fixes (known bugs on `main`):
   - VMs are listed subscription-wide (`list_all`) but status/stop use the
     configured resource group. Use the resource group parsed from each VM's
     ID, or list by resource group; pick one and test it.
   - Stop uses power-off, which keeps billing. Stop must deallocate.
   - `instance_view.statuses[1]` is read without a bounds check; VMs in
     failed provisioning (single status) crash and are never cleaned. Find
     the `PowerState/*` status by prefix.
5. Drop unused dependencies (`paramiko`, `requests`, `beautifulsoup4`).

## 9. Notifications and metrics

- `Notifier` interface fed by the run `Report`. Slack and InfluxDB are
  optional sinks enabled by flags.
- Slack: Block Kit, running items first then stopped/other, chunked at about
  2800 chars and 20 items per message with "Part N/M" headers, retry on API
  errors. Keep the GCP disk user-mention feature (`--slack_notify_users`,
  `--slack_user_label`).
- InfluxDB v2 line protocol with the same measurement layout as today
  (spot requests and instances under VMS, leftover volumes under DISKS).
- Notifier failures are logged and never abort cleanup.

## 10. Testing

- Port `tests/test_aws_disk.py`, `tests/test_aws_spot_instance_requests.py`,
  `tests/test_azu_spot_vm.py`, `tests/test_gcp_spot_vm.py`,
  `tests/test_oci_spot_vm.py` as table-driven Go tests against SDK fakes.
- Unit tests for the literal decoder, age parsing, policy matching, Slack
  chunking.
- `go vet`, `staticcheck` (if available) and `go test -race ./...` must pass.

## 11. Tooling

- Module: `github.com/yugabyte/cloud-resource-cleanup`, `go 1.24` (local
  toolchain is 1.24.1).
- SDKs: AWS SDK for Go v2, Azure SDK for Go (`azidentity`, `armcompute`,
  `armnetwork`), `cloud.google.com/go/compute`, `github.com/oracle/oci-go-sdk`,
  `github.com/slack-go/slack`, `github.com/influxdata/influxdb-client-go/v2`.
  Agent confirms current major versions.
- Follow the `use-modern-go` skill
  (https://github.com/JetBrains/go-modern-guidelines) for every Go file.
- The Python code stays in place until the Go binary reaches parity; the Go
  code lives alongside it on this branch.
