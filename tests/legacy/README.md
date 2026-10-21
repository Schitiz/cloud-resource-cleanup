# tests/legacy

## Purpose

Frozen copies of `main` code, used as parity oracles. They are `.txt` files so they are never
linted, imported by the product or collected by pytest. `aws_keypairs.txt` is the exact output
of `git show main:crc/aws/keypairs.py`; `tests/test_aws_keypair_parity.py` loads it and runs it
against the refactored `crc.aws.keypairs`. `aws_elastic_ips.txt` is the exact output of
`git show main:crc/aws/elastic_ips.py`; `tests/test_aws_ip_parity.py` runs it against `crc.aws.elastic_ips`. `aws_kms.txt` is the exact output of
`git show main:crc/aws/kms.py`; `tests/test_aws_kms_parity.py` runs it against `crc.aws.kms`.

## Public API

This directory exposes no library, only reference text files.

## Safety Invariants

- Never edit an oracle file: it must stay byte-identical to `main` at the time it was frozen.
- Oracles run only against fake SDK clients; no network, no credentials.

## Extension Rules

1. A rung that refactors a module freezes `git show main:<path>` here as `<package>_<module>.txt`
   and adds a parity test next to the other tests.
2. Delete an oracle only in the rung that removes the behaviour it pins (a behaviour-fix rung).
