#!/usr/bin/env python3
"""Prepare immutable RC4 firmware, independent packages and install instructions."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess

base = pathlib.Path('bin/targets/ramips/mt76x8')
out = base / 'release'
out.mkdir(exist_ok=True)
image = 'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc4-sysupgrade.bin'
shutil.copy2(base / 'openwrt-ramips-mt76x8-cudy_lt500-v2-squashfs-sysupgrade.bin', out / image)
for name in ('openwrt-ramips-mt76x8-cudy_lt500-v2.manifest', 'profiles.json'):
    shutil.copy2(base / name, out / name)
versions = dict(line.split(' - ', 1) for line in (out / 'openwrt-ramips-mt76x8-cudy_lt500-v2.manifest').read_text().splitlines())
assert versions['zapret-manager-lt500'] == '4.996-1'
for name in ('core', 'vless', 'hysteria2', 'proxy', 'xsteer', 'obfs', 'tgws'):
    assert versions['steer-' + name] == '2.0.5-1'
    packages = list(pathlib.Path('bin/packages').glob(f'mipsel_24kc/*/steer-{name}_2.0.5-1_mipsel_24kc.ipk'))
    assert len(packages) == 1, packages
    shutil.copy2(packages[0], out / packages[0].name)
panels = list(pathlib.Path('bin/packages').glob('mipsel_24kc/*/zapret-manager-lt500_4.996-1_mipsel_24kc.ipk'))
assert len(panels) == 1, panels
panel = panels[0]
shutil.copy2(panel, out / panel.name)
manifest = {'format': 1, 'board': 'cudy,lt500-v2', 'capability': 'awg2-i1-tun-steer205-panel4',
            'version': '4.996-1', 'file': panel.name, 'sha256': hashlib.sha256(panel.read_bytes()).hexdigest()}
(out / 'lt500-panel.json').write_text(json.dumps(manifest, indent=2) + '\n')
image_sha = hashlib.sha256((out / image).read_bytes()).hexdigest()
notes = pathlib.Path('docs/LT500v2-RC4-INSTALL-RU.md').read_text()
notes = notes.replace('@IMAGE_SHA256@', image_sha).replace('@IMAGE_BYTES@', str((out / image).stat().st_size)).replace('@KERNEL_VERSION@', versions['kernel'])
for name in ('INSTALL-RC4.md', 'INSTALL-RC4-RU.md'):
    (out / name).write_text(notes)
source = {'release': 'v2.0-zapret-rc4', 'openwrt': '23.05.5', 'kernel': versions['kernel'],
          'firmware_sha256': image_sha, 'build_commit': os.environ.get('LT500_BUILD_COMMIT') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          'manager': {'version': '4.996-1', 'source': '171791b26e3959de50b800a7c80365fc2b7f3fce'},
          'steer': {'version': '2.0.5-1', 'source': '239c2897a726bc66dbe1900a3f4595d4d9b5f62d'}}
(out / 'BUILD-INFO.json').write_text(json.dumps(source, indent=2) + '\n')
checksums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
                    for p in sorted(out.iterdir()) if p.is_file() and p.name != 'SHA256SUMS')
(out / 'SHA256SUMS').write_text(checksums)
print(checksums)
