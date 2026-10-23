# crc.cli.routes

## Purpose

One route table per cloud (`aws.py`, `azu.py`, `gcp.py`, `oci.py`): the set of resource kinds the
CLI runs through `crc.core.engine` instead of the legacy `CRC` handler. `crc/cli/dispatch.py`
asks `crc.cli.bridge.route_for(cloud, kind)` before it looks up the legacy handler. A cloud's lane
edits only its own table and `crc/<cloud>/**`.

## Public API

- `Route`: frozen value of one routed kind: a flags-to-cleaner-options function, a `NotifyMode`, an optional gate run before the cleaner, optional extra notifiers and an optional after-run hook.
- `NotifyMode`: the members none (no Slack, no Influx: vpc and snapshot), report (after a successful run) or report-then-reraise (also report what was done when the cleaner raises, then raise it: AWS disk).
- `ExtraNotifiers`: type alias of a function from the run object to notifiers that run after Slack and Influx (for a message the report does not carry; no route needs it yet: the Azure VM NIC Slack message after the VM message comes from the report, its slack ids).
- `AfterRun`: type alias of a function taking the run object, the flags and the engine outcomes; runs after the notifiers (the snapshot console line).
- `OptionsBuilder`: type alias of a function from the parsed flags to the options dict of the cleaner.
- `Precheck`: type alias of a gate function taking the run object, the flags and the targets.

## Safety Invariants

- A kind that is not in a table keeps its legacy handler; nothing is routed implicitly. `aws.py` routes `disk`, `ip`, `keypair`, `kms`, `snapshot`, `spot_instance_requests`, `vm` and `vpc`; `azu.py` (cloud name `azure`) routes `disk` (report then re-raise, as `delete_disks`), `ip`, `nic`, `spot_instances` (its `precheck` raises `ValueError` for an empty `--resource_group` before the cleaner, as `delete_spot_instances` did) and `vm` (delete and stop); `gcp.py` and `oci.py` keep the legacy handlers.
- The table module imports the cleaner package of its cloud, which registers the cleaner; the registry decides what runs, the route only maps flags to options and says whether to notify.
- Option values are the raw flag values the legacy handler passed (`None` stays `None`); the cleaner factory normalises them.

## Extension Rules

1. To route a kind, add `kind: Route(builder)` to `ROUTES` of the cloud file and an `_kind` options builder that returns the keys the cleaner factory reads from `context.options`.
2. Import the cleaner package in the cloud file (`import crc.<cloud>.<pkg>  # noqa: F401`) so it is registered.
3. Retarget the keypair-style tests (see `crc/cli/README.md`, Extension Rules) and delete the adapter and its `CRC` method.
4. Keep every file at 250 lines or fewer.
