## Coding summary

Lane G-GCP, branch `gb/gcp`: owner-approved behaviour fixes for BUG-124, BUG-062 and BUG-183.

- **Routed / changed:** the three kinds were already engine-routed; nothing new to route, no adapter
  deleted or shimmed. The registered factories now validate the age on a real run
  (`core_age.require_positive_age`), before any client is built, so before any cloud call:
  - GCP disk (`crc/gcp/disk_cleaner.py`): `--detach_age` must be positive (`ValueError` naming
    `detach_age`); `--age` is no substitute (BUG-124).
  - GCP IP (`crc/gcp/ip_cleaner.py`, `ip_client.py`): `--age` must be positive; each address that
    passes the name filter must be at least `age` old by `creationTimestamp` (same
    `TIME_FORMAT` parsing and `core_age.is_old` as disks and VMs). Younger addresses are kept
    (`too_young`); a missing or unreadable timestamp keeps the address and records a failure
    (BUG-062). The route (`crc/cli/routes/gcp.py`) passes `options.age` only when the flag was given.
  - GCP VM (`crc/gcp/vm_cleaner.py`): `--age` must be positive for delete and stop; a custom age
    label still replaces the age per instance but not the requirement (BUG-183).
  - Dry runs keep working without an age.
- **Docs:** `CLEANUP_SAFETY.md` (SAF-011 note, SAF-023 rewritten, file table), `crc/gcp/README.md`,
  BUGS.md rows BUG-124, BUG-062, BUG-183 marked `fixed in G-GCP`, the three `TODO(BUG-NNN)` comments removed.
- **CLI parity tests:** `tests/test_cli_bridge_gcp.py` now gives the ip cases `age` (the oracle
  ignores it) and `address()` a `creationTimestamp`; the frozen RUN START lines of the ip cases in
  `tests/helpers_cl2_gcp_runlog.py` gain `age={"days":1}`. Disk and VM cases already carried an age.
  Engine-side parity harnesses (`test_gcp_ip_parity.py`) pass `age` and an old timestamp and drop
  the two debug age lines `main` never logged. The six oracle cases that now diverge are marked:
  disk `age-empty/none/zero` (`diverges="BUG-124"`, `_assert_bug_124`) and VM `age-empty/none/zero`
  (`BUG_183`, `_assert_bug_183`): oracle still deletes, the cleaner raises before any call.
- **Tests:** 44,674 collected before, 44,705 after (31 net: 33 new in `tests/test_gcp_require_age.py`;
  `test_saf_023_...` was split into a dry-run test and a real-run-raises test, +1). Floor raised to
  44,705 with `make raise-test-floor`. `make check` green; `make smoke-offline` 17/17.
- **Owner actions:**
  1. `tests/archtest/safety_lock.json`: the locked `test_saf_023_gcp_disk_without_detach_age_deletes_every_detached_disk`
     asserted the bug, so it was renamed to `test_saf_023_gcp_disk_real_run_without_detach_age_raises_before_any_call`
     (the entry name was renamed in the JSON by hand because the update script cannot rename; hashes
     then regenerated with `update_safety_lock.py`, which also added three SAF-011 locks for the new tests). Please review.
  2. `tests/test_jenkins_contract.py` and its fixture are untouched (Lane G-AWS). `_ip` omits `age`
     when the flag is absent, so the frozen options of today's fixture and of the updated one
     (GCP IP with `--age`) both pass; after merge, the frozen GCP IP options will contain `age`.
  3. Triggers repo `crc/require-age` must be deployed together with this change: GCP disk needs
     `--detach_age`, GCP IP needs `--age`, or the real Jenkins runs now fail with `ValueError`.
- **New bugs:** none.
- **Left:** nothing. Direct construction of `DiskCleaner`/`VmCleaner`/`IpCleaner` (tests only) is not
  validated; the check is in the registered factories, as for the Spot cleaners.
