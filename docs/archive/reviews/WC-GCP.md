## Coding summary

Lane WC-GCP (branch `wc/gcp`).

- Routed: `(gcp, ip)` and `(gcp, disk)` already run through `crc/cli/bridge.py`, the GCP route table and the registered Cleaners (`IpCleaner`, `DiskCleaner`); nothing in `crc/`, `crc.py` or the CLI tests used the `IP` and `Disk` classes. Unrouted kinds: none in this lane.
- Deleted: adapter classes `crc.gcp.ip.IP` (`ip_adapter.py`) and `crc.gcp.disk.Disk` (`disk_adapter.py`), their package re-exports and their Public API lines. `ip.py` and `disk.py` stay as facades for the client and cleaner names. The `VM` class (used by `crc/cli/scan.py`), `SpotVM` and the hash-locked tests are untouched.
- Tests retargeted to `crc.core.engine.run` (Registry plus `build_*_cleaner`, or a helper `tests/helpers_wc_gcp_engine.py` that runs a cleaner built around a fake client): `test_gcp_ip_parity.py`, `test_gcp_disk_parity.py` (same oracle cases, same SDK-mutation, order, log, stdout and error assertions, BUG-001, 063, 064, 005, 006, 126, 127 divergences kept), `test_gcp_ip.py`, `test_gcp_ip_fix.py`, `test_gcp_disk.py`, `test_gcp_disk_fix.py`, `test_gcp_logger.py`. The old adapter-vs-oracle test (`test_matches_main`) became `test_engine_matches_main`; a parametrised `..._lists_every_region/zone_before_it_deletes` test over all cases replaces its case count. Ported cases: second `delete()` accumulation (each engine run is independent; the oracle's accumulation is still asserted), `default_state` attribute (IpCleaner `state` argument through the engine), `disk_state` argument ignored, class attributes (client constants), constructor slack shapes (factory options).
- Allowed behaviour change (ENG): plan() lists everything before apply() deletes, also within a zone for disks; so a later listing error, or a nameless zone entry (`zone-without-name-after-first-zone`, `addresses-list-permission-denied`), stops before any delete. Asserted as `ENGINE_QUIRKS`.
- READMEs: `crc/gcp/README.md` trimmed to the current code (rung names, adapter wording, legacy-path wording and moved-doc links removed).
- Test count: floor 44415 before; 44415 collected after (adapter tests removed, ordering and ported tests added). Floor not raised.
- Owner actions: none required. `spot_vm/README.md` still has rung names and adapter wording (see Left).

## Left

- `crc/gcp/spot_vm/README.md` trim (text only) not done in the time limit; `VM`/`SpotVM` stay as classes.
- BUGS.md / CLEANUP_SAFETY.md ENG row and sentence belong to the CLI lane, not edited here.

## New bugs

None found.
