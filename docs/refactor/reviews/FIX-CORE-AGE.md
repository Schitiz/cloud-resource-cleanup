## Coding summary

Rung FIX-CORE-AGE (wave FIX-1): `--custom_age_tag_key` is now fail closed for a tag that is present but broken.

- **Bugs fixed.** BUG-004 (empty or unparseable custom age tag fell back to `--age`) and BUG-016 (a parsed
  custom age that is not finite, zero or negative was used as is). As a side effect the same code path
  now keeps instead of failing in the variants BUG-208 (Azure VM `{'days': 1e999}` raised `OverflowError`) and
  BUG-182 (float, string or list tag: `TypeError` or never old); the driver decides whether to mark those rows.
- **Bugs left.** None of the two. BUG-182's `True` / `{'days': True}` case (1 day) is unchanged (see New bugs).
- **How.** `crc/core/age.py`: `get_retention_age` (used by the 9 non-spot call sites: aws disk/kms/vm, azure disk/vm,
  gcp disk/vm, oci disk/vm) now validates with the same code as `validated_retention_age`
  (`_checked_retention_age`, same messages; `validated_retention_age` still logs at WARNING and raises
  `ValueError`, the spot modules are untouched). No key, no tags or tag absent: `None` (use `--age`) as before.
  Valid tag: the parsed literal as before (so calls, selections and logs equal today). Present but empty, whitespace,
  `None`/non-string value, unparseable, not an int/dict, unsupported key, not finite, zero or negative:
  the keep marker `KEEP_AGE` (`{"days": 1000000}`), the run log counts `skip("bad_age_tag")` and the cause is
  logged at DEBUG only. `is_old` returns False for `KEEP_AGE` before the `MAX_AGE` override, so the
  production `--max_age {"days": 21}` cannot shorten it. The other callers need no change because they all
  pass the value through `policy.effective_age` into `is_old` (AWS disk through `normalize_age` and
  `older_than_floor`, where 1,000,000 days is also never reached). `crc/service.py` only gets a docstring update
  (it delegates unchanged).
- **Production commands.** Every Jenkins command keeps its flags and its selection. Only a resource whose
  `max_retention_age` tag is present but broken changes: it is kept (before: judged by `--age`, or deleted on
  a zero/negative/inf tag). Resources without the tag and resources with a valid tag are unchanged.
- **Direction.** Only keeps more. A resource is never deleted, stopped or released that was kept before; no new
  SDK call, no new flag, no exit-code change (the `OverflowError` / `TypeError` stops become keeps).
- **Files changed.** `crc/core/age.py`, `crc/service.py` (docstring), `crc/core/README.md`, `crc/README.md`,
  `tests/test_core_age.py`, `tests/test_core_age_fix.py` (new), `tests/test_crc_service_parity.py`, and the
  quirk tables of `tests/test_{aws_disk,aws_kms,aws_vm,azure_disk,azure_vm,gcp_disk,gcp_vm,oci_disk,oci_vm}_parity.py`
  (marked `BUG_004_FIXED`: the new outcome is asserted, the other quirks still assert oracle and new). Hash-locked
  tests are not touched and all pass.
- **Parity note.** The module oracles in `tests/legacy/*.txt` (`class VM(Service)`) inherit the live
  `crc.service.Service`, so they cannot show the old custom-age behaviour; the old behaviour is pinned by
  `tests/test_crc_service_parity.py` against the frozen `crc_service.txt` (diverging cases are the index set
  `BUG_004_CASES`, asserted by `test_get_retention_age_bad_tag_diverges_and_keeps`: differs from the oracle,
  returns `KEEP_AGE`, only DEBUG logs). All other cases still equal the oracle. The `test_matches_main` case
  `custom-age-inf-raises` of `tests/test_azure_vm_parity.py` no longer has `fails_in_plan`.
- **Tests.** Before (182466d): 42444 collected, all passed. After: 42491 collected (+47), all pass; `make check` green.
- **Owner actions.** See below.

## Owner action

`CLEANUP_SAFETY.md` is CODEOWNERS: proposed replacement of the SAF-009 sentence ("Other modules that still call
`get_retention_age` alone **fail open** ...") in "Age gates":

> [SAF-009] Modules that use `get_retention_age` (AWS disk/kms/vm, Azure disk/vm, GCP disk/vm, OCI disk/vm) fail
> **closed** too (BUG-004, BUG-016): a custom age tag that is present but empty, unparseable, not finite, zero or
> negative makes `get_retention_age` return `KEEP_AGE`, which `is_old` never treats as old (`MAX_AGE` included), and
> the run log counts `bad_age_tag`. An absent tag still uses `--age` / detach_age.

Also in the Module map row for `crc/service.py`: add "`get_retention_age` returns `KEEP_AGE` for a bad tag".
The READMEs of the per-module packages (`crc/aws/vm/README.md:40`, `crc/oci/disk/README.md:32`,
`crc/oci/vm/README.md:38`) still say "fail-open custom age tag"; I left them to the module FIX rungs / the driver to
avoid merge conflicts.

## New bugs

- Double counting: for a kept bad-tag resource the run log counts `bad_age_tag` (in `get_retention_age`) and the
  module's own later skip (for example `too_young` in `crc/aws/disk/volumes.py:_old_enough`) when it records one;
  `SKIPPED` counts can exceed the number of resources. Exists on main: no (introduced by the keep marker). Fix: switch
  the callers to `validated_retention_age` in their own FIX rungs and drop the marker.
- `crc/aws/disk/volumes.py:_old_enough` (`invalid_age_tag` skip) can no longer see an invalid tag from
  `get_retention_age`; the branch stays for ages that pass validation but fail `normalize_age`. Exists on main: yes
  (dead path now).
- `True` / `{'days': True}` tags are accepted as 1 day by `require_positive_age` (BUG-024 family), so a `True` tag is a
  valid 1-day age. Main: yes (`crc/service.py:214-220`).
- Duplicate AWS tag keys: the first entry decides (empty first entry keeps; before, the first non-empty won,
  BUG-289). AWS tag keys are unique, so no real impact.
