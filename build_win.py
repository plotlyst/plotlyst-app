import argparse
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from bump_premium_version import read_version, bump_middle_version, write_version

BUILD_DIR = Path('build')
DIST_DIR = Path('dist')
RES_WXS_TEMPLATE = Path('resources/plotlyst.wxs')
APP_WXS_PATH = BUILD_DIR / 'plotlyst/windows/app/plotlyst.wxs'
TROUBLESHOOTING_FILE = Path('resources/plotlyst-troubleshooting.txt')


def clear_build_folder():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)


def run(cmd):
    print(f"Running: {cmd}")
    subprocess.run(cmd, shell=True, check=True)


def inject_wxs(version: str):
    def replace_version(match):
        return f'{match.group(1)}{version}{match.group(2)}'

    content = RES_WXS_TEMPLATE.read_text(encoding='utf-8')
    new_content = re.sub(
        r'(ProductVersion\s*=\s*")[^"]+(")',
        replace_version,
        content
    )
    APP_WXS_PATH.write_text(new_content, encoding='utf-8')


def zip_msi(version: str, output_name: str):
    msi_file = DIST_DIR / f"Plotlyst-{version}.msi"
    zip_path = DIST_DIR / output_name
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(msi_file, arcname=msi_file.name)
        zipf.write(TROUBLESHOOTING_FILE, arcname=TROUBLESHOOTING_FILE.name)


def build_distribution(identity: str, edition: str, version: str, zipname: str):
    clear_build_folder()
    run(f'python ..\\license\\activate.py {edition}')
    run('briefcase.exe create')
    inject_wxs(version)
    run('briefcase.exe build')
    run(f'briefcase.exe package --identity "{identity}"')
    zip_msi(version, zipname)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--identity', required=True, help='Code signing identity')
    args = parser.parse_args()

    original_version = read_version()
    if not original_version:
        raise RuntimeError("Could not read version from version.py")

    build_distribution(
        identity=args.identity,
        edition='free',
        version=original_version,
        zipname='Plotlyst-free.zip'
    )

    premium_version = bump_middle_version(original_version)
    print(premium_version)
    write_version(premium_version)
    build_distribution(
        identity=args.identity,
        edition='plus',
        version=premium_version,
        zipname='Plotlyst.zip'
    )

    write_version(original_version)


if __name__ == '__main__':
    main()
