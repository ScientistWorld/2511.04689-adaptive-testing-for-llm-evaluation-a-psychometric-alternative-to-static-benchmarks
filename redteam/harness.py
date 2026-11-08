#!/usr/bin/env python3
"""Stage one candidate, terminate it, then run restored test with no arguments.

The evaluator, scripts, environment and Python runtime are never patched.
Only files a future agent owns are staged. Finally restore all staged files.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/user')
AUDIT = ROOT / 'redteam'
sys.path.insert(0, str(AUDIT / 'support'))
from build_method import BENCHMARKS, copy_outputs


def command(argv, log):
    with log.open('w') as f:
        proc = subprocess.run(argv, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    return proc.returncode


def main(case):
    directory = AUDIT / case
    directory.mkdir(parents=True, exist_ok=True)
    restore = AUDIT / '_restore'
    if restore.exists():
        raise RuntimeError('Unrestored previous run; inspect redteam/_restore before proceeding')
    restore.mkdir()
    start = time.monotonic()
    files = [ROOT / f'scoring/scores_{split}.json' for split in ('train', 'test')]
    if case == 'shortcut_test_size':
        files += [ROOT / f'data/downloads/atlas_response_matrices/data/clean_response_matrix_{b}.csv' for b in BENCHMARKS]
    if case == 'shortcut_fixed_targets':
        files += [ROOT / f'data/calibrated_banks/{b}/irt_person_scores_WLE_SE.csv' for b in BENCHMARKS]
    (restore / 'restore_manifest.json').write_text(json.dumps([str(file.relative_to(ROOT)) for file in files]))
    backups = []
    for index, file in enumerate(files):
        backup = restore / f'file_{index}'
        if file.exists():
            shutil.copyfile(file, backup)
        backups.append((file, backup))
    old_checkpoints = ROOT / 'checkpoints'
    had_checkpoints = old_checkpoints.exists()
    if had_checkpoints:
        old_checkpoints.rename(restore / 'checkpoints')
    old_checkpoints.mkdir()
    status = {'case': case, 'method_exit': None, 'train_exit': None, 'test_exit': None,
              'test_command': ['bash', 'scripts/evaluate_test.sh'], 'test_arguments': [],
              'persistent_processes': False, 'environment_overrides': {}}
    try:
        # The first reference recomputes the baseline from visible code.
        # Other runs reuse these trained outputs as authorized in the audit.
        if (AUDIT / 'reference_seed123/artifacts/random_static/manifest.json').exists():
            copy_outputs(AUDIT / 'reference_seed123/artifacts/random_static', old_checkpoints / 'random_static')
        else:
            baseline = [sys.executable, str(AUDIT / 'support/baseline_original.py'), '--benchmarks', *BENCHMARKS,
                        '--test-length', '750', '--output-dir', 'checkpoints/random_static']
            if command(baseline, directory / 'baseline.log'):
                raise RuntimeError('baseline failed')
        status['method_exit'] = command([sys.executable, str(directory / 'method.py')], directory / 'method.log')
        if status['method_exit'] == 0:
            status['train_exit'] = command(['bash', 'scripts/evaluate_train.sh'], directory / 'train.log')
            if status['train_exit'] == 0:
                shutil.copyfile(ROOT / 'scoring/scores_train.json', directory / 'scores_train.json')
            # Always try hidden test, including malformed artifacts rejected by train.
            status['test_exit'] = command(['bash', 'scripts/evaluate_test.sh'], directory / 'test.log')
            if status['test_exit'] == 0:
                shutil.copyfile(ROOT / 'scoring/scores_test.json', directory / 'scores_test.json')
            else:
                lines = (directory / 'test.log').read_text().splitlines()
                status['test_error'] = lines[-1] if lines else ''
        if case.startswith('reference_seed') or case.startswith('better_') or case.startswith('weaker_'):
            metadata = old_checkpoints / 'method_training_metadata.json'
            if metadata.exists():
                shutil.copyfile(metadata, directory / 'training_metadata.json')
        # Preserve compact manifest-indexed outputs for replay and diagnostics.
        artifacts = directory / 'artifacts'
        if artifacts.exists():
            shutil.rmtree(artifacts)
        artifacts.mkdir()
        for name in ('random_static', 'atlas_python'):
            if (old_checkpoints / name / 'manifest.json').exists():
                copy_outputs(old_checkpoints / name, artifacts / name)
    finally:
        shutil.rmtree(old_checkpoints)
        if had_checkpoints:
            (restore / 'checkpoints').rename(old_checkpoints)
        for file, backup in backups:
            if backup.exists():
                shutil.copyfile(backup, file)
            elif file.exists():
                file.unlink()
        shutil.rmtree(restore)
        status['seconds'] = time.monotonic() - start
        (directory / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
        print(json.dumps(status), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
