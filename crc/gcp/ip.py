# Copyright (c) Yugabyte, Inc.

"""GCP IP address cleaner.

`IpCleaner` implements the `crc.core.cleaner.Cleaner` contract: `plan()` lists the regions and
their addresses and filters them, `apply()` deletes the planned RESERVED addresses.
`IP` is the legacy class `crc.py` uses; it keeps its constructor and attributes and runs the
cleaner region by region, in the exact call order of the original implementation.
"""

import logging
from collections.abc import Iterable, Sequence
from typing import Protocol

from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import GoogleAuthError
from google.cloud import compute_v1

from crc.core import logger, policy
from crc.core.cleaner import (
    Candidate,
    Cleaner,
    Failure,
    Operation,
    Plan,
    Result,
    RunContext,
    Skipped,
)
from crc.core.registry import register
from crc.gcp._scan import ZoneScan
from crc.service import Service

_RESERVED = "RESERVED"


class AddressView(Protocol):
    """The two fields of a GCP address this cleaner reads."""

    @property
    def name(self) -> str:
        """Name of the address."""
        ...

    @property
    def status(self) -> str:
        """Address status, for example RESERVED or IN_USE."""
        ...


class OperationView(Protocol):
    """The long-running delete operation GCP returns; `result()` blocks until it is done and
    raises when it failed."""

    def result(self) -> object:
        """Wait for the operation to finish."""
        ...


class GcpIpClient(Protocol):
    """The three Compute Engine calls this cleaner uses."""

    def list_regions(self, project_id: str) -> Sequence[str]:
        """Names of the regions of the project."""
        ...

    def list_addresses(self, project_id: str, region: str) -> Iterable[AddressView]:
        """Addresses of one region."""
        ...

    def delete_address(self, project_id: str, region: str, address: str) -> OperationView:
        """Start the deletion of one address of a region."""
        ...


class ComputeIpClient:
    """`GcpIpClient` on google-cloud-compute. Like `main`, every call builds a new client."""

    def list_regions(self, project_id: str) -> Sequence[str]:
        regions = compute_v1.RegionsClient().list(project=project_id)
        return [region.name for region in regions]

    def list_addresses(self, project_id: str, region: str) -> Iterable[AddressView]:
        addresses: Iterable[AddressView] = compute_v1.AddressesClient().list(
            project=project_id, region=region
        )
        return addresses

    def delete_address(self, project_id: str, region: str, address: str) -> OperationView:
        operation: OperationView = compute_v1.AddressesClient().delete(
            project=project_id,
            region=region,
            address=address,
        )
        return operation


def _log_summary(deleted: Sequence[str], *, dry_run: bool) -> None:
    items = list(deleted)
    if not dry_run:
        logging.warning(f"number of GCP IPs deleted: {len(items)}")
        logging.warning(f"List of GCP IPs deleted: {items}")
    else:
        logging.warning(f"List of GCP IPs (Total: {len(items)}) which will be deleted: {items}")


