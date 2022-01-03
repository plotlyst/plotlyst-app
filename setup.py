from pathlib import Path

from setuptools import setup, find_packages

HERE = Path(__file__).parent.absolute()
with (HERE / 'README.md').open('rt') as fh:
    LONG_DESCRIPTION = fh.read().strip()

REQUIREMENTS: dict = {
    'core': [
        'PyQt6==6.2.0',
        'overrides==3.1.0',
        'qtawesome==1.1.1',
        'PyQt6-Charts==6.2',
        'anytree==2.8.0',
        'emoji==1.4.1',
        'fbs[sentry]',
        'atomicwrites==1.4.0',
        'dataclasses-json==0.5.2',
        'language-tool-python==2.6.1',
    ],
    'test': [
        'pytest==6.2.4',
        'pytest-qt==4.0.2',
        'pytest-cov==2.12.1',
        'pytest-randomly==3.10.3',
    ],
    'dev': [
        'pyqt6-tools',
    ],
    'doc': [
    ],
}

setup(
    name='plotlyst',
    version='0.1.0',

    author='Zsolt Kovari',
    author_email='',
    description='Plotlyst',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='',

    packages=find_packages(),
    python_requires='>=3.6, <4',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],

    install_requires=REQUIREMENTS['core'],
    extras_require={
        **REQUIREMENTS,
        # The 'dev' extra is the union of 'test' and 'doc', with an option
        # to have explicit development dependencies listed.
        'dev': [req
                for extra in ['dev', 'test', 'doc']
                for req in REQUIREMENTS.get(extra, [])],
        # The 'all' extra is the union of all requirements.
        'all': [req for reqs in REQUIREMENTS.values() for req in reqs],
    },
)
