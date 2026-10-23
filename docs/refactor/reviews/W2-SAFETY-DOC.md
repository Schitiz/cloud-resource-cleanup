# W2-SAFETY-DOC review

## Coding summary

Lane W2-SAFETY-DOC (docs only): `CLEANUP_SAFETY.md` and the root `README.md` now describe the code of branch `w2/safety-doc`. No code, test, lock or other doc file was touched. `make check` is green (archtest `SAF-LOCK` passes: no SAF ID was added, removed or renumbered).

### CLEANUP_SAFETY.md, SAF items changed (claim, proof)

| ID | Change | Proof in code |
|----|--------|---------------|
| SAF-002 | `sys.exit(0)` now lives in `crc/cli/scan.py`; scan forces `--dry_run` | `crc/cli/scan.py:149`, `:152`; dry_run forced at `:497-499`; the only `sys.exit` in `crc/` |
| SAF-007 | AWS disk age validation is in `crc/aws/disk/settings.py` (package, not `disk.py`) | `crc/aws/disk/settings.py:36` (`normalize_age`), `:86` (age gate required) |
| SAF-009 | Rewritten: `get_retention_age` users fail closed with `KEEP_AGE`, `is_old` never treats it as old, `MAX_AGE` included, `bad_age_tag` counted | `crc/core/age.py:23` (`KEEP_AGE`), `:216-218` (`is_old` returns False before `MAX_AGE`), `:249-280` (`get_retention_age`, `skip("bad_age_tag")` at `:279`); callers: `crc/aws/disk/volumes.py:175`, `crc/aws/kms.py:247`, `crc/aws/vm/cleaner.py:342`, `crc/azu/disk.py:230`, `crc/azu/vm/cleaner.py:299`, `crc/gcp/disk.py:274`, `crc/gcp/vm.py:258`, `crc/oci/disk/cleaner.py:323`, `crc/oci/vm/cleaner.py:256` |
| SAF-014 | Breaker is in `dispatch.py`; `--cloud all` with `disk`/`all` raises in `validate_targets` before any cleaner | `crc/cli/dispatch.py:26-28`, `:227-228` |
| SAF-017 | Path `crc/aws/disk.py` became `crc/aws/disk/` | `crc/aws/disk/settings.py:86-98` |
| SAF-025 | AWS floor: `--age` omitted: max(tag, detach_age); `--age` only: tag or age; both: (tag or age) + `detach_age`; `MAX_AGE` never shortens | `crc/core/policy.py:341-349` (`aws_disk_creation_floor`), `crc/aws/disk/volumes.py:189` and `:197` (`_detach_floor`), `:207-214` (adds `detach_age` only when both are set; BUG-283); CloudWatch window uses only `detach_age`: `crc/aws/disk/cleaner.py:231-240`; `older_than_floor` ignores `MAX_AGE`: `crc/aws/disk/volumes.py:69-75` |
| SAF-031 | Spot yb_task rule named precisely (exact keys `yb_task` / `yb-task`), no longer "same as disk" because disk folds key names | `crc/core/policy.py:24`, `:277-279` (spot) vs `:264-268` and `crc/aws/disk/volumes.py:58-66` (disk, BUG-282) |
| SAF-043 | GCP Spot keeps an unlabelled VM when `--filter_tags` is empty (BUG-228); OCI relies on age only | `crc/gcp/spot_vm/instances.py:94-95`; OCI `crc/oci/spot_vm/decide.py:85-100` has no such rule |
| SAF-044 | Extended: GCP leftover disk custom age label (BUG-242); OCI volume owned only if created at/after the instance and no other attachment except `DETACHED`; unknown keeps | `crc/gcp/spot_vm/disks.py:86-104`, `:107-135`; `crc/oci/spot_vm/leftovers.py:24` (`_NOT_ATTACHED`), `:120-150` (`volume_owned`) |
| SAF-045 | Extended to the OCI VM cleaner (skip reason `managed`) | `crc/oci/vm/cleaner.py:40`, `:235-240`; `crc/oci/spot_vm/decide.py:63-65`; GCP `crc/gcp/spot_vm/instances.py:49-53`, `:108-109` |
| other | Paths and wording only: SAF-001 (`crc/aws/connectivity.py:26`), SAF-003/004 (`crc/aws/disk/cleaner.py:120-139`, `crc/aws/_base.py:14-38`, `crc/aws/disk/__init__.py:51-52,170`), SAF-005 (`crc/azu/spot_vm/cleaner.py:162-173`), SAF-021..024 (`crc/gcp/disk.py:269-281`), SAF-046 (`crc/oci/spot_vm/cleaner.py:186-191`), SAF-037 (`crc/cli/dispatch.py:111-119`). "On main" headings and the "(on main)" wording are gone |

