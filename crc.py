# Copyright (c) Yugabyte, Inc.

import logging
import os
import sys

from influxdb_client import InfluxDBClient, Point  # noqa: F401 (Point: re-exported name)
from slack_sdk import WebClient

# The CRC class lives in crc/cli. The adapter classes, the constants and the SDK names below are
# re-exported so that `from crc import ...` style lookups on this file keep resolving.
from crc.aws.disk import Disk as AWS_Disk  # noqa: F401
from crc.aws.elastic_ips import ElasticIPs  # noqa: F401
from crc.aws.keypairs import KeyPairs  # noqa: F401
from crc.aws.kms import Kms  # noqa: F401
from crc.aws.snapshot import Snapshot
from crc.aws.spot_instance_requests import SpotInstanceRequests  # noqa: F401
from crc.aws.vm import VM as AWS_VM  # noqa: F401
from crc.aws.vpc import VPC  # noqa: F401
from crc.azu.disk import Disk  # noqa: F401
from crc.azu.ip import IP as AZU_IP  # noqa: F401
from crc.azu.nic import NIC  # noqa: F401
from crc.azu.spot_vm import SpotVM as AZU_SpotVM  # noqa: F401
from crc.azu.vm import VM as AZU_VM  # noqa: F401
from crc.cli.args import get_argparser
from crc.cli.constants import (  # noqa: F401
    CLOUDS,
    DELETED,
    DISKS,
    IPS,
    KEYPAIRS,
    KMS,
    NICS,
    RESOURCES,
    SPOT_INSTANCE_REQUEST,
    STOPPED,
    VMS,
)
from crc.cli.runner import CRC
from crc.cli.validate import (
    _validate_influxdb_input,  # noqa: F401
    are_values_of_dict_lists,
    is_valid_dict,
    is_valid_list,
    is_valid_type,  # noqa: F401
    validate_influxdb_inputs,
)
from crc.gcp.disk import Disk as GCP_Disk  # noqa: F401
from crc.gcp.ip import IP as GCP_IP  # noqa: F401
from crc.gcp.spot_vm import SpotVM as GCP_SpotVM  # noqa: F401
from crc.gcp.vm import VM as GCP_VM  # noqa: F401
from crc.notifications import notify_cleanup
from crc.oci.disk import Disk as OCI_Disk  # noqa: F401
from crc.oci.spot_vm import SpotVM as OCI_SpotVM  # noqa: F401
from crc.oci.vm import VM as OCI_VM  # noqa: F401


