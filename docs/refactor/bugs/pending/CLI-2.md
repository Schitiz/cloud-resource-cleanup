# CLI-2 pending bugs and quirks

Rung CLI-2 (the `CRC` class moved to `crc/cli/`). Columns as in `docs/refactor/BUGS.md`; ID is
`NEW`; locations are `git show main:crc.py` lines. Nothing here is fixed.

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| NEW | `ping_on_slack` writes any `operation_type` string into the message on main, but the delegating code behind `crc.cli.notify` (`SlackNotifier.ping_owners`) only knows `Deleted` and `Stopped`: `ping_on_slack("Disk", "Gone", {...})` raises `KeyError: 'Gone'` instead of sending `Gone the following ...`. Unreachable from the CLI (the only caller passes `DELETED`); found by `tests/test_cli_crc_parity.py` (the case is left out of its table). `get_msg` was moved back to the exact `main` f-strings in this rung and matches for any string | `crc.py:249`, `:251`, `:493` | yes (behaviour differs now) | cosmetic | low | CLI-2 | open |
| NEW | The `GCP_SpotVM` branch of `delete_spot_instances` checks `if not self.project_id` (`project_id is required for GCP Spot VM cleanup`), but `CRC.__init__` already raised `project_id is mandatory Parameter for GCP` for a `gcp` object without a project, so that branch is unreachable unless the attribute is cleared after construction | `crc.py:88`, `:618-619` | yes | cosmetic | low | CLI-2 | open |
| NEW | `notify_deleted_nic_via_slack` is defined twice on main and the first definition (`nic.get_deleted_nic`, `:337-352`) is dead code; it was dropped in `crc/cli/notify.py` (ruff F811) with no behaviour change. The second definition (`nic.get_deleted`) is the one that runs, also for the Azure NIC message after a VM delete (`BUG-028`) | `crc.py:337-352`, `:456-471` | yes | cosmetic | low | CLI-2 | open |
