#!/usr/bin/env python3
"""Validate release IPKs with the image's own opkg without installing anything."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

root = pathlib.Path(sys.argv[1]).resolve()
packages = sorted(pathlib.Path(sys.argv[2]).resolve().glob('*.ipk'))
assert len(packages) == 2, packages
qemu = os.environ.get('LT500_TEST_QEMU') or shutil.which('qemu-mipsel-static')
assert qemu
with tempfile.TemporaryDirectory(prefix='lt500-opkg-check-') as directory:
    fixture = pathlib.Path(directory)
    shutil.copytree(root / 'usr/lib/opkg', fixture / 'usr/lib/opkg', symlinks=True)
    # opkg compares recorded conffile hashes even during --noaction reinstall.
    # The fixture must contain the image's actual configuration as well as its DB.
    shutil.copytree(root / 'etc', fixture / 'etc', symlinks=True)
    for path in ('var/lock', 'var/opkg-lists', 'tmp'):
        (fixture / path).mkdir(parents=True, exist_ok=True)
    config = fixture / 'opkg.conf'
    config.write_text('dest root /\narch all 1\narch noarch 1\narch mipsel_24kc 10\n')
    command = [qemu, '-L', str(root), str(root / 'bin/opkg.real'),
               '--offline-root', str(fixture), '--conf', str(config),
               '--noaction', '--force-reinstall', 'install', *map(str, packages)]
    result = subprocess.run(command, env=dict(os.environ, IPKG_NO_SCRIPT='1'), capture_output=True, text=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert 'Collected errors:' not in result.stderr, result.stderr
print('Actual image opkg accepted both independent packages: format, architecture and dependencies checked in no-action mode')
