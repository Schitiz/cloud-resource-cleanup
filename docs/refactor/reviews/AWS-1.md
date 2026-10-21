## Coding summary

Rung AWS-1: `crc/aws/vpc.py` refactored into a registered `Cleaner` (`@register("aws", "vpc")`), no behaviour change.

- **Summary.** `VpcCleaner` (`plan()` lists with `ec2.vpcs.filter` and decides protection, no mutating call; `apply()` tears down and deletes) behind typed Protocols in the new `crc/aws/vpc_api.py` (kept separate because ARCH-004 caps non-legacy files at 400 lines), injected through `VpcRuntime` / the constructor. `VPC` keeps its constructor, `vpc_ids_to_delete`, `get_deleted`, `delete_count`, `get_vpc_ids`, `_get_filter`, `_should_skip_vpc` and `delete()`, and drives the cleaner region by region, VPC by VPC, in the exact call order of `main`. Protection goes through `policy.exception_tags_any` and `policy.notags_all` (FILTER_VARIANTS names `should_skip_by_tags`; the cleaner calls its two parts one tag at a time so the early return and `KeyError`s of `main` are kept). The filter stays the server side EC2 `tag:key` filter. `crc.py` is unchanged. Both ratchet lines for `crc/aws/vpc.py` / `crc.aws.vpc` are removed from `pyproject.toml`; nothing was added.
- **Tests.** Before: 2703 passed. After: 3005 passed (+302): `tests/test_aws_vpc_parity.py` 287 (90 cases through the legacy adapter and again through the registered Cleaner path, 37 quirk checks, 63 `_should_skip_vpc` combinations, filter/ids/factory/injection checks) and `tests/test_aws_vpc.py` 15 (plan read-only, apply order, dry run, protection, summaries). The oracle `tests/legacy/aws_vpc.txt` is byte-identical to `git show main:crc/aws/vpc.py`. Deliberate one-line mutations (retry count, default security group name) fail the table. `make check` is green (ruff, mypy strict, import-linter, pytest, archtests ARCH-001..005, SAF-LOCK).
- **Open issues.**
  - Cleaner path vs `main`, abnormal runs only: `plan()` decides protection for all VPCs of a region before `apply()` deletes, so after a region aborted mid-teardown (connectivity error) the Cleaner path has already logged the `Tags and notags not present` warning for VPCs `main` never reached. Results, SDK calls per region, summary lines and errors are identical; the adapter path (`VPC.delete()`) is identical including log order. With a real boto3 `Vpc` the protection check raises `TypeError` on the first VPC (BUG-012), so no deletion precedes it in either path.
  - Cleaner path across several regions lists every region before deleting (as the other AWS cleaners), so a listing error in a later region is raised before earlier regions are deleted, whereas `main` had deleted them.
  - Dry-run `apply()` does nothing and logs nothing (`plan()` already logged the dry-run summary).
  - 9 new quirks are in `docs/refactor/bugs/pending/AWS-1.md` (the main ones: no age gate or default-VPC guard, so an empty `filter_tags` selects every VPC of every region; and `--resource vpc` running the AWS `VPC` class on every cloud without a `self.cloud` check). BUG-012 and BUG-021 are kept as is.
  - `docs/refactor/bugs/README.md` and `docs/refactor/bugs/pending/README.md` were added only because ARCH-002 requires a README in every directory with files; other lanes will add the same two files, so expect an add/add conflict to resolve at integration (keep either).
- **Core changes needed.** None.
- **`FILTER_VARIANTS.md` change needed (not edited).** In the `aws/vpc.py` row, add that since AWS-1 protection is evaluated through `policy.exception_tags_any` / `policy.notags_all` per tag on the Vpc resource (still raising `TypeError` for a real Vpc, BUG-012), cite `main` lines `:94-127`, `:167`, and that the oracle is `tests/legacy/aws_vpc.txt`. The "VPC passes a resource object" note in section 6 stays true.
- **`crc/README.md` / `tests/README.md` / `tests/legacy/README.md` (not edited).** `tests/legacy/README.md` should list `aws_vpc.txt` (exact `git show main:crc/aws/vpc.py`, run by `tests/test_aws_vpc_parity.py`); `tests/README.md` should list `test_aws_vpc_parity.py` and `test_aws_vpc.py`; `crc/README.md` should mention `vpc_api.py` if it lists `crc/aws` modules.

