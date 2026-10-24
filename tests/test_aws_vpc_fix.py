"""BUG-012, BUG-083, BUG-087 and BUG-088 of `crc.aws.vpc` (no cloud calls)."""

import datetime
import logging
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from botocore.exceptions import ClientError

from crc.aws.vpc import VpcCleaner
from crc.core import engine, logger
from crc.core.cleaner import Operation, RunContext
from crc.core.registry import Registry
from crc.core.selection import Selection
from tests.test_aws_vpc_parity import (
    ENV,
    MUTATING,
    PROD,
    W2,
    Case,
    FakeAws,
    FakeClient,
    FakeResource,
    FakeVpc,
    Sub,
    V,
    full,
)

NOW = datetime.datetime(2026, 3, 1, 12, 0, 0)
FILTER = {"env": ["test"]}
ATTEMPTS = 5


def _violation() -> Exception:
    error: Exception = ClientError(
        {"Error": {"Code": "DependencyViolation", "Message": "in use"}}, "DeleteVpc"
    )
    return error


def _denied() -> Exception:
    error: Exception = ClientError({"Error": {"Code": "UnauthorizedOperation"}}, "DeleteVpc")
    return error


class _Done:
    """The ids the engine run deleted (listed in a dry run)."""

    def __init__(self, get_deleted: list[str]) -> None:
        self.get_deleted = get_deleted


def _engine_run(cleaner: VpcCleaner, *, dry_run: bool) -> _Done:
    registry = Registry()
    registry.register("aws", "vpc")(lambda ctx: cleaner)
    ctx = RunContext(dry_run=dry_run, operation=Operation.DELETE, options={}, now=NOW)
    (outcome,) = engine.run(Selection((("aws", "vpc"),)), ctx, registry)
    ids = outcome.plan.candidates if outcome.result is None else outcome.result.succeeded
    return _Done([c if isinstance(c, str) else c.id for c in ids])


def _run(
    aws: FakeAws,
    sleeps: list[float],
    *,
    filter_tags: Any = FILTER,
    exception_tags: Any = None,
    notags: Any = None,
    dry_run: bool = False,
) -> _Done:
    cleaner = VpcCleaner(
        lambda region: FakeClient(aws, region),
        lambda region: FakeResource(aws, region),
        lambda: list(aws.case.regions),
        filter_tags,
        exception_tags,
        notags,
    )
    cleaner.sleep = sleeps.append
    return _engine_run(cleaner, dry_run=dry_run)


def _mutating(aws: FakeAws) -> list[tuple[Any, ...]]:
    return [c for c in aws.calls if c[0] in MUTATING]


@pytest.fixture(autouse=False)
def quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("crc.service.init_logging", lambda *args, **kwargs: None)


@pytest.mark.usefixtures("quiet")
@pytest.mark.parametrize("filter_tags", [None, {}])
@pytest.mark.parametrize("dry_run", [True, False])
def test_empty_filter_tags_raises_before_any_sdk_call(filter_tags: Any, dry_run: bool) -> None:
    aws = FakeAws(Case("x", {W2: [full("vpc-1")]}))
    with pytest.raises(ValueError, match="non-empty filter_tags"):
        _run(aws, [], filter_tags=filter_tags, dry_run=dry_run)
    assert aws.calls == []


@pytest.mark.parametrize("filter_tags", [None, {}])
def test_cleaner_plan_with_empty_filter_tags_raises_before_any_sdk_call(filter_tags: Any) -> None:
    aws = FakeAws(Case("x", {W2: [full("vpc-1")]}))
    cleaner = VpcCleaner(
        lambda region: FakeClient(aws, region),
        lambda region: FakeResource(aws, region),
        lambda: [W2],
        filter_tags,
        None,
        None,
    )
    ctx = RunContext(dry_run=True, operation=Operation.DELETE, options={}, now=NOW)
    with pytest.raises(ValueError, match="non-empty filter_tags"):
        cleaner.plan(ctx)
    assert aws.calls == []


@pytest.mark.usefixtures("quiet")
def test_default_vpc_is_never_touched_and_never_listed() -> None:
    aws = FakeAws(Case("x", {W2: [V("vpc-d", is_default=True), full("vpc-1")]}))
    vpc = _run(aws, [])
    assert vpc.get_deleted == ["vpc-1"]
    assert not any("vpc-d" in str(c) and c[0] in MUTATING for c in aws.calls)
    assert ("delete_vpc", W2, "vpc-d") not in aws.calls


@pytest.mark.usefixtures("quiet")
def test_default_vpc_dry_run_is_not_listed() -> None:
    aws = FakeAws(Case("x", {W2: [V("vpc-d", is_default=True)]}))
    assert _run(aws, [], dry_run=True).get_deleted == []


def test_cleaner_plan_skips_default_vpc() -> None:
    aws = FakeAws(Case("x", {W2: [V("vpc-d", is_default=True), V("vpc-1")]}))
    cleaner = VpcCleaner(
        lambda region: FakeClient(aws, region),
        lambda region: FakeResource(aws, region),
        lambda: [W2],
        FILTER,
        None,
        None,
    )
    ctx = RunContext(dry_run=False, operation=Operation.DELETE, options={}, now=NOW)
    plan = cleaner.plan(ctx)
    assert [c.id for c in plan.candidates] == ["vpc-1"]
    assert [s.id for s in plan.skipped] == ["vpc-d"]
    assert _mutating(aws) == []