class IpCleaner:
    """Deletes RESERVED addresses whose name contains a `filter_regex` entry (any; empty
    matches all) unless it contains an `exception_regex` entry (any; BUG-001 fixed). Applies
    to every region of the project. A failed delete is recorded and the next address goes on
    (BUG-063); an address counts as deleted only once its operation finished (BUG-064)."""

    cloud = "gcp"
    kind = "ip"

    def __init__(
        self,
        client: GcpIpClient,
        project_id: str,
        filter_regex: Sequence[str] | None,
        exception_regex: Sequence[str] | None,
        state: str = _RESERVED,
    ) -> None:
        self._client = client
        self._project_id = project_id
        self._filter_regex = filter_regex
        self._exception_regex = exception_regex
        self._state = state
        self.failures: list[Failure] = []

    def supports(self, operation: Operation) -> bool:
        return operation is Operation.DELETE

    def regions(self) -> Sequence[str]:
        """Region names of the project (read-only call)."""
        return self._client.list_regions(self._project_id)

    def plan(self, context: RunContext) -> Plan:
        """List every region and filter. Makes no mutating call."""
        candidates: list[Candidate] = []
        skipped: list[Skipped] = []
        for region in self.regions():
            region_plan = self.plan_region(region)
            candidates.extend(region_plan.candidates)
            skipped.extend(region_plan.skipped)
        if context.dry_run:
            for c in candidates:
                logger.current().action("would_delete", c.region, c.id, c.name)
            _log_summary([c.id for c in candidates], dry_run=True)
        return Plan(candidates=tuple(candidates), skipped=tuple(skipped))

    def apply(self, plan: Plan, context: RunContext) -> Result:
        """Delete the planned addresses, region by region (nothing in a dry run)."""
        by_region: dict[str, list[Candidate]] = {}
        for candidate in plan.candidates:
            by_region.setdefault(candidate.region, []).append(candidate)
        deleted: list[str] = []
        self.failures = []
        for region, items in by_region.items():
            deleted.extend(self.apply_region(region, items, dry_run=context.dry_run))
        _log_summary(deleted, dry_run=context.dry_run)
        return Result(succeeded=tuple(deleted), failed=tuple(self.failures))

    def plan_region(self, region: str) -> Plan:
        """List one region and decide, in the order of `main`: log the address, read its
        name, skip other states, then the filter and the exception test."""
        candidates: list[Candidate] = []
        skipped: list[Skipped] = []
        scan = ZoneScan(region)
        for address in self._client.list_addresses(self._project_id, region):
            logging.debug(address)
            scan.scanned += 1
            name = address.name
            if not policy.state_in(address.status, (self._state,)):
                skipped.append(Skipped(id=name, reason=f"status is not {self._state}", name=name))
                logger.current().skip("state")
                continue
            matches_filter = self._matches_filter(name)
            excluded = self._excluded(name)
            if matches_filter and not excluded:
                candidates.append(
                    Candidate(id=name, name=name, region=region, state=address.status)
                )
                scan.selected += 1
            else:
                reason = "no filter_regex match" if not matches_filter else "exception_regex"
                skipped.append(Skipped(id=name, reason=reason, name=name))
                logger.current().skip("filter_mismatch" if not matches_filter else reason)
        scan.finish()
        return Plan(candidates=tuple(candidates), skipped=tuple(skipped))

    def apply_region(
        self, region: str, candidates: Sequence[Candidate], *, dry_run: bool
    ) -> list[str]:
        """Delete `candidates` one by one and return the names deleted (all of them in a dry
        run, where nothing is deleted). A failed address is recorded in `failures` and skipped."""
        deleted: list[str] = []
        for candidate in candidates:
            if not dry_run and not self._delete(region, candidate):
                continue
            kind = "would_delete" if dry_run else "deleted"
            logger.current().action(kind, region, candidate.id, candidate.name)
            deleted.append(candidate.id)
        return deleted

    def _delete(self, region: str, candidate: Candidate) -> bool:
        try:
            self._client.delete_address(self._project_id, region, candidate.id).result()
        except (GoogleAPIError, GoogleAuthError, OSError) as e:
            logging.error(f"Error occurred while deleting IP address {candidate.id}: {e}")
            logger.current().fail(region, candidate.id, e)
            self.failures.append(Failure(id=candidate.id, error=str(e)))
            return False
        except Exception as e:
            logger.current().fail(region, candidate.id, e)
            raise
        logging.info(f"Deleting IP address: {candidate.id}")
        return True

    def _matches_filter(self, name: str) -> bool:
        return policy.filter_substring_matches(self._filter_regex or (), name)

    def _excluded(self, name: str) -> bool:
        return any(pattern in name for pattern in self._exception_regex or ())


@register("gcp", "ip")
def build_ip_cleaner(context: RunContext) -> Cleaner:
    """Registry factory. Options: `project_id`, `name_regex` and `exception_regex`."""
    options = context.options
    project_id = options.get("project_id")
    if not project_id:
        raise ValueError("project_id is required for GCP IP cleanup")
    return IpCleaner(
        client=ComputeIpClient(),
        project_id=project_id,
        filter_regex=options.get("name_regex"),
        exception_regex=options.get("exception_regex"),
    )


class IP(Service):
    """Legacy entry point used by `crc.py`: deletes RESERVED GCP addresses whose name contains
    a `filter_regex` entry and does not contain an `exception_regex` entry. In dry run it only
    lists them.

    Attributes: `default_state` ("RESERVED"), `deleted_ips` (names deleted, or listed in a dry
    run), `dry_run`, `project_id`, `filter_regex`, `exception_regex`. `get_deleted` and `count`
    read the result.
    """

    default_state = _RESERVED

    def __init__(
        self,
        dry_run: bool,
        project_id: str,
        filter_regex: Sequence[str] | None,
        exception_regex: Sequence[str] | None,
        client: GcpIpClient | None = None,
    ) -> None:
        super().__init__()
        self.deleted_ips: list[str] = []
        self.dry_run = dry_run
        self.project_id = project_id
        self.filter_regex = filter_regex
        self.exception_regex = exception_regex
        self._client: GcpIpClient = client or ComputeIpClient()

    @property
    def get_deleted(self) -> list[str]:
        """Names of the addresses deleted (listed in a dry run)."""
        return self.deleted_ips

    @property
    def count(self) -> int:
        """Number of addresses deleted (listed in a dry run); logs the count."""
        count = len(self.deleted_ips)
        logging.info(f"count of items in deleted_ips: {count}")
        return count

    def _cleaner(self) -> IpCleaner:
        return IpCleaner(
            self._client,
            self.project_id,
            self.filter_regex,
            self.exception_regex,
            self.default_state,
        )

    def delete(self) -> None:
        """Delete (or, in a dry run, only list) the matching addresses of every region."""
        cleaner = self._cleaner()
        for region in cleaner.regions():
            region_plan = cleaner.plan_region(region)
            deleted = cleaner.apply_region(region, region_plan.candidates, dry_run=self.dry_run)
            self.deleted_ips.extend(deleted)
        _log_summary(self.deleted_ips, dry_run=self.dry_run)
