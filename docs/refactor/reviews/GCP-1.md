# GCP-1 review

## Coding summary

Rung GCP-1: `crc/gcp/ip.py` refactored into a `Cleaner` (lane `refactor/lane-gcp`). No behaviour change.

- **Summary.** `IpCleaner` (`cloud="gcp"`, `kind="ip"`, registered with `@register("gcp", "ip")`
  through `build_ip_cleaner`) lists regions and addresses in `plan()` (read-only) and calls
  `delete_address` from `apply()` / `apply_region()` only. Filtering uses
  `policy.filter_substring_matches`, `policy.gcp_ip_exception_excludes` (inverted, BUG-001) and
  `policy.state_in` (RESERVED). The SDK sits behind the typed Protocols `GcpIpClient` and
  `AddressView`; `ComputeIpClient` builds a new SDK client for every call, as main does. `IP` is
  the thin adapter `crc.py` uses (constructor, `deleted_ips`, `default_state`, `get_deleted`,
  `count`, `delete()` unchanged; optional fifth argument `client`). `crc.py` is not changed.
  The module has no age gate, so there is no clock and no `context.now` use.
- **Parity.** `tests/legacy/gcp_ip.txt` is the byte-identical `git show main:crc/gcp/ip.py`.
  `tests/test_gcp_ip_parity.py` runs the oracle and the adapter against the same fake
  `compute_v1` clients over 58 cases (dry run, filters, inverted exception, status, API, region
  listing, iteration and delete errors, empty results, malformed addresses) comparing SDK calls
  in order, results, count, logs, stdout and errors; the same table runs through the registered
  Cleaner (plan then apply) and the logged summary lines match. Region listing has no
  connectivity fallback on main (BUGS pending), so listing errors propagate in both.
  Cleaner path differences, inherent to plan-then-apply and also accepted in the AWS rungs: all
  regions are listed before the first delete, so an error while listing a later region stops
  before any delete, and log lines interleave differently for more than one region (compared as
  multisets, exact for one region).
- **Test counts.** Before: 2703 passed. After: 2876 passed (+173: 151 in `tests/test_gcp_ip_parity.py`, 22 in `tests/test_gcp_ip.py`). No existing test changed.
- **Gates.** `ruff check .`, `mypy` (strict, no new override: google-cloud-compute is typed),
  `lint-imports`, `pytest -q`. `crc/gcp/ip.py` and `crc.gcp.ip` are removed from both ratchet
  lists in `pyproject.toml`.
- **Open issues.** New quirks are in `docs/refactor/bugs/pending/GCP-1.md` (9 rows, none fixed).
  ARCH-002 requires a README with the four sections in every directory, so
  `docs/refactor/bugs/README.md` and `docs/refactor/bugs/pending/README.md` were added; other
  lanes may add the same files (merge conflicts on those two READMEs are trivial).
- **Core change needed.** None. `crc/core/policy.py` already has the three functions used.
- **FILTER_VARIANTS.md change needed.** None for behaviour. Optional: the `gcp/ip.py` row cites
  main line numbers that are still correct (`:83`, `:87-89`, `:91-95`).
- **`crc/README.md` / `tests/legacy/README.md` / `tests/README.md` change needed.** Add `gcp_ip.txt`
  (exact `git show main:crc/gcp/ip.py`, used by `tests/test_gcp_ip_parity.py`) to
  `tests/legacy/README.md`; `crc/core/README.md` could say `gcp` / `ip` is now registered
  alongside the AWS cleaners; both files are outside this lane's edit rights.
