# Pending bugs and quirks: ST-OCI-DISK

Rung ST-OCI-DISK moved `crc/oci/disk.py` and `crc/oci/disk_api.py` into the subpackage `crc/oci/disk/` without a logic edit. The coding pass found no quirk beyond the `BUGS.md` rows for this module (`BUG-004`, `BUG-096` to `BUG-110`); the round 2 review found the two below. The log line is kept as on main (`crc/oci/disk/cleaner.py:270`); the refactored docstring already describes `notags` correctly (`crc/oci/disk/adapter.py:55`).

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| NEW | The age check logs the whole freeform tag dict at INFO (`logging.info(tags)`) for every volume and boot volume that passes the state, attachment, exception/notags and filter checks, with no volume name on the line, so every tag value (owner e-mails, ticket ids, custom age values) of every candidate lands in the job logs (OCI VM analogue: `BUG-170`) (found in ST-OCI-DISK round 2) | `crc/oci/disk.py:144-145` | yes | cosmetic | low | ST-OCI-DISK | open |
| NEW | The `Disk.__init__` docstring says `notags` excludes "volumes which do not have these tags", but `_should_skip_volume` skips the volumes that do have all of them (`all(key in tags and ...)`), so a reader of main configures `--notags` inverted (found in ST-OCI-DISK round 2) | `crc/oci/disk.py:41`, `:116-122` | yes | docs only | low | ST-OCI-DISK | open |
