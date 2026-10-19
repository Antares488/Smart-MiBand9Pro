"""Separate bundled read-only assets from persistent user data."""
import os
import sys
from pathlib import Path


def resource_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def data_dir():
    override = os.environ.get('SMARTMIBAND_DATA_DIR')
    if override:
        root = Path(override)
    elif getattr(sys, 'frozen', False):
        root = Path(os.environ['LOCALAPPDATA']) / 'SmartMiBand'
    else:
        root = Path(__file__).resolve().parent
    root.mkdir(parents=True, exist_ok=True)
    return root
