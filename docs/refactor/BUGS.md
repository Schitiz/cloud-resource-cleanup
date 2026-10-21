# Bug and quirk register

Single register of every bug and quirk found in CRC. Rows are sorted by risk (critical, high,
medium, low). Locations are `file:line` on the `main` branch, verified with
`git show main:<path>`. The legacy modules on `refactor/python-agentic` are identical to
`main` except `crc/service.py`, which only delegates age handling to `crc/core/age.py`; the
age rows therefore cite `main`'s `crc/service.py`.

## Rules

1. Every rung appends the bugs and quirks it finds here, with the `main` file:line. New bugs
   do not go into `STATUS.md` any more (older lists there stay as they are).
2. Do not fix a bug outside a behaviour-fix rung (`docs/refactor/PLAN.md`). A refactor rung
   preserves the quirk and covers it with a test.
3. Never delete a row. When a bug is fixed, wrongly reported or superseded, change its status
   (`open`, `fixed in <rung>`, `not a bug`, `wontfix`) and keep the row.
4. IDs are `BUG-NNN` and are never reused or renumbered. A new row takes the next free ID and
   is inserted at the end of its risk group, so the table stays sorted by risk.
5. Effect is one of: deletes what it should keep, keeps what it should delete, run fails,
   cosmetic. Risk is critical, high, medium or low. "Exists on main" is yes only after a check
   of `main`.

