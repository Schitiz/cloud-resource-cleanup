# ST-AWS-VM pending bugs and quirks

Columns as in `docs/refactor/BUGS.md`. Rung ST-AWS-VM is a pure move of `crc/aws/vm.py`, `vm_api.py`, `vm_cleaner.py` and `vm_scan.py` into `crc/aws/vm/`; it changes no behaviour. Round 2 found one quirk of the moved code that is not registered yet (below). The quirks of the VM cleaner stay registered as BUG-004, BUG-020, BUG-021 and BUG-213 to BUG-227.

| ID | Title | Location on main | Exists on main | Effect | Risk | Found in | Status |
|----|-------|------------------|----------------|--------|------|----------|--------|
| NEW | `find_instances_with_tag` is annotated `List[Dict[str, str]]` but each record holds a `tags` dict, a `datetime` `launch_time` and possibly `None` `id` / `instance_type`; `state` is upper-cased (`RUNNING`) although the inline comment says `'running'`, `'stopped'`; and the name falls back to `tags.get("Name")`, the last `Name` value, when the first `Name` tag is empty, so an instance with duplicated `Name` tags gets a different name here than in the delete/stop path (`_get_instance_name`, first value) | `crc/aws/vm.py:110`, `:136-141`, `:290-292` | yes | cosmetic | low | ST-AWS-VM (round 2) | open |
