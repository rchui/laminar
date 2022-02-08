import os
import re
import sys
from importlib.machinery import SourceFileLoader

VERSION = "laminar/version.py"


def main(env_var: str = "GITHUB_REF") -> int:
    # Get git tag
    git_ref = os.getenv(env_var, "none")
    tag = re.sub("^refs/tags/v*", "", git_ref.lower())

    # Get package version
    version = str(SourceFileLoader("version", VERSION).load_module().VERSION).lower()

    # Enforce matching version
    if tag == version:
        print(f"✓ {env_var} env var {git_ref!r} matches package version: {tag!r} == {version!r}")
        return 0
    else:
        print(f"✖ {env_var} env var {git_ref!r} does not match package version: {tag!r} != {version!r}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
