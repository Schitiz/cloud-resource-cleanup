"""Pytest setup: install the `MAX_AGE` reader that `main()` installs in production.

`crc/core` reads no environment variable (ARCH-003); `crc.cli.main.main` gives `crc.core.age` a
source that reads `MAX_AGE`. Tests that call a cleaner or `is_old` without `main` and set the
variable with `monkeypatch` rely on the same production function, installed here.
"""

from crc.cli.context import install_max_age_source

install_max_age_source()
