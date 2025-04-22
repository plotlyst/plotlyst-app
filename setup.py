import json
import os
import re
from distutils.cmd import Command

from setuptools import setup


def get_briefcase_version():
    with open("pyproject.toml") as f:
        for line in f:
            match = re.search(r'version\s*=\s*[\'"]([^\'"]+)[\'"]', line)
            if match:
                return match.group(1)

    raise RuntimeError("Unable to find version in pyproject.toml")


def get_base_version():
    with open("src/main/python/plotlyst/version.py") as f:
        content = f.read()
        match = re.search(r"plotlyst_product_version = ['\"]([^'\"]+)['\"]", content)
        if match:
            return match.group(1)
        raise RuntimeError("Unable to find __version__ string in version.py")


def check_versions(base_version):
    pyproject_version = get_briefcase_version()
    if pyproject_version != base_version:
        raise RuntimeError(
            f"Version mismatch: [tool.briefcase] version is {pyproject_version}, but version.py has {base_version}")


def generate_json_file(version):
    settings = {
        "app_name": "Plotlyst",
        "author": "Zsolt Kovari",
        "main_module": "src/main/python/plotlyst/__main__.py",
        "version": version,
    }

    os.makedirs("src/build/settings", exist_ok=True)

    json_file_path = os.path.join("src", "build", "settings", "base.json")
    with open(json_file_path, 'w') as json_file:
        json.dump(settings, json_file, indent=4)


class GenerateJsonFileCommand(Command):
    description = "Generate JSON file with app settings."
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        version = get_base_version()
        check_versions(version)
        generate_json_file(version)
        print(f"JSON settings file generated with version {version}.")


version = get_base_version()
check_versions(version)

generate_json_file(version)

setup(
    version=version,
    cmdclass={
        'generate_json': GenerateJsonFileCommand,
    },
)
