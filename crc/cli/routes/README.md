# crc.cli.routes

## Purpose

One route table per cloud (`aws.py`, `azu.py`, `gcp.py`, `oci.py`): the set of resource kinds the
CLI runs through `crc.core.engine` instead of the legacy `CRC` handler. `crc/cli/dispatch.py`
asks `crc.cli.bridge.route_for(cloud, kind)` before it looks up the legacy handler. A cloud's lane
edits only its own table and `crc/<cloud>/**`.

## Public API

- `Route`: frozen value of one routed kind: a flags-to-cleaner-options function, a flag that turns Slack and Influx off (vpc), and an optional gate run before the cleaner.
- `OptionsBuilder`: type alias of a function from the parsed flags to the options dict of the cleaner.
- `Precheck`: type alias of a gate function taking the run object, the flags and the targets.

## Safety Invariants

- A kind that is not in a table keeps its legacy handler; nothing is routed implicitly.
- The table module imports the cleaner package of its cloud, which registers the cleaner; the registry decides what runs, the route only maps flags to options and says whether to notify.
- Option values are the raw flag values the legacy handler passed (`None` stays `None`); the cleaner factory normalises them.

## Extension Rules

1. To route a kind, add `kind: Route(builder)` to `ROUTES` of the cloud file and an `_kind` options builder that returns the keys the cleaner factory reads from `context.options`.
2. Import the cleaner package in the cloud file (`import crc.<cloud>.<pkg>  # noqa: F401`) so it is registered.
3. Retarget the keypair-style tests (see `crc/cli/README.md`, Extension Rules) and delete the adapter and its `CRC` method.
4. Keep every file at 250 lines or fewer.