## Round 1 (Argon)

Scope reviewed: `git diff 9b5c85a..HEAD` (`crc/aws/vpc.py`, `crc/aws/vpc_api.py`, `crc/aws/README.md`, `pyproject.toml`, `docs/refactor/bugs/pending/AWS-1.md`, `docs/refactor/reviews/AWS-1.md`, `tests/legacy/aws_vpc.txt`, `tests/test_aws_vpc.py`, `tests/test_aws_vpc_parity.py`) against `git show main:crc/aws/vpc.py`, `AGENTS.md`, `docs/refactor/BUGS.md`, and `.cursor/skills/crc-python-refactor/REVIEW_CHECKLIST.md`.

### 1. Behaviour parity (`git show main:crc/aws/vpc.py`)

- **SDK calls (order and arguments)** (`crc/aws/vpc.py:79-149`, `:217-229`, `:288-299`, `:376-395` vs `main:crc/aws/vpc.py:79-92`, `:144-240`):
  - Per region in `get_all_regions("ec2", "us-west-2")`: connects `boto3.client("ec2", region_name=region)` and `boto3.resource("ec2", region_name=region)`, lists via `ec2.vpcs.filter(Filters=vpc_filter)`, records every returned `vpc.id` in `vpc_ids_to_delete` before checking `dry_run` or `_should_skip_vpc(vpc)` (`BUG-012`), and tears down unprotected VPCs in the exact sequence of `main` (`ec2.DhcpOptions("default").associate_with_vpc(VpcId=vpc.id)`, `vpc.internet_gateways.all()` -> `detach_internet_gateway` + `gw.delete()`, `vpc.route_tables.all()` -> `rt.associations` non-main `rta.delete()` then `if not rt.associations: rt.delete()`, `vpc.subnets.all()` -> `subnet.instances.all()` `instance.terminate()`, `client.describe_vpc_endpoints` -> `client.delete_vpc_endpoints`, `vpc.security_groups.all()` non-`"default"` `sg.delete()`, `client.describe_vpc_peering_connections(Filters=[{"Name": "requester-vpc-info.vpc-id", "Values": [vpc.id]}])` -> `ec2.VpcPeeringConnection(...).delete()`, `vpc.network_acls.all()` non-`is_default` `netacl.delete()`, `vpc.subnets.all()` -> `subnet.network_interfaces.all()` `interface.delete()` + `subnet.delete()`, and 5-attempt `client.delete_vpc(VpcId=vpc.id)` loop).
- **Filter, protection and age decisions** (`crc/aws/vpc.py:217-225`, `:267-286` vs `main:crc/aws/vpc.py:79-127`, `:167`):
  - Server-side `tag:key` filter passes value lists unchanged (`BUG-021`); no age gate.
  - `is_protected(vpc)` passes the `Vpc` object to `should_skip` (`BUG-012`); `should_skip` logs `"Tags and notags not present"` when both `exception_tags` and `notags` are empty/falsy, checks `policy.exception_tags_any({key: value}, self._exception_tags)` per tag in loop order (preserving early return before later malformed tags and `KeyError('Key')` / `KeyError('Value')`), and evaluates `policy.notags_all(all_tags, self._notags or {})` at the end.
- **Logs, errors and dry-run path** (`crc/aws/vpc.py:66-76`, `:140-149`, `:186-196`, `:200-215`, `:349-353`, `:381-395` vs `main:crc/aws/vpc.py:70-77`, `:91`, `:103`, `:156-168`, `:229-252`):
  - Every `logging.info`, `logging.warning`, and `logging.error` message matches `main`.
  - `CONNECTIVITY_ERRORS` skip the region via `log_skipped_region(region, "VPC cleanup", e)` while keeping VPC IDs already appended to `vpc_ids_to_delete`; non-connectivity errors outside `delete_vpc` propagate immediately; `delete_vpc` catches `Exception` 5 times and logs `"Failed to Delete VPC {vpc.id} after 5 retries"` on exhaustion without raising.

