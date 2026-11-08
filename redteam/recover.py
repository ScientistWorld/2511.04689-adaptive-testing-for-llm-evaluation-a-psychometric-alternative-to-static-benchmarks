#!/usr/bin/env python3
"""Restore staged files after a compute node kills a candidate mid-run."""
import json
import shutil
from pathlib import Path

ROOT = Path('/home/user')
restore = ROOT / 'redteam/_restore'
if not restore.exists():
    raise SystemExit('No interrupted audit run to restore')
files = json.loads((restore / 'restore_manifest.json').read_text())
if (ROOT / 'checkpoints').exists():
    shutil.rmtree(ROOT / 'checkpoints')
if (restore / 'checkpoints').exists():
    (restore / 'checkpoints').rename(ROOT / 'checkpoints')
for index, relative in enumerate(files):
    destination = ROOT / relative
    source = restore / f'file_{index}'
    if source.exists():
        shutil.copyfile(source, destination)
    elif destination.exists():
        destination.unlink()
shutil.rmtree(restore)
print('Restored interrupted audit run')
