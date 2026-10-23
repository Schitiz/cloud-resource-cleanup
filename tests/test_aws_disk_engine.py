"""Cleaner-based copy of the locked `tests/test_aws_disk.py` safety cases (SAF-003, 007, 011, 012,
013, 015, 017, 018, 019, 020, 025).

The locked file builds the `Disk` adapter; these tests drive `DiskCleaner` through
`crc.core.engine.run` (or `plan()` for the read-only cases) with fake EC2 and CloudWatch clients,
for the owner to swap in and relock once the adapter is gone.
"""

import datetime
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pytest
from botocore.exceptions import ClientError

from crc.aws.disk import DiskCleaner, DiskRuntime
from crc.aws.disk.settings import build_settings
from crc.core import engine
from crc.core.cleaner import Operation, Plan, RunContext
from crc.core.registry import Registry
from crc.core.selection import Selection

NOW = datetime.datetime(2026, 3, 1, 12, 0, 0, tzinfo=datetime.UTC)
REGION = "us-west-2"
PAGES = 2
SUFFIXES = ("idletime", "readops", "writeops")


class FakeEc2:
    def __init__(self, volumes: list[dict[str, Any]], failing: Sequence[str] = ()) -> None:
        self.volumes = volumes
        self.failing = failing
        self.deleted: list[str] = []

    def get_paginator(self, name: str) -> "FakeEc2":
        return self

    def paginate(self, *, Filters: Sequence[Mapping[str, Any]]) -> Iterable[Mapping[str, Any]]:
        return [{"Volumes": self.volumes}]

    def delete_volume(self, *, VolumeId: str) -> Mapping[str, Any]:
        if VolumeId in self.failing:
            raise ClientError({"Error": {"Code": "VolumeInUse", "Message": "in use"}}, "x")
        self.deleted.append(VolumeId)
        return {}


class ScriptedCloudWatch:
    """Answers `get_metric_data` with the scripted responses in order; an exception is raised."""

    def __init__(self, *responses: Any) -> None:
        self.responses = list(responses)
        self.calls = 0

    def get_metric_data(self, **kwargs: Any) -> Mapping[str, Any]:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response  # type: ignore[no-any-return]


def volume(volume_id: str = "vol-1", days: float = 30, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "VolumeId": volume_id,
        "State": "available",
        "Attachments": [],
        "CreateTime": NOW - datetime.timedelta(days=days),
        "Tags": [{"Key": "yb_task", "Value": "itest"}, {"Key": "Name", "Value": "foo"}],
    }
    item.update(extra)
    return item


def ids_for(index: int) -> list[str]:
    return [f"m{index}{suffix}" for suffix in SUFFIXES]


def complete(query_id: str, values: list[float] | None = None) -> dict[str, Any]:
    return {"Id": query_id, "StatusCode": "Complete", "Values": values or []}


def cleaner(
    ec2: FakeEc2, cloudwatch: ScriptedCloudWatch | None = None, **options: Any
) -> DiskCleaner:
    runtime = DiskRuntime(
        ec2_factory=lambda region: ec2,
        cloudwatch_factory=lambda region: cloudwatch or ScriptedCloudWatch(),
        list_regions=lambda: [REGION],
    )
    return DiskCleaner(build_settings({"age": {"hours": 6}, **options}), runtime)


def context(*, dry_run: bool = True) -> RunContext:
    return RunContext(dry_run=dry_run, operation=Operation.DELETE, options={}, now=NOW)


def plan_ids(disk: DiskCleaner) -> list[str]:
    plan: Plan = disk.plan(context())
    return [str(c.extra["VolumeId"]) for c in plan.candidates]


def run_engine(disk: DiskCleaner, *, dry_run: bool) -> engine.RunOutcome:
    registry = Registry()
    registry.register("aws", "disk")(lambda ctx: disk)
    selection = Selection(items=(("aws", "disk"),))
    return engine.run(selection, context(dry_run=dry_run), registry)[0]


def test_saf_003_had_errors_logs_without_raising() -> None:
    ec2 = FakeEc2([volume("vol-ok"), volume("vol-bad")], failing=["vol-bad"])
    disk = cleaner(ec2)
    outcome = run_engine(disk, dry_run=False)
    assert disk.had_errors is True
    assert outcome.result is not None
    assert list(outcome.result.succeeded) == ["us-west-2/vol-ok yb_task=itest"]
    assert ec2.deleted == ["vol-ok"]


@pytest.mark.parametrize("age", [None, {}])
def test_saf_011_and_018_an_age_gate_is_required(age: Any) -> None:
    with pytest.raises(ValueError, match="requires an age gate"):
        build_settings({"age": age})


