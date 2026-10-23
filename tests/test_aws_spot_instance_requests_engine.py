"""Cleaner-based copy of the main locked safety cases of `tests/test_aws_spot_instance_requests.py`.

The locked file builds the `SpotInstanceRequests` adapter; these tests drive `SpotRequestCleaner`
through `crc.core.engine.run` (or `plan()` for the read-only cases) on the recording fake AWS of
`tests/test_aws_spot_instance_requests_parity.py`. Covered: SAF-007, 008, 011, 026, 027, 028, 029
and 035. The tag, volume and terminate-error cases (SAF-030 to SAF-033) stay in the locked file
until the owner swaps it (see docs/refactor/reviews/ENG-1.md).
"""

from typing import Any

import pytest

from crc.aws.spot_instance_requests import SpotRequestCleaner, SpotRuntime
from crc.aws.spot_instance_requests.model import Waiter
from crc.core import engine, registry
from crc.core.cleaner import Operation, RunContext
from crc.core.registry import Registry
from crc.core.selection import Selection
from tests.test_aws_spot_instance_requests_cleaner import MUTATING, OPTIONS, _methods, _setup
from tests.test_aws_spot_instance_requests_parity import (
    NOW,
    QA,
    Case,
    FakeAws,
    ce,
    inst,
    one,
    req,
    std,
)


def plan_ids(case: Case, monkeypatch: pytest.MonkeyPatch, **options: Any) -> list[str]:
    ctx = RunContext(True, Operation.DELETE, {**OPTIONS, **options}, NOW)
    aws = FakeAws(case)
    monkeypatch.setattr("boto3.client", aws.client)
    monkeypatch.setattr("crc.service.init_logging", lambda *args, **kwargs: None)
    cleaner = registry.get("aws", "spot_instance_requests")(ctx)
    cleaner.runtime = _runtime(cleaner, case, aws)  # type: ignore[attr-defined]
    return [c.id for c in cleaner.plan(ctx).candidates]


def _runtime(cleaner: Any, case: Case, aws: FakeAws) -> Any:
    return SpotRuntime(
        client_factory=cleaner.runtime.client_factory,
        list_regions=lambda: list(case.regions),
        clock=lambda: NOW,
        waiter=Waiter(aws.sleep, aws.monotonic),
    )


def run_engine(
    case: Case, monkeypatch: pytest.MonkeyPatch, *, dry_run: bool
) -> tuple[FakeAws, engine.RunOutcome]:
    aws, cleaner, ctx = _setup(case, monkeypatch, dry_run)
    local = Registry()
    local.register("aws", "spot_instance_requests")(lambda context: cleaner)
    selection = Selection(items=(("aws", "spot_instance_requests"),))
    return aws, engine.run(selection, ctx, local)[0]


@pytest.mark.parametrize("age", [{}, {"days": 0}, None])
def test_saf_007_011_027_a_positive_age_is_required(age: Any) -> None:
    ctx = RunContext(
        False, Operation.DELETE, {"filter_tags": {"yb_owner": ["qa"]}, "age": age}, NOW
    )
    with pytest.raises(ValueError):
        registry.get("aws", "spot_instance_requests")(ctx)


@pytest.mark.parametrize("bad", ["{'day': 30}", "never", "30d", "{days: 30}", "{'days': 30"])
def test_saf_008_an_invalid_or_unparseable_custom_age_tag_skips_the_request(
    bad: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    tags = [*QA, {"Key": "retention", "Value": bad}]
    case = Case("x", one(std(requests=[req(tags=tags)])))
    assert plan_ids(case, monkeypatch, custom_age_tag_key="retention") == []


def test_saf_026_tags_are_matched_on_the_request_not_the_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = Case(
        "x", one(std(requests=[req(instance="i-untagged")], instances={"i-untagged": inst()}))
    )
    assert plan_ids(case, monkeypatch)[0] == "sir-1"


def test_saf_026_untagged_requests_are_skipped_even_without_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = Case("x", one(std(requests=[req(tags=[])])))
    assert plan_ids(case, monkeypatch, filter_tags={}) == []


def test_saf_029_a_cancelled_request_with_an_instance_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = Case("x", one(std(requests=[req(state="cancelled", instance="i-1")])))
    assert plan_ids(case, monkeypatch)[0] == "sir-1"


def test_saf_029_a_cancelled_request_without_an_instance_is_not_planned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = Case("x", one(std(requests=[req(state="cancelled", instance=None)])))
    assert plan_ids(case, monkeypatch) == []


def test_saf_028_cancel_comes_before_terminate_and_leftover_volume_is_deleted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aws, outcome = run_engine(Case("x", one(std())), monkeypatch, dry_run=False)
    order = [m for m in _methods(aws) if m in MUTATING]
    assert order == [
        "create_tags",
        "cancel_spot_instance_requests",
        "terminate_instances",
        "delete_volume",
    ]
    assert outcome.result is not None
    assert outcome.result.related["Disk"] == ("vol-1",)


def test_saf_028_a_failed_cancel_does_not_terminate_a_persistent_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    denied = ce("UnauthorizedOperation", "CancelSpotInstanceRequests")
    spec = std(errors={"cancel_spot_instance_requests": denied})
    aws, outcome = run_engine(Case("x", one(spec)), monkeypatch, dry_run=False)
    assert "terminate_instances" not in _methods(aws)
    assert outcome.result is not None
    assert outcome.result.succeeded == ()


def test_saf_028_a_failed_volume_tag_does_not_terminate(monkeypatch: pytest.MonkeyPatch) -> None:
    denied = ce("UnauthorizedOperation", "CreateTags")
    aws, outcome = run_engine(
        Case("x", one(std(errors={"create_tags": denied}))), monkeypatch, dry_run=False
    )
    methods = _methods(aws)
    assert "terminate_instances" not in methods
    assert "cancel_spot_instance_requests" not in methods
    assert outcome.result is not None
    assert outcome.result.succeeded == ()


def test_saf_029_an_already_cancelled_request_skips_cancel_then_terminates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = Case("x", one(std(requests=[req(state="cancelled", instance="i-1")])))
    aws, outcome = run_engine(case, monkeypatch, dry_run=False)
    methods = _methods(aws)
    assert "cancel_spot_instance_requests" not in methods
    assert "terminate_instances" in methods
    assert outcome.result is not None
    assert "i-1" in outcome.result.succeeded


def test_saf_035_a_cancelled_request_whose_instance_is_gone_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = std(
        requests=[req(state="cancelled", instance="i-1")],
        instances={"i-1": inst(state="terminated", dot_false=())},
        volumes={},
    )
    aws, outcome = run_engine(Case("x", one(spec)), monkeypatch, dry_run=False)
    assert not MUTATING & set(_methods(aws))
    assert outcome.result is not None
    assert outcome.result.succeeded == ()


def test_the_registered_cleaner_is_the_spot_request_cleaner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, cleaner, _ = _setup(Case("x", one(std())), monkeypatch, True)
    assert isinstance(cleaner, SpotRequestCleaner)
