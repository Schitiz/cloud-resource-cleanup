"""AWS route table: the kinds run through `crc.core.engine`. Copy this file's shape per kind."""

from typing import Any

import crc.aws.keypairs  # noqa: F401 - importing the package registers the cleaner
from crc.cli.inputs import Options
from crc.cli.routes import Route


def _keypair(options: Options) -> dict[str, Any]:
    return {
        "name_regex": options.name_regex,
        "exception_regex": options.exception_regex,
        "age": options.age,
    }


ROUTES: dict[str, Route] = {
    "keypair": Route(_keypair),
}