@pytest.mark.parametrize(
    "options",
    [
        {"age": None, "detach_age": {"minutes": 30}},
        {"age": None, "detach_age": {"day": 3}},
        {"age": None, "detach_age": {"days": 0}},
        {"age": {"hours": 0}},
        {"age": None, "detach_age": {"days": 900}},
    ],
)
def test_saf_007_and_012_unknown_or_zero_age_units_are_rejected(options: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        build_settings(options)


def test_saf_017_age_gate_message_does_not_claim_last_detach() -> None:
    with pytest.raises(ValueError) as error:
        build_settings({"age": None, "detach_age": None})
    assert "measured from last attachment" not in str(error.value)
    assert "running instance" in str(error.value)


def test_saf_018_detach_age_alone_is_enough() -> None:
    settings = build_settings({"age": None, "detach_age": {"days": 3}})
    assert settings.age == {}
    assert settings.detach_age == {"days": 3}


def test_saf_019_detach_age_only_still_floors_on_create_time() -> None:
    brand_new = volume("vol-new", days=5 / 86400)
    disk = cleaner(FakeEc2([brand_new]), age=None, detach_age={"days": 3})
    assert plan_ids(disk) == []


def test_saf_025_detach_age_only_uses_max_of_retention_and_detach() -> None:
    tags = [
        {"Key": "yb_task", "Value": "itest"},
        {"Key": "max_retention_age", "Value": "{'days': 1}"},
    ]
    young = volume("young", days=3, Tags=tags)
    old = volume("old", days=10, Tags=tags)
    cloudwatch = ScriptedCloudWatch({"MetricDataResults": [complete(q) for q in ids_for(0)]})
    disk = cleaner(
        FakeEc2([young, old]),
        cloudwatch,
        age=None,
        detach_age={"days": 7},
        custom_age_tag_key="max_retention_age",
    )
    assert plan_ids(disk) == ["old"]


def test_saf_012_zero_custom_age_tag_skips_volume() -> None:
    tags = [
        {"Key": "yb_task", "Value": "itest"},
        {"Key": "max_retention_age", "Value": "{'days': 0}"},
    ]
    disk = cleaner(
        FakeEc2([volume(days=30, Tags=tags)]),
        age=None,
        detach_age={"days": 7},
        custom_age_tag_key="max_retention_age",
    )
    assert plan_ids(disk) == []


def test_saf_013_max_age_env_cannot_shorten_detach_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_AGE", "{'hours': 1}")
    disk = cleaner(FakeEc2([volume(days=2)]), age=None, detach_age={"days": 7})
    assert plan_ids(disk) == []


def detach_run(*responses: Any) -> tuple[list[str], DiskCleaner, ScriptedCloudWatch]:
    cloudwatch = ScriptedCloudWatch(*responses)
    disk = cleaner(
        FakeEc2([volume("vol-idle"), volume("vol-busy")]), cloudwatch, detach_age={"days": 3}
    )
    return plan_ids(disk), disk, cloudwatch


def test_saf_015_incomplete_status_keeps_the_volume() -> None:
    results = [complete(q) for q in ids_for(0)]
    results.append({"Id": ids_for(1)[0], "StatusCode": "Forbidden", "Values": []})
    results.extend(complete(q) for q in ids_for(1)[1:])
    kept, _, _ = detach_run({"MetricDataResults": results})
    assert kept == ["vol-idle"]


def test_saf_015_cloudwatch_failure_drops_the_batch() -> None:
    error = ClientError({"Error": {"Code": "AccessDenied"}}, "GetMetricData")
    kept, disk, _ = detach_run(error)
    assert kept == []
    assert disk.had_errors is True


def test_saf_020_paginates_next_token() -> None:
    page1 = {"MetricDataResults": [complete(q) for q in ids_for(0)], "NextToken": "t1"}
    page2 = {"MetricDataResults": [complete(q) for q in ids_for(1)]}
    kept, _, cloudwatch = detach_run(page1, page2)
    assert cloudwatch.calls == PAGES
    assert kept == ["vol-idle", "vol-busy"]


def test_saf_020_merge_metric_pages_keeps_earlier_values() -> None:
    busy = ids_for(1)[0]
    page1 = {
        "MetricDataResults": [{"Id": busy, "StatusCode": "PartialData", "Values": [1.0]}],
        "NextToken": "t1",
    }
    page2 = {
        "MetricDataResults": [
            complete(busy),
            *[complete(q) for q in ids_for(0) + ids_for(1)[1:]],
        ]
    }
    kept, _, _ = detach_run(page1, page2)
    assert kept == ["vol-idle"]
