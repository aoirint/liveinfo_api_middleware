import tomllib
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from logging import getLogger
from pathlib import Path

logger = getLogger(__name__)


@lru_cache
def get_version() -> str:
    package = __package__ or __name__

    try:
        return version(package)
    except PackageNotFoundError:
        # Ignore PackageNotFoundError and fallback to reading from pyproject.toml
        pass

    project_dir = Path(__file__).parent.parent.parent
    pyproject_file = project_dir / "pyproject.toml"

    try:
        with pyproject_file.open("rb") as fp:
            pyproject_data = tomllib.load(fp)
            if "project" not in pyproject_data:
                raise Exception("Invalid pyproject.toml: 'project' section is missing.")

            project_info = pyproject_data["project"]
            if "version" not in project_info:
                raise Exception(
                    "Invalid pyproject.toml: 'version' field is missing in 'project' section."  # noqa: E501
                )

            pyproject_version = project_info["version"]
            if not isinstance(pyproject_version, str):
                raise Exception(
                    "Invalid pyproject.toml: 'version' field is not a string."
                )

            return pyproject_version
    except Exception:
        logger.exception(
            "Failed to read version from pyproject.toml. Falling back to '0.0.0'."
        )

    return "0.0.0"