### 2. Oracle and parity test verification

- `diff -u <(git show main:crc/aws/vpc.py) tests/legacy/aws_vpc.txt` is empty (SHA-256 `c88b0dedf482fdb00ca8ea487a4b74df7c960d2c720e9704cd494922597672e4`).
- `tests/test_aws_vpc_parity.py` runs both the oracle and the refactored `VPC` / registered `VpcCleaner` against `FakeAws` and asserts ordered SDK calls, deleted IDs, counts, log records, stdout, and exceptions across 90 cases, 37 quirk checks, and 63 `_should_skip_vpc` combinations.
- Tested a deliberate one-line change in `crc/aws/vpc.py` (`_DELETE_RETRIES = 4`), confirmed `pytest -q tests/test_aws_vpc_parity.py` failed immediately, and reverted it.

### 3. Architecture, scope and lane compliance

- `VpcCleaner` implements `Cleaner`, is registered with `@register("aws", "vpc")`, has a strictly read-only `plan()` (`ARCH-005` passes), uses `crc.core.policy.exception_tags_any` and `crc.core.policy.notags_all`, puts `boto3` behind typed `Protocol`s in `crc/aws/vpc_api.py`, and was removed from both legacy ratchet lists in `pyproject.toml` with nothing added.
- `crc.py`, `crc/core/**`, other clouds, and shared docs forbidden by lane rules are untouched; `crc/aws/README.md` is accurate and passes `ARCH-002` symbol sync.

### BLOCKING (fixed)

1. **SDK `Vpc` resource object leaked into `Candidate.extra` across the cleaner boundary** (`crc/aws/vpc.py:32`, `:174`, `:246-265`, `tests/test_aws_vpc.py:73-77`):
   - `plan_region()` stored the `Vpc` SDK resource in `Candidate.extra["vpc"]`, violating `ARCHITECTURE.md:54` ("SDK objects do not cross the cleaner boundary; cleaners normalise to `Candidate`"), `crc/core/cleaner.py:40` ("One cloud resource, normalised by the cleaner. No SDK objects."), and `REVIEW_CHECKLIST.md:36`.
   - Kept the planned `Vpc` handles internal to `VpcCleaner._vpcs` (keyed by `(region, vpc_id)` in plan order) so `Candidate.extra` contains only `{"protected": protected}`, and tightened `test_plan_candidates_carry_region_and_unprotected_flag` to assert `dict(candidate.extra) == {"protected": False}`.
2. **Line citations in `docs/refactor/bugs/pending/AWS-1.md` cited branch lines instead of `main` for `crc.py` and included docstring lines for `_get_filter`** (`docs/refactor/bugs/pending/AWS-1.md:11`, `:18-19`):
   - Row 8 cited `crc.py:787-797` (current branch line numbers after R3 moved notification helpers out of `crc.py`), whereas `git show main:crc.py` places `delete_vpc` at `crc.py:929-939`. Row 1 cited `crc/aws/vpc.py:84-92` where lines 84-85 on `main` are inside the docstring (`_get_filter` body is `:86-92`, matching `BUG-021`). Fixed both citations and added the `NEW` high-risk row for `--resource vpc` running the AWS `VPC` class on every cloud without a `self.cloud` check (`main` `crc.py:929-939`, `:1532`, `:1544`, `:1586-1587`).

### NIT (left)

- `VpcCleaner.apply()` returns `Result(succeeded=tuple(ids))` when called directly with `context.dry_run=True` (`crc/aws/vpc.py:201-203`), though `crc.core.engine.run` skips `apply()` in dry run.

### Gates

`pip install -r requirements.txt -r requirements-dev.txt` then `make check`:

| Gate | Result |
|------|--------|
| `ruff check .` | All checks passed |
| `mypy` (`crc`, `tests`) | Success: no issues found in 86 source files |
| `lint-imports` | Contracts: 5 kept, 0 broken |
| `pytest -q` | 3005 passed |

Test count: 2703 before AWS-1 (`9b5c85a`), 3005 after (+302).

VERDICT: APPROVE
