#!/usr/bin/env python3
"""Check the real patched installer and execute its LT500 guard paths safely."""
import pathlib
import re
import subprocess
import sys
import tempfile

installer = pathlib.Path(sys.argv[1]).read_text()
assert '# Version: 3.43\n' in installer
assert '61263e50faeba2461e30d7fcc54f1fdb75ef1e21/ZapretManager_LuCI.sh' in installer
subprocess.run(['sh', '-n', sys.argv[1]], check=True)
match = re.search(r"cat > '/opt/zapret-manager-luci/backend.sh.zm-new' << 'ZM_INSTALLER_EOF'\n(.*?)\nZM_INSTALLER_EOF\n", installer, re.S)
assert match, 'Generated panel backend missing'
backend = match.group(1).replace('@ZM_VERSION@', '3.43') + '\n'

def function(name):
    # These selected functions end with an unindented closing brace.
    found = re.search(r'^' + re.escape(name) + r'\(\) \{\n.*?^\}', backend, re.M | re.S)
    assert found, name
    return found.group()

with tempfile.TemporaryDirectory(prefix='lt500-panel-guards-') as d:
    root = pathlib.Path(d)
    source = root / 'backend.sh'
    source.write_text(backend)
    subprocess.run(['sh', '-n', str(source)], check=True)
    marker = root / 'allinone'
    marker.touch()
    updater = root / 'update'
    updater.write_text('#!/bin/sh\nprintf "compatible-%s\\n" "$1"\n')
    updater.chmod(0o755)
    names = ('_lt500_pinned_pkg', '_zm_pkg_purge', 'zapret_action',
             'awg_action', '_st_install_awg', 'zm_update_status', 'zm_update_action')
    functions = '\n'.join(function(n) for n in names)
    functions = functions.replace('/etc/lt500-allinone', str(marker))
    functions = functions.replace('/usr/libexec/lt500-panel-update', str(updater))
    mocks = '''
_st_awg_loaded() { return 1; }
_awg_proto_ok() { return 0; }
_rb_warn() { echo "$*"; }
_zm_busy_job() { return 1; }
'''

    def run(command, expected):
        p = subprocess.run(['sh', '-c', functions + mocks + command], capture_output=True, text=True)
        assert p.returncode == expected, (command, p.returncode, p.stdout, p.stderr)
        return p.stdout

    for action in ('install', 'update', 'remove'):
        for name in ('zapret_action', 'awg_action'):
            assert 'LT500v2' in run(f'{name} {action}', 1)
    for package in ('kmod-amneziawg', 'kmod-tun', 'zapret', 'amneziawg-tools', 'luci-proto-amneziawg'):
        run(f'_lt500_pinned_pkg {package}', 0)
        run(f'_zm_pkg_purge {package}', 0)
    run('_lt500_pinned_pkg steer-core', 1)
    assert 'внешний kmod не устанавливаем' in run('_st_install_awg', 1)
    assert run('zm_update_status', 0).strip() == 'compatible-status'
    assert run('zm_update_action', 0).strip() == 'compatible-update'
    # An existing built-in AWG must succeed without fetching any packages.
    assert 'AmneziaWG' in run('''
_st_awg_loaded() { return 0; }
awg() { return 0; }
_st_install_awg update
''', 0)
    marker.unlink()
    run('_lt500_pinned_pkg kmod-tun', 1)

print('Panel 3.43: installer/backend syntax, firmware package guards and compatible update dispatch passed')
