# Pending bugs and quirks: rung CLI-3 (`main()` moved into `crc/cli/`)

Found while splitting `main()`. Behaviour is unchanged from `main` (no fixes in this rung); the
locations are lines of `git show main:crc.py`. IDs are assigned when the rows move to `BUGS.md`.

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| NEW | An empty `--scan_tag ''` (for example an unset Jenkins parameter) is falsy, so the read-only scan is skipped and the same command line runs the destructive cleanup of `--resource`/`--cloud`; only a non-empty tag without `=` raises | `crc.py:1429` (`if scan_tag:`), `:1430-1431` | yes | deletes what it should keep | high | CLI-3 | open |
| NEW | The scan path leaves `MAX_AGE` set in `os.environ`: it ends in `sys.exit(0)` (or raises the `--scan_tag must be in KEY=VALUE` error), so the reset at the end of `main()` never runs (`BUG-037` shape, which only names exceptions) | `crc.py:1423-1425`, `:1431`, `:1526`, `:1529`, `:1645-1647` | yes | cosmetic | low | CLI-3 | open |
| NEW | `--scan_tag` runs after the delete-run validations and ignores `--resource`: with the default `--resource all` the scan needs `--cloud all` and `--kms_key_description` / `--kms_user` (`BUG-035` and `BUG-036` shape), and `--cloud aws --scan_tag k=v` alone fails with the "All Resources cleanup" error | `crc.py:1366-1371`, `:1377-1385`, `:1429` | yes | run fails | low | CLI-3 | open |
| NEW | A falsy `--influxdb '{}'` skips the token check, the field check and the client, so a typo silently turns Influx reporting off; the same holds for an empty `--slack_channel ''` (no token needed, no client, no notification) | `crc.py:1356-1360`, `:1410`, `:1415` | yes | cosmetic | low | CLI-3 | open |
| NEW | In the scan loop a hit that is not a dict (a provider returning strings) raises `AttributeError` at `h.get(...)`, outside every `try`, and aborts the scan after earlier clouds were already reported | `crc.py:1466-1468` | yes | run fails | low | CLI-3 | open |
| NEW | The scan Slack message is sent with the run's `--operation_type` (`stop` reports "vm" scan hits as a stopped operation that never ran) and always as resource `vm` | `crc.py:1509` | yes | cosmetic | low | CLI-3 | open |
| NEW | `scan_tag` is read from `args` twice (the first read is dead) and the `# Handle read-only scanning` comment is mis-indented | `crc.py:1348`, `:1427-1428` | yes | cosmetic | low | CLI-3 | open |

Notes (no row needed): `raise EnvironmentError(...)` is `OSError` (an alias), so the type name in a
traceback is `OSError` on both sides; `crc/cli/` writes `OSError`. The dead `clouds == "all"` branch
of the scan list (`BUG-038`) is replaced by `list(targets.clouds)`, which is what the dead branch
always evaluated to.
