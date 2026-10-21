# ST-AWS-VM pending bugs and quirks

Columns as in `docs/refactor/BUGS.md`. Rung ST-AWS-VM is a pure move of `crc/aws/vm.py`, `vm_api.py`, `vm_cleaner.py` and `vm_scan.py` into `crc/aws/vm/`; it changes no behaviour and found no new bug or quirk. The quirks of the VM cleaner stay registered as BUG-004, BUG-020, BUG-021 and BUG-213 to BUG-227.

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
