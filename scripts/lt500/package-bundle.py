#!/usr/bin/env python3
"""Package checked RC2 release files without rebuilding firmware."""
import hashlib
import pathlib
import sys
import zipfile

directory = pathlib.Path(sys.argv[1])
expected_image = 'd7c1277aa4ee0673dbb30cf150bdcd21d2b2663608e53d5cafa53dbcd107b447'
image = directory / 'Cudy-LT500v2-OpenWrt-23.05.5-v2.0-zapret-rc2-sysupgrade.bin'
assert hashlib.sha256(image.read_bytes()).hexdigest() == expected_image
files = [image.name, 'INSTALL-RC2.md', 'INSTALL-RC2-RU.md', 'lt500-panel.json',
         'openwrt-ramips-mt76x8-cudy_lt500-v2.manifest', 'profiles.json',
         'zapret-manager-lt500_2.48-2_mipsel_24kc.ipk']
checksums = ''.join(hashlib.sha256((directory / name).read_bytes()).hexdigest()
                    + '  ' + name + '\n' for name in sorted(files))
name = 'LT500v2-OpenWrt-23.05.5-RC2-zapret-bundle.zip'
archive = directory / name
with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as output:
    for member in sorted(files + ['SHA256SUMS']):
        info = zipfile.ZipInfo(member, (2026, 10, 8, 7, 45, 14))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        data = checksums.encode() if member == 'SHA256SUMS' else (directory / member).read_bytes()
        output.writestr(info, data, compresslevel=9)
(directory / (name + '.sha256')).write_text(
    hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + name + '\n')
print(name)
