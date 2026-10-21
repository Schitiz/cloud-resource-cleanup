# Pending bugs and quirks: GCP-1 (`crc/gcp/ip.py`)

Same columns as `docs/refactor/BUGS.md`; the ID is `NEW` until the integrator assigns one.
Locations are `main` file:line (`git show main:crc/gcp/ip.py`, `git show main:crc/gcp/_base.py`).
`BUG-001` (inverted GCP IP `--exception_regex`, `crc/gcp/ip.py:91-95`) is already registered;
the parity tests cover it and it is not repeated here.

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| NEW | GCP IP cleanup has no age gate and no tag/label filter: with an empty `--name_regex` every RESERVED address of every region is deleted | `crc/gcp/ip.py:83-96` | yes | deletes what it should keep | high | GCP-1 | open |
| NEW | A delete error in a region aborts the run and loses the record of the addresses of that region already deleted (`deleted_ips` is extended only after the region loop), and no summary is logged or reported | `crc/gcp/ip.py:98-107`, `:109-115` | yes | run fails | medium | GCP-1 | open |
| NEW | `AddressesClient().delete()` returns a long-running operation that is never waited on: "Deleting IP address" is logged and the name is counted as deleted before GCP confirms, so an asynchronous failure goes unnoticed | `crc/gcp/ip.py:101-107` | yes | cosmetic | medium | GCP-1 | open |
| NEW | `--name_regex` and `--exception_regex` are plain substring tests (`regex in name`), not regexes, despite the flag names; a regex such as `^ip-` never matches | `crc/gcp/ip.py:87-93` | yes | keeps what it should delete | low | GCP-1 | open |
| NEW | Only regional addresses are listed (`AddressesClient`, per region); global addresses are never listed or cleaned | `crc/gcp/ip.py:74-76` | yes | keeps what it should delete | low | GCP-1 | open |
| NEW | Region listing has no error handling and no connectivity fallback (unlike AWS `get_all_regions`): any `RegionsClient().list` error, including auth errors, propagates and nothing is cleaned | `crc/gcp/_base.py:6-13`, `crc/gcp/ip.py:70` | yes | run fails | low | GCP-1 | open |
| NEW | An address with a non-string name (or a non-string filter entry) raises `TypeError` from `regex in name`, after other addresses of the region were only collected, so nothing of that region is deleted | `crc/gcp/ip.py:87-93` | yes | run fails | low | GCP-1 | open |
| NEW | `get_deleted` is annotated `-> str` but returns the list `deleted_ips` | `crc/gcp/ip.py:48-53` | yes | cosmetic | low | GCP-1 | open |
| NEW | `IP.delete()` called twice on one instance accumulates `deleted_ips` and the second summary lists addresses of both runs | `crc/gcp/ip.py:107-115` | yes | cosmetic | low | GCP-1 | open |
