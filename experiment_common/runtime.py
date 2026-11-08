"""Repository paths and the installed, external MemriBoard package contract."""
from __future__ import annotations

from configparser import ConfigParser
from importlib import metadata, resources
from pathlib import Path, PureWindowsPath
import platform

from experiment_common.durable import sha

ROOT = Path(__file__).resolve().parents[1]
INI = 'configs/board.ini'
SIM_INI = 'configs/simulator_settings.ini'


def repo_path(value: str | Path) -> Path:
    """Resolve only paths contained in this checkout, on Windows and Unix."""
    raw = str(value)
    path, windows = Path(raw), PureWindowsPath(raw)
    if not raw or path.is_absolute() or windows.drive or windows.root:
        raise ValueError('Use a nonempty repository-relative path')
    if '..' in path.parts or '..' in windows.parts:
        raise ValueError('Parent-directory traversal is not allowed')
    resolved = (ROOT / path).resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError('Path must remain inside the repository')
    return resolved


def check_environment(*, simulator: bool) -> dict[str, object]:
    """Import the public package without creating a Connector or opening a port.

    MemriBoard's historical import names are manager and simulator. Its release
    name is not assumed to be a public PyPI distribution called memriboard.
    Numerical conversions remain the provider's implementation.
    """
    try:
        from manager.board import Connector
        from manager.service import converters
    except ImportError as exc:
        raise RuntimeError('Install the external MemriBoard package first; see docs/INSTALL.md') from exc
    for name in ('open_port', 'impact', 'close_port'):
        if not callable(getattr(Connector, name, None)):
            raise RuntimeError('Incompatible MemriBoard Connector: missing ' + name)
    for name in ('convert_adc_to_volt', 'convert_volt_to_dac', 'convert_dac_to_volt'):
        if not callable(getattr(converters, name, None)):
            raise RuntimeError('Incompatible MemriBoard converters: missing ' + name)
    from bindsnet.network.nodes import LIFNodes  # CPU dependency; no device I/O.
    import torch
    assert LIFNodes is not None and torch is not None
    versions = {name: metadata.version(name) for name in ('numpy', 'torch', 'torchvision', 'bindsnet', 'SQLAlchemy')}
    public_files = {
        'manager/board.py': resources.files('manager').joinpath('board.py'),
        'manager/service/converters.py': resources.files('manager.service').joinpath('converters.py'),
    }
    if simulator:
        from simulator.src import create_crossbar_array
        if not callable(create_crossbar_array):
            raise RuntimeError('MemriBoard simulator creation API is unavailable')
        settings = resources.files('simulator').joinpath('simulator_settings.ini')
        installed, expected = ConfigParser(), ConfigParser()
        installed.read_string(settings.read_text(encoding='utf-8-sig'))
        expected.read(ROOT / SIM_INI, encoding='utf-8-sig')
        if dict(installed['board']) != dict(expected['board']):
            raise RuntimeError('Installed simulator settings differ from configs/simulator_settings.ini; use a matching MemriBoard package')
        public_files.update({
            'simulator/src.py': resources.files('simulator').joinpath('src.py'),
            'simulator/memristor.py': resources.files('simulator').joinpath('memristor.py'),
            'simulator/simulator_settings.ini': settings,
        })
    # Record hashes, not host-specific filesystem paths or credentials.
    import hashlib
    owners = metadata.packages_distributions().get('manager', [])
    return {
        'python': platform.python_version(), 'packages': versions,
        'memriboard_distributions': {name: metadata.version(name) for name in owners},
        'memriboard_public_sha256': {name: hashlib.sha256(item.read_bytes()).hexdigest() for name, item in public_files.items()},
        'board_ini_sha256': sha(ROOT / INI), 'hardware_opened': False,
    }
