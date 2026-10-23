# crc.azu.ip

## Purpose

Azure public IP cleaner. `AzureIpCleaner` is a registered `Cleaner` (`@register("azure", "ip")`) that deletes unused IPs of the configured resource group; `IP` is the adapter `crc.py` uses.

Modules (split by responsibility in W2-AZU, no behaviour change):

- `client.py`: SDK Protocols
- `cleaner.py`: `AzureIpCleaner` and the registry factory
- `adapter.py`: the legacy `IP` class

## Public API

- `PublicIpOperations`: Protocol of the two public IP calls used, list and begin_delete; tests pass fakes.
- `IpNetworkClient`: Protocol of the network client part used (the public_ip_addresses operations).
- `AzureIpCleaner`: the Cleaner (supports, read-only plan, mutating apply, plus list_ips, decide and delete_candidate used by the adapter); the client factory is injected through the constructor.
- `build_ip_cleaner()`: registry factory behind @register("azure", "ip"); reads resource_group, filter_tags, exception_tags and notags from RunContext.options and builds the client from the Azure base.
- `IP`: adapter crc.py calls (delete(), get_deleted, count, deleted_ips, base); runs the cleaner IP by IP in the order of main.

## Safety Invariants

- Authoritative text: `CLEANUP_SAFETY.md`; the per-module invariants are in `crc/azu/README.md` (Azure IPs (AZ-1)). `plan()` makes no mutating call and never in a dry run (ARCH-005); the delete calls run from `apply()` and the adapter only.
- Selection: any-key `filter_tags`, `exception_tags` any key, `notags` all keys, kept when in use; no age gate (SAF-011 not met).
- Do not call real cloud APIs in tests; mock every SDK client.

## Extension Rules

1. Structure only in a refactor rung: keep call order, log text and swallowed errors as on `main`; behaviour fixes are separate rungs (`docs/refactor/PLAN.md`).
2. Reach the SDK only through the Protocols in `client.py`; shared log and skip helpers live in `crc/azu/_common.py`.
3. `from crc.azu.ip import ...` must keep working for every public name; update this README with any public change.
