import re
from pathlib import Path

VERSION_PY = Path('src/main/python/plotlyst/version.py')
PYPROJECT_TOML = Path('pyproject.toml')


def read_version():
    text = VERSION_PY.read_text(encoding='utf-8')
    match = re.search(r"plotlyst_product_version\s*=\s*'([\d\.]+)'", text)
    return match.group(1) if match else None


def write_version(version: str):
    new_py = re.sub(
        r"plotlyst_product_version\s*=\s*'[\d\.]+'",
        f"plotlyst_product_version = '{version}'",
        VERSION_PY.read_text(encoding='utf-8')
    )
    VERSION_PY.write_text(new_py, encoding='utf-8')

    new_toml = re.sub(
        r'version\s*=\s*"[0-9.]+"',
        f'version = "{version}"',
        PYPROJECT_TOML.read_text(encoding='utf-8')
    )
    PYPROJECT_TOML.write_text(new_toml, encoding='utf-8')


def bump_middle_version(version: str):
    major, minor, patch = map(int, version.split('.'))
    return f"{major}.{minor + 100}.{patch}"


if __name__ == '__main__':
    original_version = read_version()
    if not original_version:
        raise RuntimeError("Could not read version from version.py")

    premium_version = bump_middle_version(original_version)
    print(premium_version)
    write_version(premium_version)
