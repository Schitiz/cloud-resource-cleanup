# W2-CLI review

## Coding summary

Wave W2 lane W2-CLI: structure-only split of six files to 250 lines or fewer, plus dedupe of the
Slack/Influx report boilerplate. No behaviour change; no test was edited.

- **Files split (before -> after lines, `wc -l`).**
  - `crc/cli/args.py` 290 -> 139; the age, notify and resource flag groups moved to new `crc/cli/args_run.py` (157). Flag order is unchanged (`get_argparser` still calls the groups in the old order).
  - `crc/cli/dispatch.py` 267 -> 245; the pair table and unsupported-pair message moved to new `crc/cli/pairs.py` (36). `dispatch` re-exports `SUPPORTED_CLOUDS` and `is_supported_pair`; `HANDLERS`, `Snapshot`, `make_crc` and `AWS_DISK_OPT_IN_MESSAGE` stay in `dispatch`, so tests that patch them still hit the code.
  - `crc/cli/resource_ops.py` 314 -> 237 and `crc/cli/vm_ops.py` 299 -> 235 (dedupe, below). The adapter classes stay module globals of these two files and are looked up at call time, so `monkeypatch.setattr(resource_ops|vm_ops, "<Adapter>", ...)` in `tests/test_cli_crc_parity.py`, `test_core_engine.py`, `test_core_report.py` and `test_cli_dispatch_fix.py` still takes effect.
  - `crc/core/policy.py` 362 -> 16; now a facade (star re-export with `__all__` per module) over `policy_tags.py` (175), `policy_text.py` (85), `policy_managed.py` (127) and `policy_age.py` (46). `from crc.core import policy`, `crc.core.__init__` and `policy.<name>` work as before; `crc.core` imports no cloud, cli or notify package.
  - `crc/notify/slack.py` 325 -> 213; message splitting moved to `slack_chunks.py` (48), the posting, user lookup and owner-ping methods to `slack_owners.py` (96, class `SlackPoster`, base of `SlackNotifier`). `human_readable_timedelta`, `_format_item_row`, `send_slack_message` (it uses `time`), `notify_cleanup` and `datetime` stay in `slack.py` because tests patch `slack.human_readable_timedelta`, `slack.datetime` and `crc.notify.slack.time.sleep`. `SLACK_SAFE_CHARS`, `ITEMS_PER_MESSAGE`, `_chunk_lines_into_messages`, `NOT_FOUND` and `SlackClient` are re-exported from `slack`.
- **Helpers extracted (inside `crc/cli`).**
  - `report_calls.report_result(ops, resource, notify, label, result_attr)`: the `if slack_client: notify(...)` then `if influxdb_client: write_influxdb(...)` pair, used by IP, keypair, NIC, disk, KMS (resource_ops) and delete_vm, spot instance requests, stop_vm (vm_ops). The result attribute is still read only when an Influx client is set.
  - `adapter_args.vm_arguments` (the four VM and three spot VM constructors, previously seven copies of the same argument lists), `ip_arguments`, `disk_arguments` and `DiskArgs`. Only the argument lists moved; the class is chosen in `vm_ops` / `resource_ops`.
  - `vm_ops._delete_spot`: one body for the Azure, GCP and OCI spot deletes (the `resource_group` / `project_id` checks stay before it, as before).
- **Tests.** `pytest -q`: 43010 at cea0a8a, 43010 after (equal). `make check` (ruff, mypy, lint-imports, pytest) green; runtime 2m42s (baseline at cea0a8a: 2m54s; Python 3.12 in this VM).
- **READMEs updated.** `crc/cli/README.md` (new modules and public names), `crc/notify/README.md` (`SlackPoster`), `crc/core/README.md` (policy facade note).
- **Owner actions.**
  - `report_result` could become a `NotifyMixin` method in `crc/cli/notify.py` (not in this lane); it moves there unchanged. No cross-cloud helper candidates found in these files.
  - `crc/cli/main.py` was not touched; `scan.py` still imports `_run_options` from `dispatch`.
  - After the wave, the `README.md` rule "Keep each file under 400 lines" in `crc/cli/README.md` should become 250 together with ARCH-004.
  - Python in this VM is 3.12, not the 3.11 CI uses; nothing here depends on the difference.

## New bugs

Noticed, not fixed:

- `crc/cli/resource_ops.py:190-198` `delete_vpc` sends no Slack message and writes no Influx points, unlike every other delete.
- `crc/notify/slack.py:177` `notify_cleanup` logs a failed part with the root `logging.exception`, not the module `logger`.
- `crc/notify/slack_owners.py:69` the owner e-mail domain `@yugabyte.com` is hard coded.
- `crc/cli/vm_ops.py:27-33` `_delete_vm` treats an empty `instance_state` list like `None` (delete all states).
