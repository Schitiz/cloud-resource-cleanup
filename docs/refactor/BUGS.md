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

From R3 the notification quirks (BUG-028 to BUG-034, BUG-041, BUG-042) live in `crc/notify/slack.py`
and `crc/notify/influx.py`; `crc.py` still holds the duplicate definition and the `"#" + channel`
prefix is applied by `SlackNotifier.post`. The `Location on main` column keeps citing `crc.py`.

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
| BUG-062 | GCP IP cleanup has no age gate and no tag/label filter: with an empty `--name_regex` every RESERVED address of every region is deleted | `crc/gcp/ip.py:83-96` | yes | deletes what it should keep | high | GCP-1 | open |
| BUG-010 | Azure VM `_get_vm_status` reads `instance_view(...).statuses[1]` without a bounds check; failed-provisioning VMs raise `IndexError`, which the per-VM `except` only logs, so they are never cleaned | `crc/azu/vm.py:257-259` (called inside the try of `:146-157`; the `except` is at `:154`) | yes | keeps what it should delete | medium | known before R2c (PLAN.md) | open |
| BUG-011 | AWS Elastic IP `notags` raises `TypeError`: `all(<bool>,)` is called on a single bool when `notags` is set and no exception tag matched (FILTER_VARIANTS.md section 2 says it never skips; policy keeps that reading) | `crc/aws/elastic_ips.py:102-107` (called `:127`) | yes | run fails | medium | R1b | open |
| BUG-012 | AWS VPC `_should_skip_vpc` takes tags but is called with the boto3 Vpc resource, so exception_tags or notags in a real run likely raise (not verified live); every VPC is also recorded as deleted before the skip check | `crc/aws/vpc.py:94`, `:160-167` | yes | run fails | medium | R1b | open |
| BUG-013 | Azure IP raises `TypeError` for untagged IPs (`tags is None`) when exception_tags or notags is set | `crc/azu/ip.py:70-78` | yes | run fails | medium | R1b | open |
| BUG-014 | AWS KMS filter with several values for one key never matches (all (key, value) pairs must be present) | `crc/aws/kms.py:137-145` | yes | keeps what it should delete | medium | R1b | open |
| BUG-015 | AWS KMS `exception_tags` indexes `tag["Key"]` on `TagKey` dicts: every tagged key raises `KeyError`, swallowed by a bare `except:` that skips the key | `crc/aws/kms.py:90-91`, `:147`, `:181-183` | yes | keeps what it should delete | medium | R1b | open |
| BUG-016 | Custom age tag parsed by `get_retention_age` is not validated: `{'days': inf}` (`1e999`) or zero/negative dicts are returned as is | `crc/service.py:268-274`, `:306`, `:314` | yes | deletes what it should keep | medium | R1a | open |
| BUG-017 | `--cloud all --resource keypair` deletes AWS keypairs and then raises `ValueError` on Azure (same shape for `nic` on non-Azure clouds), so the run fails after the first cloud already deleted | `crc.py:799-800`, `:823` | yes | run fails | medium | R2b | open |
| BUG-018 | `--cloud all --resource all` and `--cloud all --resource disk` can never run: the AWS EBS breaker raises on the first pair; `--cloud aws --resource all` fails earlier | `crc.py:1367`, `:1394`, `:1546-1552` | yes | run fails | medium | R2b | open |
| BUG-045 | AWS key pair cleanup has no age gate or name gate: an empty `age` (`is_old({})` is True) with an empty `name_regex` deletes every key pair in every region; `__init__` does not validate either | `crc/aws/keypairs.py:48-69` (`__init__`), `:112-114`, `:120-124` | yes | deletes what it should keep | medium | R4a | open |
| BUG-053 | AWS Elastic IP cleanup has no age gate: every unassociated tagged address that matches the filter is released at once, including one allocated minutes ago and not yet associated by its owner; `Describe` data carries no allocation time, so the module cannot tell | `crc/aws/elastic_ips.py:125-144` (no age check before `release_address` at `:143`) | yes | deletes what it should keep | medium | R4b | open |
| BUG-055 | AWS KMS key is scheduled for deletion although it was logged `KEY SKIPPED`: a key is appended to `active_keys` at the first policy statement naming `kms_user`, and a later statement without `Principal.AWS` (a `Service` principal) raises `KeyError`, which the bare `except:` logs as skipped while the key stays selected | `crc/aws/kms.py:174-183` (append `:180`, schedule `:189-191`) | yes | deletes what it should keep | medium | R4c | open |
| BUG-063 | A delete error in a region aborts the run and loses the record of the addresses of that region already deleted (`deleted_ips` is extended only after the region loop), and no summary is logged or reported | `crc/gcp/ip.py:98-107`, `:109-115` | yes | run fails | medium | GCP-1 | open |
| BUG-064 | `AddressesClient().delete()` returns a long-running operation that is never waited on: "Deleting IP address" is logged and the name is counted as deleted before GCP confirms, so an asynchronous failure goes unnoticed | `crc/gcp/ip.py:101-107` | yes | cosmetic | medium | GCP-1 | open |
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
| BUG-040 | `--cloud all --resource snapshot` runs the AWS `Snapshot(age_days=90).delete()` once per cloud (4 times): the snapshot branch sits inside `for cloud in clouds` and ignores `cloud`; later passes repeat the AWS scan and the dry-run message | `crc.py:39`, `:1532`, `:1544`, `:1629-1643` | yes | cosmetic | low | R2c round 2 | open |
| BUG-041 | When `usergroups_list` fails, `get_user_groups_list` returns the string `"not_found"`; `ping_on_slack` iterates it as a list of groups, so the first owner without a Slack user raises `TypeError: string indices must be integers` and the remaining owners are not pinged | `crc.py:224-228`, `:245`, `:258-259` | yes | run fails | low | R3 | open |
| BUG-042 | In `ping_on_slack`, `conversations_open` and the `response["channel"]["id"]` read are outside the `try`, so a failure there aborts the whole disk notification and the run (the post itself is guarded) | `crc.py:296-299` (the `try` starts at `:301`) | yes | run fails | low | R3 | open |
| BUG-043 | `human_readable_timedelta` (scan-tag uptime) pads zero units inconsistently: 3 hours shows `03h 00s`, 2 days `2d 00s`, 1 day 5 minutes `1d 00h 05m 00s`; the docstring promises `3d 04:12:05` | `crc/notifications.py:74-109` (conditions at `:104`, `:106`) | yes | cosmetic | low | R3 (round 2) | open |
| BUG-044 | `send_slack_message` `max_retries=3` is the total number of attempts (2 retries), and a part that still fails is logged twice: `logger.exception` in `send_slack_message`, then `logging.exception` on the root logger in `notify_cleanup` | `crc/notifications.py:111`, `:132-133`, `:183` | yes | cosmetic | low | R3 (round 2) | open |
| BUG-046 | AWS key pair cleanup is not atomic across regions: it lists and deletes region by region, a non-connectivity error (ClientError, invalid regex, naive `CreateTime`) aborts the run after earlier regions were already deleted, and no summary line is logged; a connectivity error mid-region keeps the names already deleted but skips the rest | `crc/aws/keypairs.py:99-146`, `:143-145`, `:147-155` | yes | cosmetic | low | R4a | open |
| BUG-047 | AWS key pair deletion order comes from a `set` (and the exception regex patterns are also tried in set order), so it varies between processes and decides which invalid pattern raises | `crc/aws/keypairs.py:95-98`, `:101`, `:136-141` | yes | cosmetic | low | R4a | open |
| BUG-048 | AWS key pairs without `KeyName` or `CreateTime` are skipped silently (no log); the exception regex is evaluated even when the name regex does not match, so an invalid exception pattern raises for any key pair | `crc/aws/keypairs.py:105-106`, `:112-118` | yes | cosmetic | low | R4a | open |
| BUG-049 | AWS key pair cleanup does not check whether a key pair is still referenced (running instances, launch templates, Auto Scaling): any old matching key pair is deleted, so later launches from those templates fail; only the name and age decide | `crc/aws/keypairs.py:104-142` (no lookup before `delete_key_pair` at `:138`) | yes | deletes what it should keep | low | R4a (round 2) | open |
| BUG-050 | Deleted key pairs are recorded by bare name without region (`deleted_keypairs.append(keypair_to_delete)`), so the same name deleted in two regions appears twice in the Slack and InfluxDB report with no way to tell the regions apart | `crc/aws/keypairs.py:142`, `crc.py:446` | yes | cosmetic | low | R4a (round 2) | open |
| BUG-051 | AWS Elastic IP cleanup is not atomic across regions: it lists and releases region by region, a non-connectivity error (`ClientError`, `KeyError` on a missing `AllocationId`, `TypeError` from `notags`) aborts the run after earlier regions were already released, and no summary line is logged | `crc/aws/elastic_ips.py:119-147`, `:152-160` | yes | cosmetic | low | R4b | open |
| BUG-052 | A connectivity error while releasing addresses of a region loses the record of the ones already released: `deleted_ips.extend` runs only after the release loop, so those IPs are gone but missing from `get_deleted`, Slack and InfluxDB | `crc/aws/elastic_ips.py:141-147`, `:148-150` | yes | cosmetic | low | R4b | open |
| BUG-054 | An unassociated, tagged Elastic IP without `PublicIp` (a Wavelength carrier IP is described with `CarrierIp` instead) that passes the filter raises `KeyError('PublicIp')`; nothing catches it, so the run stops in that region, later regions are never cleaned and no summary is logged (BUG-051 shape) | `crc/aws/elastic_ips.py:130`, `:139` | yes | run fails | low | R4b (round 2) | open |
| BUG-056 | AWS KMS key with several policy statements naming `kms_user` is added to `active_keys` once per statement, so `schedule_key_deletion` is called twice for it; the second call fails on a key already pending deletion (`KMSInvalidStateException`), nothing catches it, and the run aborts before `get_deleted` is filled | `crc/aws/kms.py:174-180`, `:188-192` | yes | run fails | low | R4c | open |
| BUG-057 | AWS KMS scheduling is not atomic and has no per-key error handling: a `schedule_key_deletion` error aborts the run after earlier keys were scheduled, but `kms_keys_to_delete.extend` runs only after the loop, so those keys are missing from `get_deleted`, Slack and InfluxDB and no summary line is logged | `crc/aws/kms.py:188-196` | yes | cosmetic | low | R4c | open |
| BUG-058 | AWS KMS logs the warning `Exception tags and not present` for every key when `exception_tags` is empty or `None` (the message is also garbled), flooding the log of a normal run | `crc/aws/kms.py:84-86`, called `:147` | yes | cosmetic | low | R4c | open |
| BUG-059 | AWS KMS cleanup is hard-coded to `us-west-2` (`get_all_regions` is imported and never called), so KMS keys in every other region are ignored | `crc/aws/kms.py:10`, `:21`, `:113` | yes | keeps what it should delete | low | R4c | open |
| BUG-060 | AWS KMS key policy match compares `Principal.AWS` to `kms_user` with `==` only: a statement listing several principals (`"AWS": [arn1, arn2]`) never equals the user ARN, so a key shared with the Jenkins user is never selected; a `"Principal": "*"` statement raises `TypeError`, which the bare `except:` turns into `KEY SKIPPED` | `crc/aws/kms.py:174-176`, `:181-183` | yes | keeps what it should delete | low | R4c (round 2) | open |
| BUG-061 | AWS KMS per-key bare `except:` also catches `KeyboardInterrupt` (and `SystemExit`): an operator's Ctrl-C during the key loop is logged as `KEY SKIPPED`, the loop goes on, and in a real run the keys already selected are still scheduled for deletion | `crc/aws/kms.py:181-183`, schedule `:187-192` | yes | deletes what it should keep | low | R4c (round 2) | open |
| BUG-065 | `--name_regex` and `--exception_regex` are plain substring tests (`regex in name`), not regexes, despite the flag names; a regex such as `^ip-` never matches | `crc/gcp/ip.py:87-93` | yes | keeps what it should delete | low | GCP-1 | open |
| BUG-066 | Only regional addresses are listed (`AddressesClient`, per region); global addresses are never listed or cleaned | `crc/gcp/ip.py:74-76` | yes | keeps what it should delete | low | GCP-1 | open |
| BUG-067 | Region listing has no error handling and no connectivity fallback (unlike AWS `get_all_regions`): any `RegionsClient().list` error, including auth errors, propagates and nothing is cleaned | `crc/gcp/_base.py:6-13`, `crc/gcp/ip.py:70` | yes | run fails | low | GCP-1 | open |
| BUG-068 | An address with a non-string name (or a non-string filter/exception entry) raises `TypeError` from `regex in name` (including in `exception_regex` when `filter_regex` did not match), after other addresses of the region were only collected, so nothing of that region is deleted | `crc/gcp/ip.py:87-93` | yes | run fails | low | GCP-1 | open |
| BUG-069 | GCP IP cleanup is not atomic across regions: it lists and deletes region by region, so an `AddressesClient().list` error (or mid-page iteration error) in a later region aborts the run after earlier regions were already deleted, with no summary line logged (`BUG-046` / `BUG-051` shape) | `crc/gcp/ip.py:70-107`, `:109-115` | yes | cosmetic | low | GCP-1 | open |
| BUG-070 | Deleted GCP IPs are recorded by bare name without region (`ips_to_delete.append(name)`), so the same address name deleted in two regions appears twice in `get_deleted`, Slack and InfluxDB with no way to tell the regions apart (`BUG-050` shape) | `crc/gcp/ip.py:96`, `:107`, `crc.py:422`, `:780-783` | yes | cosmetic | low | GCP-1 | open |
| BUG-071 | `get_deleted` is annotated `-> str` but returns the list `deleted_ips` | `crc/gcp/ip.py:48-53` | yes | cosmetic | low | GCP-1 | open |
| BUG-072 | `IP.delete()` called twice on one instance accumulates `deleted_ips` and the second summary lists addresses of both runs | `crc/gcp/ip.py:107-115` | yes | cosmetic | low | GCP-1 | open |
| BUG-073 | Every address of every region, including IN_USE and filtered-out ones, is logged in full at INFO (`logging.info(address)`, the whole `Address` proto with IP, users and labels) before any filter, so logs are noisy and expose address details of resources the run does not touch | `crc/gcp/ip.py:78-79` | yes | cosmetic | low | GCP-1 | open |

## Counts

73 rows: critical 2, high 8, medium 14, low 49. All open.

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
