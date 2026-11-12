#!/usr/bin/env python3
"""Prepare immutable RC5 firmware, independent packages and install instructions."""
import hashlib
import json
import os
import pathlib
import shutil
import subprocess

base = pathlib.Path('bin/targets/ramips/mt76x8')
out = base / 'release'
out.mkdir(exist_ok=True)
image = 'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc5-sysupgrade.bin'
shutil.copy2(base / 'openwrt-ramips-mt76x8-cudy_lt500-v2-squashfs-sysupgrade.bin', out / image)
for name in ('openwrt-ramips-mt76x8-cudy_lt500-v2.manifest', 'profiles.json'):
    shutil.copy2(base / name, out / name)
versions = dict(line.split(' - ', 1) for line in (out / 'openwrt-ramips-mt76x8-cudy_lt500-v2.manifest').read_text().splitlines())
assert versions['zapret-manager-lt500'] == '5.064-1'
assert versions['steer-core'] == '2.1.3-1'
assert not any('steer-' + m in versions for m in ('vless', 'hysteria2', 'proxy', 'xsteer', 'obfs', 'tgws'))
steer = pathlib.Path('dl/steer-core-2.1.3-1_mipsel_24kc.ipk')
assert hashlib.sha256(steer.read_bytes()).hexdigest() == '81a290efe633fc09a96bbb0d3808473c581290d61a28faac0ac22ad3c7297a3e'
shutil.copy2(steer, out / steer.name)
panels = list(pathlib.Path('bin/packages').glob('mipsel_24kc/*/zapret-manager-lt500_5.064-1_mipsel_24kc.ipk'))
assert len(panels) == 1, panels
panel = panels[0]
shutil.copy2(panel, out / panel.name)
manifest = {'format': 1, 'board': 'cudy,lt500-v2', 'capability': 'awg2-i1-tun-steer213-panel5-noradio',
            'version': '5.064-1', 'file': panel.name, 'sha256': hashlib.sha256(panel.read_bytes()).hexdigest()}
(out / 'lt500-panel.json').write_text(json.dumps(manifest, indent=2) + '\n')
image_sha = hashlib.sha256((out / image).read_bytes()).hexdigest()
notes = pathlib.Path('docs/LT500v2-RC5-INSTALL-RU.md').read_text()
notes = notes.replace('@IMAGE_SHA256@', image_sha).replace('@IMAGE_BYTES@', str((out / image).stat().st_size)).replace('@KERNEL_VERSION@', versions['kernel'])
for name in ('INSTALL-RC5.md', 'INSTALL-RC5-RU.md'):
    (out / name).write_text(notes)
source = {'release': 'v2.0-zapret-rc5', 'openwrt': '23.05.5', 'kernel': versions['kernel'],
          'firmware_sha256': image_sha, 'build_commit': os.environ.get('LT500_BUILD_COMMIT') or subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          'manager': {'radio': False, 'version': '5.064-1', 'source': 'be2baf3db38dcefafc104a5460fe5829315ab514'},
          'steer': {'version': '2.1.3-1', 'source': '9e05393b9747f4f85cd1ede38e34d03c6583b187', 'package_sha256': hashlib.sha256(steer.read_bytes()).hexdigest(), 'net1': '1.4.3', 'signed_seed': True}}
(out / 'BUILD-INFO.json').write_text(json.dumps(source, indent=2) + '\n')
checksums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n'
                    for p in sorted(out.iterdir()) if p.is_file() and p.name != 'SHA256SUMS')
(out / 'SHA256SUMS').write_text(checksums)
print(checksums)