Related: `docs/refactor/FILTER_VARIANTS.md` (how each module filters, section 7 open items),
`CLEANUP_SAFETY.md` (SAF IDs), `docs/refactor/STATUS.md` (rung log).

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| BUG-001 | GCP IP `--exception_regex` is inverted: names that match an exception are processed, others are excluded | `crc/gcp/ip.py:91-95` | yes | deletes what it should keep | critical | R1b | open |
| BUG-002 | Azure VM lists VMs subscription-wide (`list_all()`) but status, stop and delete use `self.base.resource_group`; a same-named VM in the configured group is acted on | `crc/azu/vm.py:134`, `:257`, `:273`, `:279`, `:293-294` | yes | deletes what it should keep | critical | known before R2c (PLAN.md) | open |
| BUG-003 | Azure VM stop uses `begin_power_off`, so the VM is stopped but not deallocated and keeps billing | `crc/azu/vm.py:293-294` | yes | keeps what it should delete | high | known before R2c (PLAN.md) | open |
| BUG-004 | Custom age tag is fail open: an empty or unparseable tag falls back to `--age` (9 call sites; the Spot modules use `validated_retention_age` instead) | `crc/service.py:268-274`, `:298-318`; callers `crc/aws/disk.py:400`, `crc/aws/kms.py:155`, `crc/aws/vm.py:223`, `crc/azu/disk.py:114`, `crc/azu/vm.py:141`, `crc/gcp/disk.py:121`, `crc/gcp/vm.py:254`, `crc/oci/disk.py:146`, `crc/oci/vm.py:118` | yes | deletes what it should keep | high | R1b | open |
| BUG-005 | GCP disk `notags` is stored but never applied | `crc/gcp/disk.py:80` (stored), `:150-161` (only exception checks) | yes | deletes what it should keep | high | R1b | open |
| BUG-006 | GCP disk `name_regex` is stored but never used, so the name filter is ignored | `crc/gcp/disk.py:81` | yes | deletes what it should keep | high | R1b | open |
| BUG-007 | AWS KMS filter with an empty value list adds no constraint, so every key matches | `crc/aws/kms.py:137-142` | yes | deletes what it should keep | high | R1b | open |
| BUG-008 | AWS KMS custom age tag never matches: `get_retention_age` looks up `Key` but `list_resource_tags` returns `TagKey`/`TagValue` | `crc/aws/kms.py:131-136`, `:155-158`; `crc/service.py:302` | yes | deletes what it should keep | high | R1b | open |
| BUG-009 | `--resource snapshot` always runs the AWS `Snapshot` class with hard-coded `age_days=90` for every cloud (`--cloud azure --resource snapshot` touches AWS) and sends nothing to Slack or Influx | `crc.py:1629-1647` | yes | deletes what it should keep | high | R2b | open |
| BUG-010 | Azure VM `_get_vm_status` reads `instance_view(...).statuses[1]` without a bounds check; failed-provisioning VMs raise `IndexError`, which the per-VM `except` only logs, so they are never cleaned | `crc/azu/vm.py:257-259` (called inside the try of `:146-157`; the `except` is at `:154`) | yes | keeps what it should delete | medium | known before R2c (PLAN.md) | open |
| BUG-011 | AWS Elastic IP `notags` raises `TypeError`: `all(<bool>,)` is called on a single bool when `notags` is set and no exception tag matched (FILTER_VARIANTS.md section 2 says it never skips; policy keeps that reading) | `crc/aws/elastic_ips.py:102-107` (called `:127`) | yes | run fails | medium | R1b | open |
| BUG-012 | AWS VPC `_should_skip_vpc` takes tags but is called with the boto3 Vpc resource, so exception_tags or notags in a real run likely raise (not verified live); every VPC is also recorded as deleted before the skip check | `crc/aws/vpc.py:94`, `:160-167` | yes | run fails | medium | R1b | open |
| BUG-013 | Azure IP raises `TypeError` for untagged IPs (`tags is None`) when exception_tags or notags is set | `crc/azu/ip.py:70-78` | yes | run fails | medium | R1b | open |
| BUG-014 | AWS KMS filter with several values for one key never matches (all (key, value) pairs must be present) | `crc/aws/kms.py:137-145` | yes | keeps what it should delete | medium | R1b | open |
| BUG-015 | AWS KMS `exception_tags` indexes `tag["Key"]` on `TagKey` dicts: every tagged key raises `KeyError`, swallowed by a bare `except:` that skips the key | `crc/aws/kms.py:90-91`, `:147`, `:181-183` | yes | keeps what it should delete | medium | R1b | open |
| BUG-016 | Custom age tag parsed by `get_retention_age` is not validated: `{'days': inf}` (`1e999`) or zero/negative dicts are returned as is | `crc/service.py:268-274`, `:306`, `:314` | yes | deletes what it should keep | medium | R1a | open |
| BUG-017 | `--cloud all --resource keypair` deletes AWS keypairs and then raises `ValueError` on Azure (same shape for `nic` on non-Azure clouds), so the run fails after the first cloud already deleted | `crc.py:799-800`, `:823` | yes | run fails | medium | R2b | open |
| BUG-018 | `--cloud all --resource all` and `--cloud all --resource disk` can never run: the AWS EBS breaker raises on the first pair; `--cloud aws --resource all` fails earlier | `crc.py:1367`, `:1394`, `:1546-1552` | yes | run fails | medium | R2b | open |
| BUG-019 | Azure disk state test is a substring of the allowed string (`disk_state in "Unattached"`), so `"attached"` and the empty string pass | `crc/azu/disk.py:16`, `:124-126` | yes | deletes what it should keep | low | R1b | open |
| BUG-020 | AWS VM and Elastic IP skip untagged resources only when the `Tags` key is absent, an empty list is processed | `crc/aws/vm.py:200-201`, `crc/aws/elastic_ips.py:125` | yes | deletes what it should keep | low | R1b | open |
| BUG-021 | EC2 server-side `tag:key` filter is passed an empty value list unchanged; its effect was never verified | `crc/aws/vm.py:181-183`, `crc/aws/vpc.py:86-92`, `crc/aws/spot_instance_requests.py:109-115` | yes | deletes what it should keep | low | R1b | open |
| BUG-022 | Sensitive `yb_task` and Kubernetes CSI protections exist only in AWS disk and AWS spot leftover volumes; other modules rely on `exception_tags` from Jenkins | `crc/aws/disk.py:67-74`, `:173-208`; `crc/aws/spot_instance_requests.py:229-254` | yes | deletes what it should keep | low | R1b | open |
| BUG-023 | GCP disk `age` is stored but never used (only `detach_age` applies) | `crc/gcp/disk.py:77`, `:123` | yes | deletes what it should keep | low | R1b | open |
| BUG-024 | `True` is accepted as an age of 1 day (`isinstance(True, int)`) | `crc/service.py:38`, `:43-44` | yes | deletes what it should keep | low | R1a | open |
| BUG-025 | `MAX_AGE` that is not a dict raises (`SyntaxError`, `AttributeError`) instead of failing closed | `crc/service.py:222-225` | yes | run fails | low | R1a | open |
| BUG-026 | `is_old` ignores unknown age keys; an age with only unknown keys returns False | `crc/service.py:237-266` | yes | keeps what it should delete | low | R1a | open |
| BUG-027 | `{}` in `MAX_AGE` replaces the age with `{}` and `is_old` returns False | `crc/service.py:222-229`, `:237-266` | yes | keeps what it should delete | low | R1a | open |
| BUG-028 | `notify_deleted_nic_via_slack` is defined twice; the second wins, so Azure VM delete sends VM names as the NIC list | `crc.py:337`, `:344`, `:371-372`, `:456` | yes | cosmetic | low | R2a | open |
| BUG-029 | `ping_on_slack` hard-codes "disks" and builds the count without a space | `crc.py:267`, `:273`, `:291` | yes | cosmetic | low | R2a | open |
| BUG-030 | `influxdb_bucket` and `resource_suffix` exist only with `influxdb_conn`; `write_influxdb` then fails with `AttributeError` and the catch-all hides it | `crc.py:98-99`, `:524-539` | yes | cosmetic | low | R2a | open |
| BUG-031 | `notify_deleted_disk_via_slack` sends nothing when `get_deleted` is neither a `list` nor a `dict` (exact `type()` check) and does not say so | `crc.py:480-493` | yes | cosmetic | low | R2a | open |
| BUG-032 | Dry runs still write Influx points and send Slack messages | `crc.py:565-567`, `:615` | yes | cosmetic | low | R2a | open |
| BUG-033 | `ping_on_slack` computes `operated_list_length` twice (dead code) and uses bare `except:` | `crc.py:214`, `:226`, `:243-256` | yes | cosmetic | low | R2a | open |
| BUG-034 | A Slack channel that already starts with `#` becomes `##name` in notifications (only `notify_cleanup` strips it) | `crc.py:347`, `:1509` | yes | cosmetic | low | R2a | open |
| BUG-035 | KMS description and user are required for `--resource kms` on every cloud, also clouds without KMS; error text has the typo "reuired" | `crc.py:1377-1385` | yes | run fails | low | R2b | open |
| BUG-036 | Error text says `--resources all` but the flag is `--resource` | `crc.py:1366-1371` | yes | cosmetic | low | R2b | open |
| BUG-037 | `MAX_AGE` is set in `os.environ` and deleted only at the end of `main()`, not in a `finally`, so any exception leaves it set | `crc.py:1421-1424`, `:1645-1647` | yes | cosmetic | low | R2b | open |
| BUG-038 | `clouds == "all"` is always False after `clouds` became a list, so the scan list comes from the dead else branch | `crc.py:1439` | yes | cosmetic | low | R2b | open |
| BUG-039 | An `--operation_type` other than `delete` or `stop` silently does nothing for `vm` (unreachable via argparse `choices`) | `crc.py:1576-1584` | yes | cosmetic | low | R2b | open |

## Counts

39 rows: critical 2, high 7, medium 9, low 21. All open.

## Notes

- The three Azure VM bugs (subscription-wide list versus resource group, `begin_power_off`
  without deallocate, unchecked `statuses[1]`) were known before R2c and are scheduled as
  behaviour fixes in `docs/refactor/PLAN.md`.
- R2c found one correction to earlier documentation: AWS Elastic IP `notags` does not
  "never skip" as `FILTER_VARIANTS.md` section 2 and `crc.core.policy.aws_eip_should_skip`
  describe; the call `all(<bool>,)` raises `TypeError` (BUG-011). Policy keeps the
  documented reading until a behaviour-fix rung decides.
- The fail-open custom age tag is listed with the 9 call sites found by `git grep` on `main`;
  `FILTER_VARIANTS.md` section 7 counts 11 modules.
