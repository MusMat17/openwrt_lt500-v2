#!/usr/bin/env python3
"""Validate every literal generated panel file without executing the installer."""
import json
import pathlib
import re
import subprocess
import sys
import tempfile

source = pathlib.Path(sys.argv[1]).read_text()
assert not re.search(r'UI_RADIO|ui_radio_|zmwRadio|var RADIO|hostingradio', source), 'Radio remains in packaged panel'
lines = source.splitlines(keepends=True)
blocks = []
payload = None
for line in lines:
    if payload is not None:
        if line.strip() == 'ZM_INSTALLER_EOF':
            blocks.append((target, ''.join(payload).replace('@ZM_VERSION@', '5.064')))
            payload = None
        else:
            payload.append(line)
    elif "<< 'ZM_INSTALLER_EOF'" in line:
        match = re.match(r'''cat > ['\"]([^'\"]+)['\"] <<''', line)
        if match:
            target = match[1].replace('$_zmi_st/', '/opt/zapret-manager-luci/')
        else:
            assert line.startswith('sed "s/@ZM_VERSION@/$ZM_NEW_VER/" > "$_zmi_st/backend.sh" <<'), line
            target = '/opt/zapret-manager-luci/backend.sh'
        payload = []
assert payload is None and len(blocks) == 57, len(blocks)
assert len(set(name for name, _ in blocks)) == len(blocks)
counts = {'shell': 0, 'javascript': 0, 'json': 0}
with tempfile.TemporaryDirectory(prefix='lt500-panel-payloads-') as d:
    for index, (name, content) in enumerate(blocks):
        path = pathlib.Path(d) / f'{index}.js'
        path.write_text(content)
        if content.startswith('#!/bin/sh') or name.endswith('.sh'):
            subprocess.run(['sh', '-n', str(path)], check=True)
            counts['shell'] += 1
        elif name.endswith('.js'):
            # LuCI view files return at top level; its loader wraps them in a function.
            path.write_text('(function(){\n' + content + '\n});\n')
            subprocess.run(['node', '--check', str(path)], check=True, capture_output=True)
            counts['javascript'] += 1
        elif name.endswith('.json'):
            json.loads(content)
            counts['json'] += 1
print(f'All {len(blocks)} generated panel payloads extracted; syntax validated: {counts}')