def main():
    """
    Main function to perform resource cleanup operations on the specified cloud(s) and resource(s).

    :return: None
    """
    args = get_argparser()
    clouds = args.get("cloud")
    project_id = args.get("project_id")
    resources = args.get("resource")
    operation_type = args.get("operation_type")
    resource_states = args.get("resource_states")
    filter_tags = args.get("filter_tags")
    exception_tags = args.get("exception_tags")
    name_regex = args.get("name_regex")
    exception_regex = args.get("exception_regex")
    age = args.get("age")
    custom_age_tag_key = args.get("custom_age_tag_key")
    max_age = args.get("max_age")
    detach_age = args.get("detach_age")
    dry_run = args.get("dry_run")
    notags = args.get("notags")
    slack_channel = args.get("slack_channel")
    slack_notify_users = args.get("slack_notify_users")
    slack_user_label = args.get("slack_user_label")
    influxdb = args.get("influxdb")
    kms_pending_window = args.get("kms_pending_window")
    kms_key_description = args.get("kms_key_description")
    kms_user = args.get("kms_user")
    resource_group = args.get("resource_group")
    scan_tag = args.get("scan_tag")

    INFLUXDB_TOKEN = os.environ.get("INFLUXDB_TOKEN")
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")

    slack_client = None
    influxdb_client = None

    if slack_channel and not SLACK_BOT_TOKEN:
        raise EnvironmentError("SLACK_BOT_TOKEN is not set")

    if influxdb and not INFLUXDB_TOKEN:
        raise EnvironmentError("INFLUXDB_TOKEN is not set")

    # Validate operation_type and resources
    if operation_type == "stop" and resources != "vm":
        raise ValueError("Stop is supported only for vm resource")

    # Validate resources and clouds
    if resources == "all" and clouds != "all":
        raise ValueError(
            "All Resources cleanup is supported only with all Clouds. Format: --cloud all --resources all"
        )

    if slack_notify_users and not slack_user_label:
        raise ValueError(
            "--slack_user_label is mandatory when passing --slack_notify_user"
        )

    if resources == "kms" or resources == "all":
        if not kms_key_description:
            raise ValueError(
                "Key description string is required for deleting KMS keys."
            )
        if not kms_user:
            raise ValueError(
                "Jenkins user ARN is reuired for deleting associated KMS keys."
            )

    # Process Cloud
    # AWS EBS is opt-in: require both --cloud aws and --resource disk. When those
    # are not both set, raise on the aws+disk iteration (same circuit breaker as
    # before this PR) so --cloud all / --resource all cannot skip EBS and then
    # continue into destructive AWS ip/keypair/vm/kms cleanup, and so
    # --cloud all --resource disk cannot reach Azure/GCP/OCI disk paths.
    cloud_arg = clouds
    aws_disk_opt_in = clouds == "aws" and resources == "disk"
    # GCP/OCI spot cleanup deletes RUNNING instances; keep --cloud all limited to
    # the legacy Azure-only spot_instances path unless the cloud is explicit.
    clouds = CLOUDS if clouds == "all" else [clouds]

    # Process Resources
    resources = RESOURCES if resources == "all" else [resources]

    # Validate Input Values
    is_valid_list("resource_states", resource_states)
    are_values_of_dict_lists("filter_tags", filter_tags)
    are_values_of_dict_lists("exception_tags", exception_tags)
    is_valid_list("name_regex", name_regex)
    is_valid_list("exception_regex", exception_regex)
    is_valid_dict("age", age)
    is_valid_dict("detach_age", detach_age)
    is_valid_dict("influxdb", influxdb)

    if slack_channel:
        slack_client = WebClient(token=SLACK_BOT_TOKEN)

    if influxdb:
        validate_influxdb_inputs(influxdb)
        influxdb_client = InfluxDBClient(
            url=influxdb["url"],
            token=INFLUXDB_TOKEN,
            org=influxdb["org"],
        )

    if max_age:
        os.environ["MAX_AGE"] = str(max_age)
        print(f"Set MAX_AGE: {os.environ['MAX_AGE']}")

        # Handle read-only scanning before destructive operations
    scan_tag = args.get("scan_tag")
    if scan_tag:
        if "=" not in scan_tag:
            raise ValueError("--scan_tag must be in KEY=VALUE format, e.g. auto_clean=false")
        tag_key, tag_value = scan_tag.split("=", 1)

        # enforce dry_run for safety
        if not dry_run:
            print("For safety, scan_tag enforces dry_run. Running in dry_run mode.")
            dry_run = True

        clouds_to_scan = CLOUDS if clouds == "all" else [c for c in clouds]
        any_hits = False

        for cloud in clouds_to_scan:
            print(f"\nScanning {cloud.upper()} for tag {tag_key}={tag_value}...")
            crc = CRC(
                cloud,
                dry_run,
                notags,
                slack_client,
                influxdb_client,
                project_id,
                resource_group,
                slack_channel,
                influxdb,
            )
            try:
                hits = crc.scan_instances_with_tag(tag_key, tag_value) or []
            except NotImplementedError as e:
                print(f"[{cloud}] scan not implemented: {e}")
                hits = []
            except Exception as e:
                print(f"[{cloud}] error scanning: {e}")
                hits = []

            # Normalize provider result into items (name,id,region/zone,console_url)
            items = []
            for h in hits:
                # h is expected to be a dict from provider: e.g. aws: {'cloud','region','id','name','tags'}
                name = h.get("name") or h.get("display_name") or ""
                rid = h.get("id") or h.get("instance_id") or name
                # region/zone normalization
                region = h.get("region") or h.get("zone") or h.get("location") or ""
                state = (h.get("state") or "").upper()
                launch_time = h.get("launch_time")  # could be datetime or string
                instance_type = h.get("instance_type")
                console_url = None
                try:
                    if cloud == "aws":
                        # AWS console instance URL
                        # ensure we have region and instance id
                        if region and rid:
                            console_url = f"https://{region}.console.aws.amazon.com/ec2/v2/home?region={region}#Instances:instanceId={rid}"
                    elif cloud == "gcp":
                        project = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT")
                        if project and region and name:
                            console_url = f"https://console.cloud.google.com/compute/instancesDetail/zones/{region}/instances/{name}?project={project}"
                    elif cloud == "azure":
                        # Azure portal link using resource id if available
                        resource_id = h.get("id") or h.get("resource_id")
                        if resource_id:
                            console_url = f"https://portal.azure.com/#resource{resource_id}"
                except Exception:
                    console_url = None

                items.append({
                    "name": name,
                    "id": rid,
                    "region": region,
                    "console_url": console_url,
                    "state": state,
                    "launch_time": launch_time,
                    "instance_type": instance_type
                })

            if items:
                any_hits = True
                # If slack configured, send slack notification; else print summary
                if slack_client and slack_channel:
                    try:
                        notify_cleanup(slack_client, "#" + slack_channel if not str(slack_channel).startswith("#") else slack_channel, "delete" if operation_type == "delete" else operation_type, cloud, "vm", items, dry_run)
                        print(f"[{cloud}] Sent Slack notification to {slack_channel} ({len(items)} items).")
                    except Exception as e:
                        print(f"[{cloud}] Failed to send Slack notification: {e}")
                        # still print items on console
                        for it in items:
                            print(f" - {it['region']:15} {it['id']:20} {it['name']}")
                else:
                    print(f"✅ Found {len(items)} instance(s) in {cloud}:")
                    for it in items:
                        print(f"  • {it['region']:15} {it['id']:20} {it['name']} {it['console_url'] or ''}")
            else:
                print(f"No instances found in {cloud} with {tag_key}={tag_value}.")

        # exit after scan (read-only)
        if any_hits:
            print("\n Instances found with that tag. Review before running cleanup.")
            sys.exit(0)
        else:
            print("\n No matching instances found. Nothing to clean.")
            sys.exit(0)

    # Perform operations
    for cloud in clouds:
        crc = CRC(
            cloud,
            dry_run,
            notags,
            slack_client,
            influxdb_client,
            project_id,
            resource_group,
            slack_channel,
            influxdb,
        )
        for resource in resources:
            if resource == "disk":
                if cloud == "aws" and not aws_disk_opt_in:
                    raise ValueError(
                        "AWS EBS volume cleanup requires '--cloud aws --resource disk'. "
                        "Refusing to continue so --cloud all / --resource all does not "
                        "skip EBS and then delete other AWS resources, and so "
                        "--cloud all --resource disk does not reach other clouds' disks."
                    )
                crc.delete_disks(
                    filter_tags,
                    exception_tags,
                    age,
                    custom_age_tag_key,
                    detach_age,
                    name_regex,
                    exception_regex,
                    slack_notify_users,
                    slack_user_label,
                )
            elif resource == "ip":
                crc.delete_ip(
                    filter_tags,
                    exception_tags,
                    name_regex,
                    exception_regex,
                )
            elif resource == "keypair":
                crc.delete_keypairs(name_regex, exception_regex, age)
            elif resource == "nic":
                crc.delete_nic(name_regex, exception_regex)
            elif resource == "vm":
                if operation_type == "delete":
                    crc.delete_vm(
                        filter_tags,
                        exception_tags,
                        age,
                        custom_age_tag_key,
                        resource_states,
                    )
                elif operation_type == "stop":
                    crc.stop_vm(filter_tags, exception_tags, age, custom_age_tag_key)
            elif resource == "vpc":
                crc.delete_vpc(filter_tags, exception_tags)
            elif resource == "kms":
                crc.delete_kms(
                    filter_tags,
                    exception_tags,
                    kms_key_description,
                    kms_user,
                    kms_pending_window,
                    age,
                    custom_age_tag_key,
                )
            elif resource == "spot_instance_requests":
                if crc.cloud != "aws":
                    logging.warning(
                        "spot_instance_requests is AWS-only; skipped for %s "
                        "(use --resource spot_instances)",
                        crc.cloud,
                    )
                    continue
                crc.delete_spot_instance_requests(
                    filter_tags, exception_tags, age, custom_age_tag_key
                )
            elif resource == "spot_instances":
                if crc.cloud == "aws":
                    logging.warning(
                        "For AWS use --resource spot_instance_requests "
                        "(cancel request before terminate). Skipping spot_instances."
                    )
                    continue
                if crc.cloud in ("gcp", "oci") and cloud_arg == "all":
                    logging.warning(
                        "GCP/OCI spot_instances require explicit --cloud %s "
                        "(not --cloud all); skipped. Azure spot_instances still runs "
                        "under --cloud all for backward compatibility.",
                        crc.cloud,
                    )
                    continue
                # Fail closed: missing --resource_group / --project_id / --age
                # must raise (do not continue into other clouds under --cloud all).
                crc.delete_spot_instances(
                    filter_tags, exception_tags, age, custom_age_tag_key
                )
            elif resource == "snapshot":
                snapshot = Snapshot(
                    dry_run=dry_run,
                    age_days=90,
                    exception_tags=exception_tags
                )
                snapshot.delete()
                if dry_run:
                    msg = (
                        f"DRY RUN: AWS Snapshots eligible for deletion (>{snapshot.age_days} days): "
                        f"{snapshot.delete_count}"
                    )
                else:
                    msg = crc.get_msg("Snapshot", "Deleted", snapshot.get_deleted)
                print(msg)
                    
    if max_age:
        del os.environ["MAX_AGE"]
        print("MAX_AGE reset.")


if __name__ == "__main__":
    main()