@pytest.mark.usefixtures("quiet")
@pytest.mark.parametrize(
    ("tags", "exception_tags", "notags", "deleted"),
    [
        (PROD, {"env": ["prod"]}, None, False),
        (ENV, {"env": ["prod"]}, None, True),
        (ENV, None, {"env": [], "owner": []}, False),
        (None, {"env": []}, None, True),
    ],
)
def test_protection_uses_the_vpc_tags_not_the_resource(
    tags: Any, exception_tags: Any, notags: Any, deleted: bool
) -> None:
    class RealLikeResource(FakeResource):
        def __init__(self, aws_obj: FakeAws, region: str) -> None:
            super().__init__(aws_obj, region)

            def _filter(*, Filters: Sequence[Mapping[str, Any]]) -> list[FakeVpc]:
                aws_obj.calls.append(("vpcs.filter", region, str(list(Filters))))
                return [FakeVpc(aws_obj, region, v) for v in aws_obj.case.regions[region]]

            self.vpcs.filter = _filter  # type: ignore[method-assign]

    aws = FakeAws(Case("x", {W2: [full("vpc-1", tags)]}))
    cleaner = VpcCleaner(
        lambda region: FakeClient(aws, region),
        lambda region: RealLikeResource(aws, region),
        lambda: list(aws.case.regions),
        FILTER,
        exception_tags,
        notags,
    )
    _engine_run(cleaner, dry_run=False)
    assert (("delete_vpc", W2, "vpc-1") in aws.calls) is deleted


@pytest.mark.usefixtures("quiet")
def test_default_vpc_and_has_instances_log_skips_and_debug_reason(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    aws = FakeAws(
        Case(
            "x",
            {
                W2: [
                    V("vpc-d", is_default=True),
                    V("vpc-1", subnets=[Sub("s-1", ["i-1"])]),
                ]
            },
        )
    )
    logger.begin("aws", "vpc", "delete", False, {})
    try:
        _run(aws, [])
    finally:
        logger.finish()
    messages = [r.getMessage() for r in caplog.records if r.levelno >= logging.INFO]
    assert "SKIPPED cloud=aws resource=vpc reason=default_vpc count=1" in messages
    assert "SKIPPED cloud=aws resource=vpc reason=has_instances count=1" in messages
    assert (logging.DEBUG, "Keeping VPC vpc-1: instances in its subnets") in [
        (r.levelno, r.getMessage()) for r in caplog.records
    ]


@pytest.mark.usefixtures("quiet")
def test_vpc_with_instances_is_kept_untouched_and_instances_not_terminated() -> None:
    aws = FakeAws(Case("x", {W2: [V("vpc-1", subnets=[Sub("s-1", ["i-1"])]), full("vpc-2")]}))
    vpc = _run(aws, [])
    assert not any("vpc-1" in str(c) for c in _mutating(aws))
    assert not any(c[0] == "instance.terminate" for c in aws.calls)
    assert ("delete_vpc", W2, "vpc-1") not in aws.calls
    assert vpc.get_deleted == ["vpc-2"]


def test_cleaner_apply_reports_only_deleted_vpcs() -> None:
    aws = FakeAws(Case("x", {W2: [V("vpc-1", subnets=[Sub("s-1", ["i-1"])]), V("vpc-2")]}))
    cleaner = VpcCleaner(
        lambda region: FakeClient(aws, region),
        lambda region: FakeResource(aws, region),
        lambda: [W2],
        FILTER,
        None,
        None,
    )
    ctx = RunContext(dry_run=False, operation=Operation.DELETE, options={}, now=NOW)
    result = cleaner.apply(cleaner.plan(ctx), ctx)
    assert result.succeeded == ("vpc-2",)
    assert ("delete_vpc", W2, "vpc-1") not in aws.calls


@pytest.mark.usefixtures("quiet")
def test_dependency_violation_is_retried_with_a_sleep_between_attempts() -> None:
    key = ("delete_vpc", W2, "vpc-1")
    aws = FakeAws(
        Case("x", {W2: [full("vpc-1")]}, errors={key: [_violation(), _violation(), None]})
    )
    sleeps: list[float] = []
    vpc = _run(aws, sleeps)
    assert sum(1 for c in aws.calls if c == key) == ATTEMPTS - 2
    assert len(sleeps) == ATTEMPTS - 3
    assert all(s > 0 for s in sleeps)
    assert vpc.get_deleted == ["vpc-1"]


@pytest.mark.usefixtures("quiet")
def test_dependency_violation_every_attempt_gives_up_after_five_and_skips_the_vpc() -> None:
    key = ("delete_vpc", W2, "vpc-1")
    aws = FakeAws(
        Case(
            "x",
            {W2: [full("vpc-1"), full("vpc-2")]},
            errors={key: [_violation()] * 9},
        )
    )
    sleeps: list[float] = []
    vpc = _run(aws, sleeps)
    assert sum(1 for c in aws.calls if c == key) == ATTEMPTS
    assert len(sleeps) == ATTEMPTS - 1
    assert vpc.get_deleted == ["vpc-2"]


@pytest.mark.usefixtures("quiet")
def test_other_error_is_not_retried_and_the_vpc_is_skipped() -> None:
    key = ("delete_vpc", W2, "vpc-1")
    aws = FakeAws(Case("x", {W2: [full("vpc-1"), full("vpc-2")]}, errors={key: [_denied()]}))
    sleeps: list[float] = []
    vpc = _run(aws, sleeps)
    assert sum(1 for c in aws.calls if c == key) == 1
    assert sleeps == []
    assert vpc.get_deleted == ["vpc-2"]
    assert ("delete_vpc", W2, "vpc-2") in aws.calls
