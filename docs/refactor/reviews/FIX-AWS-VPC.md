# FIX-AWS-VPC review (behaviour-fix rung, wave FIX-1)

## Coding summary

Branch `fix/aws-vpc`. Package `crc/aws/vpc/` (the task named `crc/aws/vpc.py`; it is a package since ST-AWS-VPC). No production command uses `--resource vpc`.

Bugs fixed:

- BUG-012: protection (`exception_tags`, `notags`) is decided on `vpc.tags` (`None` is no tags) instead of the boto3 `Vpc` resource, so a real run no longer raises `TypeError`.
- BUG-083 (default-VPC and empty-filter part only, not the age part): `ValueError` before any SDK call when `filter_tags` is empty (`VpcCleaner.require_filter_tags`, called by `plan()` and `VPC.delete()`, dry run too); a default VPC (`is_default` anything but `False`) is skipped with `skip("default_vpc")`, is not a candidate and is not listed as deleted.
- BUG-088: instances are never terminated (`_terminate_instances` removed). `has_instances()` (read-only) runs first in `delete_vpc()`; a VPC with an instance in any subnet is kept before anything is detached or deleted (`skip("has_instances")`) and is not listed as deleted.
- BUG-087: `delete_vpc` retries only on `ClientError` code `DependencyViolation` (5 attempts, 3 s injected `sleep` between attempts, `VpcRuntime.sleep` / `VpcCleaner.sleep`, new `delete.py`). Any other error is logged, recorded with `run.fail` and the VPC is skipped and not listed as deleted; the run goes on.

Bugs left: none of the four in full, but two remainders are not fixed (see Owner decision): protected VPCs are still recorded in the deleted list (as on main), and the age gate of BUG-083 (not in this rung).

Files changed: `crc/aws/vpc/cleaner.py`, `crc/aws/vpc/client.py`, `crc/aws/vpc/teardown.py`, new `crc/aws/vpc/delete.py`, `crc/aws/vpc/README.md`, `tests/test_aws_vpc_parity.py`, `tests/test_aws_vpc.py`, new `tests/test_aws_vpc_fix.py`, this file. No locked test, oracle, PLAN/STATUS/BUGS or CLEANUP_SAFETY.md touched.

Test count (`pytest -q`): 42444 before (at 182466d), 42448 after (`make check` green).

Direction rule: every change keeps more or fails closed (ValueError, default VPC kept, VPC with instances kept, failed delete kept and not claimed as deleted, no instance terminated). Order of the teardown steps is unchanged except that the read-only instance scan now runs first. Parity: the 11 cases that triggered a bug moved from `CASES` to `DIVERGING` (marked with the bug ID, assert that new differs from the oracle and the exact new outcome, both through `VPC` and through the Cleaner); the other cases still compare to the oracle, with the instance scan reads (`subnets.all` first read per VPC, `subnet.instances.all`) removed from both call lists. The shared fixtures changed: `Case.filter_tags` defaults to a non-empty filter and `full()` has no instances (so unmarked cases do not hit the new guards); fake VPCs got `is_default` and `tags`.

Owner actions: none (CLEANUP_SAFETY.md does not mention VPCs).

## Owner decision

- BUG-012, second half: a VPC skipped as protected is still added to `vpc_ids_to_delete` / `Result.succeeded` (summary, Slack). Left as on main because changing it alters summaries of inputs that the fix does not cover and the parity quirk tests pin it. Suggest a follow-up rung.
- BUG-083 age gate: not in this rung. With a non-empty `filter_tags` a freshly created VPC is still deleted.
- Dry run does not run the instance scan (it would add SDK read calls), so a dry run can list a VPC that a real run will keep (`has_instances`).
- A VPC whose only instances are `terminated` (still listed by EC2 for about an hour) is kept too (fail closed); it is deleted by the next run.

## New bugs

- `crc/aws/vpc/cleaner.py` `VPC.delete()` / `VpcCleaner.apply()` (exists on main yes): teardown errors other than connectivity errors abort the whole run and skip every later VPC and region (no per-VPC isolation), unchanged.
- `crc/aws/vpc/teardown.py` (exists on main yes): teardown steps run before `delete_vpc` and are not undone when `delete_vpc` ends up failing, so a kept VPC can be left without gateways, route tables and subnets.

## Round 1 (Argon)

### Findings

1. **Test strengthening (`tests/test_aws_vpc_parity.py`)**: replaced `_scan_free(new.calls) == _scan_free(old.calls)` (which dropped `subnet.instances.all` and the first `subnets.all` from `new.calls`) with `new.calls == _expected_calls(case, old.calls)` so `new.calls` is compared unstripped and the exact pre-`DhcpOptions` instance scan reads are asserted on both `VPC.delete()` and `VpcCleaner`. Also asserted `not check(old)` in `test_diverges_from_main_by_design` and added `delete-vpc-dependency-violation-exhausted-not-listed` to `DIVERGING` (`BUG-087`).
2. **Test strengthening (`tests/test_aws_vpc_fix.py`)**: updated `test_protection_uses_the_vpc_tags_not_the_resource` to use non-iterable `FakeVpc` objects even when `tags` are present (matching real `boto3` `Vpc` resources so all 4 cases fail on `182466d`), and added `test_default_vpc_and_has_instances_log_skips_and_debug_reason` to pin `skip("default_vpc")`, `skip("has_instances")`, and the `DEBUG` diagnostic line.

### Checklist & Gates

- (1) Fixed bugs verified (`BUG-012`, `BUG-083` default-VPC & empty-filter parts, `BUG-087`, `BUG-088`), with tests in `tests/test_aws_vpc_fix.py` and `DIVERGING` in `tests/test_aws_vpc_parity.py` that fail on `182466d` and pass on `HEAD`.
- (2) Direction rule satisfied: every change keeps more or fails closed (`ValueError` before any SDK call on empty `filter_tags`, default VPCs kept, VPCs with instances kept without terminating instances or running teardown, failed `delete_vpc` kept and omitted from deleted list). Oracle `tests/legacy/aws_vpc.txt` untouched; diverging cases marked with in-scope bug IDs.
- (3) Production commands: none use `--resource vpc`.
- (4) Fail-closed paths (`require_filter_tags`) raise `ValueError` before any SDK call (`aws.calls == []`), in both dry run and real run.
- (5) No locked safety test, `safety_lock.json`, `PLAN.md`, `STATUS.md`, `BUGS.md`, or `CLEANUP_SAFETY.md` edited.
- (6) `crc/aws/vpc/README.md` Safety Invariants and Public API updated (`ARCH-002` green).
- (7) Unfixed parts (second half of `BUG-012` and age gate of `BUG-083`) explained under `## Owner decision`.
- (8) `make check` (`ruff check .`, `mypy`, `lint-imports`, `pytest -q`) green: **42450 passed** (up from 42444 at `182466d`).

VERDICT: APPROVE
