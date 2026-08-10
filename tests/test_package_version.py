import re
from pathlib import Path

from muscles.asgi.__about__ import __version__


def test_runtime_version_matches_package_version():
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    package_version = re.search(
        r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE
    )

    assert package_version is not None
    assert __version__ == package_version.group(1)
