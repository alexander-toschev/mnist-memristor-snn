"""Build a LOCAL wheel from an authorized legacy MemriBoard source directory.

Not an upstream release. No downloads, module injection, source modification,
private MemriCORE inclusion or publication. The operator supplies the source.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def build(source: Path, output: Path) -> None:
    source, output = source.resolve(), output.resolve()
    for required in ('manager/board.py', 'manager/service/converters.py', 'simulator/src.py', 'simulator/simulator_settings.ini', 'LICENSE'):
        if not (source / required).is_file():
            raise ValueError('Missing MemriBoard source file: ' + required)
    public = ('manager', 'simulator', 'algorithms', 'tickets', 'gui')
    digest = hashlib.sha256()
    for package in public:
        for path in sorted((source / package).rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                digest.update(path.relative_to(source).as_posix().encode())
                digest.update(path.read_bytes())
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='memriboard-package-', dir=output) as temporary:
        staging = Path(temporary)
        for package in public:
            if (source / package).is_dir():
                shutil.copytree(source / package, staging / package, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copyfile(source / 'LICENSE', staging / 'LICENSE')
        (staging / 'pyproject.toml').write_text('''[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
[project]
name = "memriboard-connector-local"
version = "0.0.0+SOURCE"
description = "Locally packaged external MemriBoard; not an upstream release"
requires-python = ">=3.11"
dependencies = ["numpy", "SQLAlchemy"]
[tool.setuptools.packages.find]
where = ["."]
include = ["manager*", "simulator*", "algorithms*", "tickets*", "gui*"]
namespaces = true
[tool.setuptools.package-data]
"*" = ["*.ini", "*.json", "*.csv", "*.ui", "*.png", "*.svg"]
'''.replace('SOURCE', digest.hexdigest()[:12]), encoding='utf-8')
        subprocess.run([sys.executable, '-m', 'pip', 'wheel', '--no-cache-dir', '--no-deps', '--no-build-isolation', '--wheel-dir', str(output), str(staging)], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Authorized external MemriBoard checkout')
    parser.add_argument('--output', type=Path, default=Path('external-wheels'))
    args = parser.parse_args()
    build(args.source, args.output)