### CLEANUP_SAFETY.md, other text

- New "CLI validation" section (untagged): `validate_targets` runs before the scan and the dispatch (`crc/cli/main.py:51-53`, `crc/cli/dispatch.py:217-236`, `:256`); unsupported pairs (`crc/cli/dispatch.py:185-200`); `--cloud all --resource disk|all` raises (`:227-228`); blank `--scan_tag` raises (`crc/cli/inputs.py:148-158`, called at `crc/cli/main.py:51`).
- New untagged "Per-resource keep rules": AWS disk `yb_task` key folding (`crc/aws/disk/volumes.py:58-66`, BUG-282), GCP disk errors keep the disk (`crc/gcp/disk.py:171-173,187-190,220-246`), OCI disk unknown attachment state keeps the volume (`crc/oci/disk/cleaner.py:142-147`, `:198-199`, `:220-230`: listing errors skip the region and nothing is deleted from it), OCI VM evaluation error keeps the instance (`crc/oci/vm/cleaner.py:175-191`). They have no SAF ID because `tests/archtest/safety_lock.json` is owner-only and an unlisted ID fails `SAF-LOCK`.
- Module map: lists `crc/cli/` and describes `crc.py` as a re-export shim (`crc.py:3-5` comment, `:104` the only call; everything else is imports and `__all__`); `crc/service.py` row notes `KEEP_AGE`; `crc/core/`, `crc/oci/disk/`, `crc/oci/vm/` rows added; `*.py` paths that are now packages (`crc/aws/disk/`, `crc/aws/spot_instance_requests/`, `crc/azu/spot_vm/`, `crc/gcp/spot_vm/`, `crc/oci/spot_vm/`) corrected; the `crc/gcp/disk.py` row is the FIX-GCP-DISK text.
- Owner-action sections with "None" (AWS-EIP, AWS-KMS, AWS-SNAP, AWS-VPC, AZU-*, CLI-ALL, GCP-IP, GCP-VM, OCI-SPOT optional text folded into SAF-044) needed nothing more.

### README.md fixes

