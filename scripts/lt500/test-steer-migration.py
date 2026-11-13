#!/usr/bin/env python3
"""Emulate official signed-plugin migration on the published RC4 userspace.

Run as root in CI: chroot is needed for genuine /dev and package-db lookups.
This tests signatures/dependencies/ELFs, not kernel or network operation.
"""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import urllib.request

repo = pathlib.Path(__file__).resolve().parents[2]
assert os.geteuid() == 0, 'Run this chroot test with sudo in CI'
with tempfile.TemporaryDirectory(prefix='lt500-steer-migration-') as d:
    root = pathlib.Path(d) / 'root'
    shutil.copytree(repo / 'tmp/rc6/roundtrip', root, symlinks=True, ignore=shutil.ignore_patterns('console'))
    shutil.copyfile(shutil.which('qemu-mipsel-static'), root / 'usr/bin/qemu-mipsel-static')
    (root / 'usr/bin/qemu-mipsel-static').chmod(0o755)
    # Plugin prerequisites use existence checks. These are fixture placeholders,
    # not claims that an emulated process can load a host MIPS kernel module.
    (root / 'dev/net').mkdir(parents=True, exist_ok=True)
    (root / 'dev/net/tun').touch()
    (root / 'sys/module/amneziawg').mkdir(parents=True, exist_ok=True)
    for path in ('tmp/pm/etc/repos.d', 'tmp/pm/plugins', 'tmp/pm/run', 'tmp/pm/tmp'):
        (root / path).mkdir(parents=True, exist_ok=True)
    protocols = ['vless', 'hysteria2', 'proxy', 'xsteer', 'obfs', 'warpbox']
    (root / 'tmp/pm/etc/migrate.json').write_text(json.dumps({'packages': ['steer-' + p for p in protocols]}))
    # Empty test repos.d forces signed offline-seed fallback; real firmware
    # retains its official repository and trusted keys without modification.
    env = dict(os.environ, STEER_PLUGIN_ETC='/tmp/pm/etc', STEER_PLUGIN_DIR='/tmp/pm/plugins',
               STEER_PLUGIN_RUN='/tmp/pm/run', STEER_PLUGIN_TMP='/tmp/pm/tmp',
               STEER_PLUGIN_KEEPD='/tmp/pm/keep', STEER_PLUGIN_ARCH='mipsel_24kc')
    command = ['chroot', str(root), '/usr/bin/qemu-mipsel-static', '/usr/sbin/steerd']
    subprocess.run(command + ['--version'], env=env, check=True)
    result = subprocess.run(command + ['plugin', 'migrate'], env=env, text=True, capture_output=True, timeout=240)
    print(result.stdout, result.stderr, flush=True)
    assert result.returncode == 0
    state = json.loads((root / 'tmp/pm/etc/state.json').read_text())['plugins']
    for plugin in protocols + ['net1', 'awg']:
        item = state[plugin]
        assert item['version'] == ('1.5.0' if plugin == 'net1' else '2.1.4'), item
        assert item['state'] == 'enabled' and item['from'] == 'seed', item
        assert (root / f'tmp/pm/plugins/{plugin}/plugin.json').is_file()
    subprocess.run(command + ['plugin', 'status', '--json'], env=env, check=True)
    assert (root / 'tmp/pm/etc/migrate.done.json').is_file()
    print('RC4 musl/MIPS userspace: all eight signed seed plugins migrated with real package dependencies')