- Example 6 ("To Delete AWS VPCs") used `--resource vm`; now `--resource vpc` (`crc/cli/args.py:49`).
- Log path: code writes `logs/crc.log` (`crc/service.py:290-300`: `logs_dir = "logs"`, `logs_file = "crc.log"`), truncated each run (`crc/utils.py:246`, `mode="w"`), debug level (`crc/utils.py:229-250`). The old text said "in the same directory as the script" and "resource type, name and date deleted".
- Clouds: `oci` added to `--cloud` (`crc/cli/args.py:31`). Resources: full list `disk ip keypair vm vpc kms nic spot_instance_requests spot_instances snapshot all` (`crc/cli/args.py:43-57`) with the AWS-only / Azure-only / not-on-OCI rules (`crc/cli/dispatch.py:185-200`), the `--cloud all` rules, and the GCP/OCI `spot_instances` opt-in.
- Flags: short options (`-c -p -r -o -s -f -e -n -x -a -t -m -i`) added (`crc/cli/args.py`); `--scan_tag` documented (`crc/cli/args.py:283-291`, `crc/cli/scan.py`; AWS VMs only, `crc/cli/vm_ops.py:93-97`; needs `--resource vm`, `crc/cli/inputs.py:114-119`, `--resource all` with a single cloud raises); `--kms_pending_window` default 7 and `--kms_key_description` / `--kms_user` required for kms/all (`crc/cli/inputs.py:124-128`); `stop` only with `vm` (`crc/cli/inputs.py:111-112`); `--age` not used for GCP disks, VPC, NIC; snapshot fixed at 90 days (`crc/cli/dispatch.py:127`); spot resources need a positive age (`crc/core/age.py:40-48`, callers in spot adapters); `--max_age` exports `MAX_AGE` (`crc/cli/clients.py:33-38`); `--detach_age` bullet rewritten for the SAF-025 floor and GCP behaviour; Slack/Influx need their tokens (`crc/cli/inputs.py:100-107`).
- Features list: AWS disks (opt-in), snapshots, VPCs, Azure NICs; custom age tag fail-closed note; scan tag.
- Prerequisites: Python 3.11 (AGENTS.md), `oci`, `slack_sdk`, `influxdb-client` (`requirements.txt`); new OCI environment variables (`crc/oci/_base.py:45-48`).
- Examples: 1 had an unquoted `--max_age {'days': 14}`; 5 said "created in the last 2 days" (it selects resources older than 2 days); 6 fixed; added 10 (AWS disk with `--detach_age`), 11 (Azure NIC), 12 (snapshot), 13 (`--scan_tag`).
- Typos: "esources" fixed, "specfic" fixed; "on main" wording removed.

### Owner actions left

1. `tests/archtest/safety_lock.json` is owner-only: assign SAF IDs and locked tests (or `gaps` entries) to the untagged rules in "CLI validation" and "Per-resource keep rules", then tag them in `CLEANUP_SAFETY.md`.
2. Per-package READMEs still say the custom age tag is fail open: `crc/azu/vm/README.md:39`, `crc/aws/vm/README.md:40`, `crc/gcp/README.md:58-59` (other lanes own them).
3. `crc/cli/args.py:177-193` `--detach_age` help is stale (see New bugs).

## New bugs

- `crc/cli/args.py:189-192`: the `--detach_age` help says the AWS tag floor is `max(tag, detach_age)` only in detach_age-only mode and never mentions that with both `--age` and `--detach_age` the CreateTime floor is the effective age plus `detach_age` (`crc/aws/disk/volumes.py:207-214`, BUG-283).
- `crc/core/policy.py:24`, `:277-279` vs `:264-268`: the spot-volume `yb_task` protection matches only the exact keys `yb_task` / `yb-task` (case sensitive) while the AWS disk cleaner folds case and `-`/`_` (BUG-282). A leftover spot volume with key `YB_TASK=prod` is not protected by its own tag.
- `crc/oci/_base.py:18-22`: tenancy OCID, user OCID, fingerprint, home region and compartment are hard-coded constants, so `--cloud oci` can only ever address one tenancy; README can only document the key variables.
- `crc/cli/scan.py:149-152`, `crc/cli/vm_ops.py:93-97`: only AWS VMs implement `find_instances_with_tag`. For Azure, GCP and OCI the scan prints "scan not implemented" and the run ends with "No matching instances found. Nothing to clean." and exit 0, which reads as a clean result.
- `crc/cli/constants.py:5`: `RESOURCES` has no `vpc`, `spot_instance_requests` or `spot_instances`, so `--cloud all --resource all` never runs them (and `--cloud all --resource all` raises anyway at `crc/cli/dispatch.py:227-228`). The help text of `--resource all` does not say so.
- `crc/core/selection.py:55-111`: a second implementation of the flag and pair validation (`ValueError` messages of `main()`) next to `crc/cli/inputs.py` and `crc/cli/dispatch.py`; the two can drift apart.
- `crc/core/age.py:216`: `is_old` recognises the bad-tag marker by equality with `KEEP_AGE`, so a real `{'days': 1000000}` tag or `--age` is also read as "keep". Harmless (fail closed) but undocumented.
- `crc/cli/inputs.py:118`, `:128`: error text says `--resources` and "reuired"; the flag is `--resource`.
